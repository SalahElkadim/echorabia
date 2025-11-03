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
    
    # نجيب السعر النهائي من الموديل الجديد
    amount_sar = booking.price.total_price  # السعر الأساسي من BookingPrice

# حساب ضريبة القيمة المضافة 15%
    vat = amount_sar * 0.15

    # المجموع الكلي شامل الضريبة
    total_with_vat = amount_sar + vat

    # التحويل إلى halalah (لأن Moyasar تتعامل بالقروش)
    amount_halalah = int(total_with_vat * 100)
  # ميسر يستقبل بالهللة (1 SAR = 100 halalah)
    
    context = {
        "moyasar_key": settings.MOYASAR_PUBLISHABLE_KEY,
        "booking_id": booking.id,
        "amount": amount_halalah,  # نمرره للفورم
    }
    return render(request, "payment.html", context)




logger = logging.getLogger(__name__)
class CreatePaymentView(APIView):
    """
    إنشاء دفعة جديدة باستخدام token من Moyasar Form
    """
    def post(self, request):
        payment = None
        
        try:
            data = request.data
            logger.info(f"=== 🎬 Payment request started ===")
            logger.info(f"Request data: {data}")

            # التحقق من booking_id
            booking_id = data.get("booking_id")
            if not booking_id:
                logger.error("❌ booking_id is missing")
                return Response({
                    "success": False,
                    "error": "booking_id is required"
                }, status=400)

            booking = get_object_or_404(Booking, id=booking_id)
            logger.info(f"✅ Booking found: {booking.id}")
            
            # استقبال التوكن
            source_data = data.get("source", {})
            token = source_data.get("token")

            if not token:
                logger.error("❌ Payment token is missing")
                return Response({
                    "success": False,
                    "error": "Payment token is required"
                }, status=400)

            logger.info(f"✅ Token received: {token[:20]}...")

            # إعداد المصدر
            source = {
                "type": "token",
                "token": token
            }
            
            # 🔥 حساب المبلغ شامل الضريبة
            base_amount = booking.price.total_price
            vat = base_amount * Decimal('0.15')
            total_with_vat = base_amount 
            amount_halalah = int(total_with_vat * 100)
            
            logger.info(f"💰 Payment calculation:")
            logger.info(f"   Base: {base_amount} SAR")
            logger.info(f"   VAT: {vat} SAR")
            logger.info(f"   Total: {total_with_vat} SAR")
            logger.info(f"   Halalah: {amount_halalah}")
            
            # إنشاء الدفع عبر ميسر
            logger.info("📤 Calling Moyasar API...")
            
            payment_response = create_payment(
                amount=amount_halalah,
                description=f"Booking #{booking_id} - {booking.servicebooking.title}",
                callback_url="https://echorabia.com/payment/callback/",
                source=source,
                metadata={"booking_id": str(booking_id)}
            )

            # التحقق من وجود خطأ
            if "error" in payment_response or "message" in payment_response:
                error_msg = payment_response.get("message") or payment_response.get("error")
                logger.error(f"❌ Moyasar error: {error_msg}")
                return Response({
                    "success": False,
                    "error": error_msg,
                    "details": payment_response
                }, status=400)

            # التحقق من وجود ID
            moyasar_id = payment_response.get("id")
            if not moyasar_id:
                logger.error(f"❌ No payment ID: {payment_response}")
                return Response({
                    "success": False,
                    "error": "Failed to create payment - no ID returned",
                    "response": payment_response
                }, status=500)

            logger.info(f"✅ Moyasar payment created: {moyasar_id}")

            # حفظ في قاعدة البيانات
            try:
                payment, created = Payment.objects.get_or_create(
                    moyasar_id=moyasar_id,
                    defaults={
                        "booking": booking,
                        "amount": payment_response.get("amount", amount_halalah),
                        "status": payment_response.get("status", "initiated"),
                        "description": f"Booking #{booking_id}",
                        "source_type": payment_response.get("source", {}).get("type"),
                    }
                )

                action = "created" if created else "found existing"
                logger.info(f"✅ Payment {action} in DB: ID={payment.id}, Moyasar ID={moyasar_id}")

                # إنشاء فاتورة
                if created:
                    try:
                        invoice = self.create_invoice_for_payment(payment)
                        logger.info(f"✅ Invoice created: {invoice.invoice_number}")
                    except Exception as e:
                        logger.error(f"❌ Invoice creation failed: {str(e)}", exc_info=True)

            except Exception as e:
                logger.error(f"❌ DB save failed: {str(e)}", exc_info=True)

            # معالجة الحالات
            status = payment_response.get("status")
            logger.info(f"📊 Payment status: {status}")

            if status == "initiated":
                tx_url = payment_response.get("source", {}).get("transaction_url")
                if not tx_url:
                    logger.error("❌ No transaction URL for 3DS")
                    return Response({
                        "success": False,
                        "error": "3DS URL missing"
                    }, status=500)
                
                logger.info(f"🔐 3DS required: {tx_url}")
                return Response({
                    "success": True,
                    "status": "initiated",
                    "transaction_url": tx_url,
                    "message": "Redirect to 3DS"
                })

            elif status == "paid":
                logger.info(f"✅ Payment completed (no 3DS)")
                
                booking.status = "confirmed"
                booking.save()
                logger.info(f"✅ Booking confirmed")
                
                return Response({
                    "success": True,
                    "status": "paid",
                    "message": "Payment successful",
                    "moyasar_data": payment_response,
                })

            else:
                logger.warning(f"⚠️ Unexpected status: {status}")
                return Response({
                    "success": False,
                    "status": status,
                    "message": f"Payment status: {status}",
                    "moyasar_data": payment_response,
                }, status=400)

        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "error": str(e)
            }, status=500)

    def create_invoice_for_payment(self, payment):
        """إنشاء فاتورة"""
        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        amount_sar = Decimal(payment.amount) / 100
        base_amount = amount_sar / Decimal('1.15')
        vat_amount = amount_sar - base_amount
        
        invoice = Invoice.objects.create(
            payment=payment,
            invoice_number=invoice_number,
            amount=base_amount.quantize(Decimal('0.01')),
            tax_amount=vat_amount.quantize(Decimal('0.01')),
            currency='SAR',
            description=f"Booking #{payment.booking.id}",
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
    Callback URL بعد إتمام الدفع
    """
    try:
        status = request.GET.get("status")
        moyasar_id = request.GET.get("id")
        
        logger.info(f"🔔 === CALLBACK RECEIVED ===")
        logger.info(f"Status: {status}, Moyasar ID: {moyasar_id}")
        logger.info(f"Full URL: {request.build_absolute_uri()}")

        if not moyasar_id:
            logger.error("❌ No Moyasar ID in callback")
            return render(request, "tourapp/payment_failed.html", {
                "error": "معلومات الدفع غير كاملة"
            })

        try:
            payment = Payment.objects.get(moyasar_id=moyasar_id)
            invoice = getattr(payment, "invoice", None)
            booking = payment.booking
            
            logger.info(f"✅ Payment found: ID={payment.id}, Current status={payment.status}")
            
            # جلب التحديث من ميسر
            logger.info("📤 Fetching from Moyasar...")
            payment_data, status_code = fetch_payment_api(moyasar_id)
            
            if status_code == 200 and payment_data:
                moyasar_status = payment_data.get("status")
                old_status = payment.status
                
                logger.info(f"📊 Status: {old_status} → {moyasar_status}")
                
                payment.status = moyasar_status
                payment.save()
                
                # لو الدفع نجح
                if old_status != "paid" and moyasar_status == "paid":
                    logger.info("🎉 PAYMENT SUCCESS - Updating records...")
                    
                    # تحديث الفاتورة
                    if invoice and not invoice.paid_at:
                        invoice.status = 'paid'
                        invoice.paid_at = timezone.now()
                        invoice.save()
                        logger.info(f"✅ Invoice updated")
                    
                    # تحديث الحجز
                    if booking.status != "confirmed":
                        booking.status = "confirmed"
                        booking.save()
                        logger.info(f"✅ Booking confirmed")
                
                status = moyasar_status
            else:
                logger.warning(f"⚠️ Moyasar fetch failed: {status_code}")
                
        except Payment.DoesNotExist:
            logger.error(f"❌ Payment not found: {moyasar_id}")
            return render(request, "tourapp/payment_failed.html", {
                "error": "لم يتم العثور على عملية الدفع",
                "moyasar_id": moyasar_id
            })

        # التوجيه حسب الحالة
        if status == "paid":
            logger.info(f"✅ → SUCCESS PAGE")
            return render(request, "tourapp/payment_success.html", {
                "payment": payment,
                "invoice": invoice,
                "booking": booking,
            })
        else:
            logger.warning(f"⚠️ → FAILED PAGE (status: {status})")
            return render(request, "tourapp/payment_failed.html", {
                "payment": payment,
                "status": status,
                "moyasar_id": moyasar_id,
            })

    except Exception as e:
        logger.error(f"❌ Callback error: {str(e)}", exc_info=True)
        return render(request, "tourapp/payment_failed.html", {
            "error": "حدث خطأ في معالجة الدفعة"
        })