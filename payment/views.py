from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from .moyasar import create_payment
import requests
from rest_framework.decorators import api_view
from django.conf import settings
from .models import Payment, Invoice
from .serializers import PaymentSerializer, InvoiceSerializer, InvoiceDetailSerializer
from .moyasar import fetch_payment as fetch_payment_api
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
import uuid
from django.utils import timezone
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging
from decimal import Decimal
from django.db import transaction
from tourapp.models import Booking
from django.core.mail import send_mail

def payment_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    service = booking.servicebooking
    context = {
    "moyasar_key": settings.MOYASAR_PUBLISHABLE_KEY,
    "booking_id": booking.id,
}

    return render(request, "payment.html", context)



logger = logging.getLogger(__name__)
class CreatePaymentView(APIView):
    """
    إنشاء دفعة جديدة باستخدام token من Moyasar Form (آمن للـ Production)
    """
    def post(self, request):
        try:
            data = request.data

            # 🟢 التحقق من وجود booking_id
            booking_id = data.get("booking_id")
            if not booking_id:
                return Response({
                    "success": False,
                    "error": "booking_id is required"
                }, status=400)

            booking = get_object_or_404(Booking, id=booking_id)

            # 🟢 استقبال التوكن من الـ frontend
            source_data = data.get("source", {})
            token = source_data.get("token")

            if not token:
                return Response({
                    "success": False,
                    "error": "Payment token is required"
                }, status=400)

            # 🟢 إعداد بيانات المصدر
            source = {
                "type": "token",
                "token": token
            }

            # 🟡 إنشاء الدفع عبر ميسر
            payment_response = create_payment(
                amount=data.get("amount"),
                description=data.get("description"),
                callback_url="https://echorabia.com/payment/callback/",
                source=source,
                metadata=data.get("metadata", {"booking_id": booking_id})
            )

            # 🟢 حفظ الدفعة في قاعدة البيانات
            if "id" in payment_response:
                payment, created = Payment.objects.get_or_create(
                    moyasar_id=payment_response.get("id"),
                    defaults={
                        "booking": booking,
                        "amount": payment_response.get("amount"),
                        "status": payment_response.get("status"),
                        "description": data.get("description", ""),
                    }
                )

                # 🧾 إنشاء فاتورة جديدة لو أول مرة
                if created:
                    try:
                        self.create_invoice_for_payment(payment, data.get("description"))
                    except Exception as e:
                        logger.error(f"Failed to create invoice: {str(e)}")

            # 🟣 التعامل مع حالات الدفع المختلفة
            status = payment_response.get("status")

            # ✅ حالة initiated (3DS)
            if status == "initiated":
                tx_url = payment_response.get("source", {}).get("transaction_url")
                return Response({
                    "success": True,
                    "status": "initiated",
                    "transaction_url": tx_url,
                    "message": "Redirect the user to this URL to complete 3DS verification."
                })

            # ✅ حالة الدفع الناجح مباشرة
            elif status == "paid":
                return Response({
                    "success": True,
                    "status": "paid",
                    "message": "Payment completed successfully.",
                    "moyasar_data": payment_response,
                })

            # ❌ أي حالة أخرى (failed أو pending)
            else:
                return Response({
                    "success": False,
                    "status": status,
                    "message": "Payment not completed.",
                    "moyasar_data": payment_response,
                })

        except Exception as e:
            logger.error(f"Error in CreatePaymentView: {str(e)}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=500)

    def create_invoice_for_payment(self, payment, description=None):
        """إنشاء فاتورة جديدة عند الدفع"""
        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        invoice = Invoice.objects.create(
            payment=payment,
            invoice_number=invoice_number,
            amount=Decimal(payment.amount) / 100,
            currency='SAR',
            description=description or f"Payment for {payment.moyasar_id}",
        )
        return invoice



@csrf_exempt
@require_POST
def moyasar_webhook(request):
    """
    Webhook endpoint لاستقبال التحديثات من Moyasar
    """
    try:
        # التحقق من صحة الـ webhook (اختياري)
        signature = request.headers.get('X-Moyasar-Signature')
        if not verify_webhook_signature(request.body, signature):
            logger.warning("Invalid webhook signature")
            # نكمل المعالجة حتى لو فشل التحقق

        payload = json.loads(request.body)
        event_type = payload.get('type')
        payment_data = payload.get('data', {})
        
        logger.info(f"Received webhook: {event_type} for payment {payment_data.get('id')}")

        if event_type == 'payment_paid':
            handle_payment_paid(payment_data)
        elif event_type == 'payment_failed':
            handle_payment_failed(payment_data)
        elif event_type == 'payment_refunded':
            handle_payment_refunded(payment_data)

        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse("Error", status=200)  # نرجع 200 لمنع إعادة الإرسال


def verify_webhook_signature(payload, signature):
    """
    التحقق من صحة الـ webhook signature
    """
    try:
        if not signature or not hasattr(settings, 'MOYASAR_WEBHOOK_SECRET'):
            return True  # تجاهل التحقق إذا لم يكن الـ secret محدد
        
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            settings.MOYASAR_WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return True  # نسمح بالمرور في حالة الخطأ
    
def handle_payment_paid(payment_data):
    """
    معالجة حدث الدفع المكتمل
    """
    moyasar_id = payment_data.get('id')

    try:
        with transaction.atomic():
            payment = Payment.objects.get(moyasar_id=moyasar_id)
            payment.status = 'paid'
            payment.amount = payment_data.get('amount', payment.amount)
            payment.paid_at = timezone.now()
            payment.save()

            # تحديث الفاتورة
            update_invoice_on_payment_success(payment)

            # 🟢 هنا نربط الدفع بالحجز
            booking_id = payment_data.get("metadata", {}).get("booking_id")
            if booking_id:
                try:
                    booking = Booking.objects.get(id=booking_id)
                    booking.status = "confirmed"
                    booking.save()

                    service = booking.servicebooking

                    # إرسال الإيميل
                    subject = f'New Booking: {service.title}'
                    message = f'''
A new booking has been made and payment confirmed ✅:

Service: {service.title}
Name: {booking.name}
Email: {booking.email}
Phone: {booking.phone}
Number of Adults: {booking.numofadult}
Booking Date: {booking.date}
Hotel: {booking.hotel}
Room Number: {booking.room}
Drop-off: {booking.dropoff}
Medical Conditions: {booking.disease}
Agreed to Cancellation Policy: {'Yes' if booking.policy else 'No'}
'''
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        ['echorabia@gmail.com'],
                        fail_silently=False,
                    )
                    logger.info(f"Email sent successfully for booking {booking.id}")

                except Booking.DoesNotExist:
                    logger.error(f"Booking with ID {booking_id} not found")

            logger.info(f"Payment {moyasar_id} marked as paid via webhook")

    except Payment.DoesNotExist:
        logger.warning(f"Payment {moyasar_id} not found in database")
    except Exception as e:
        logger.error(f"Error handling payment_paid webhook: {str(e)}")

def handle_payment_failed(payment_data):
    """
    معالجة حدث فشل الدفع
    """
    moyasar_id = payment_data.get('id')
    
    try:
        payment = Payment.objects.get(moyasar_id=moyasar_id)
        payment.status = 'failed'
        payment.save()
        logger.info(f"Payment {moyasar_id} marked as failed via webhook")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment {moyasar_id} not found in database")
    except Exception as e:
        logger.error(f"Error handling payment_failed webhook: {str(e)}")


def handle_payment_refunded(payment_data):
    """
    معالجة حدث إرجاع المبلغ
    """
    moyasar_id = payment_data.get('id')
    
    try:
        payment = Payment.objects.get(moyasar_id=moyasar_id)
        payment.status = 'refunded'
        payment.save()
        logger.info(f"Payment {moyasar_id} marked as refunded via webhook")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment {moyasar_id} not found in database")
    except Exception as e:
        logger.error(f"Error handling payment_refunded webhook: {str(e)}")


def update_invoice_on_payment_success(payment):
    """
    تحديث الفاتورة عند نجاح الدفع
    """
    try:
        invoice = payment.invoice
        if not invoice.paid_at:  # لو لم يتم تحديثها من قبل
            invoice.paid_at = timezone.now()
            invoice.status = 'paid'
            invoice.save()
            logger.info(f"Invoice {invoice.invoice_number} marked as paid")
    except Invoice.DoesNotExist:
        logger.warning(f"No invoice found for payment {payment.moyasar_id}")
    except Exception as e:
        logger.error(f"Error updating invoice for payment {payment.moyasar_id}: {str(e)}")


@csrf_exempt
def payment_callback_view(request):
    """
    Callback URL لإعادة توجيه المستخدم بعد الدفع
    """
    try:
        status = request.GET.get("status")
        moyasar_id = request.GET.get("id")

        payment = None
        invoice = None

        if moyasar_id:
            try:
                payment = Payment.objects.get(moyasar_id=moyasar_id)
                invoice = getattr(payment, "invoice", None)
                
                # تحديث حالة الدفع من Moyasar
                payment_data, status_code = fetch_payment_api(moyasar_id)
                if status_code == 200:
                    old_status = payment.status
                    payment.status = payment_data.get("status")
                    payment.save()
                    
                    # إذا تم الدفع بنجاح، نحدث الفاتورة
                    if old_status != "paid" and payment.status == "paid":
                        update_invoice_on_payment_success(payment)
                        
            except Payment.DoesNotExist:
                logger.warning(f"Payment {moyasar_id} not found in callback")

        if status == "paid" and payment:
            return render(request, "tourapp/payment_success.html", {
                "payment": payment,
                "invoice": invoice,
            })
        else:
            return render(request, "tourapp/payment_failed.html", {
                "payment": payment,
                "status": status,
                "moyasar_id": moyasar_id,
            })

    except Exception as e:
        logger.error(f"Error in payment_callback_view: {str(e)}")
        return render(request, "payments/payment_failed.html", {
            "error": "حدث خطأ في معالجة الدفعة"
        })
