from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.mail import send_mail
import json
import logging
import uuid
from decimal import Decimal

from .models import Payment, Invoice
from .serializers import PaymentSerializer, InvoiceSerializer
from .moyasar import fetch_payment as fetch_payment_api
from tourapp.models import Booking


logger = logging.getLogger(__name__)


def payment_page(request, booking_id):
    """
    🔥 FIXED: عرض صفحة الدفع مع إنشاء Payment مبدئي (pending)
    """
    booking = get_object_or_404(Booking, id=booking_id)
    service = booking.servicebooking
    
    # حساب المبلغ
    amount_sar = booking.price.total_price
    amount_halalah = int(amount_sar * 100)
    
    # 🔥 إنشاء Payment مبدئي (pending_form)
    try:
        with transaction.atomic():
            given_id = str(uuid.uuid4())
            
            pending_payment = Payment.objects.create(
                moyasar_id=f"PENDING-{given_id}",
                booking=booking,
                amount=amount_halalah,
                status="pending_form",
                description=f"Booking #{booking_id} - {service.title}",
            )
            
            logger.info(f"✅ Created pending payment: {pending_payment.id}")
            payment_session_id = str(pending_payment.id)
            
    except Exception as e:
        logger.error(f"❌ Failed to create pending payment: {e}")
        return render(request, "error.html", {"message": "Failed to initialize payment"})
    
    context = {
        "moyasar_key": settings.MOYASAR_PUBLISHABLE_KEY,
        "booking_id": booking.id,
        "amount": amount_halalah,
        "payment_session_id": payment_session_id,
    }
    return render(request, "payment.html", context)


@csrf_exempt
@require_POST
def moyasar_webhook(request):
    """
    🔥 FIXED: Webhook endpoint لاستقبال التحديثات من Moyasar
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔔 WEBHOOK RECEIVED!")
        print(f"{'='*60}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Body: {request.body.decode('utf-8')}")
        print(f"{'='*60}\n")
        
        signature = request.headers.get('X-Moyasar-Signature')
        if not verify_webhook_signature(request.body, signature):
            logger.warning("Invalid webhook signature")

        payload = json.loads(request.body)
        event_type = payload.get('type')
        payment_data = payload.get('data', {})
        
        logger.info(f"📞 Webhook: {event_type} for payment {payment_data.get('id')}")

        if event_type == 'payment_paid':
            handle_payment_paid(payment_data)
        elif event_type == 'payment_failed':
            handle_payment_failed(payment_data)
        elif event_type == 'payment_refunded':
            handle_payment_refunded(payment_data)

        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return HttpResponse("Error", status=200)


def verify_webhook_signature(payload, signature):
    try:
        if not signature or not hasattr(settings, 'MOYASAR_WEBHOOK_SECRET'):
            return True
        
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
        return True


def handle_payment_paid(payment_data):
    """
    🔥 FIXED: معالجة webhook للدفع الناجح
    """
    try:
        moyasar_id = payment_data.get("id")
        if not moyasar_id:
            logger.error("❌ Payment data missing 'id'")
            return

        logger.info(f"🔔 Webhook: payment_paid for {moyasar_id}")

        # استخراج booking_id من metadata
        metadata = payment_data.get("metadata") or {}
        booking_id = metadata.get("booking_id")
        
        # 🔥 محاولة استخراج session_id من callback_url
        callback_url = payment_data.get('callback_url', '')
        session_id = None
        
        if 'session_id=' in callback_url:
            try:
                session_id = callback_url.split('session_id=')[1].split('&')[0]
                logger.info(f"✅ Extracted session_id: {session_id}")
            except:
                logger.warning(f"⚠️ Failed to extract session_id")

        booking = None
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
                logger.info(f"✅ Found booking: {booking.id}")
            except Booking.DoesNotExist:
                logger.warning(f"⚠️ Booking {booking_id} not found")

        with transaction.atomic():
            # محاولة جلب Payment الموجود
            payment = None
            
            # أولاً: بـ session_id
            if session_id:
                try:
                    pending_payment = Payment.objects.get(id=session_id, status="pending_form")
                    logger.info(f"✅ Found pending payment: {pending_payment.id}")
                    
                    # تحديث الـ pending payment
                    pending_payment.moyasar_id = moyasar_id
                    pending_payment.status = "paid"
                    pending_payment.paid_at = timezone.now()
                    pending_payment.amount = payment_data.get("amount", pending_payment.amount)
                    
                    if not pending_payment.booking and booking:
                        pending_payment.booking = booking
                    
                    pending_payment.save()
                    payment = pending_payment
                    
                    logger.info(f"✅ Updated pending payment to paid")
                except Payment.DoesNotExist:
                    logger.warning(f"⚠️ Pending payment {session_id} not found")
            
            # ثانياً: بـ moyasar_id
            if not payment:
                payment = Payment.objects.filter(moyasar_id=moyasar_id).first()
                
                if payment:
                    logger.info(f"✅ Found existing payment by moyasar_id")
                    payment.status = "paid"
                    payment.paid_at = timezone.now()
                    payment.save()
                else:
                    # إنشاء payment جديد
                    logger.info(f"✅ Creating new payment")
                    payment = Payment.objects.create(
                        moyasar_id=moyasar_id,
                        booking=booking,
                        amount=payment_data.get("amount"),
                        status="paid",
                        paid_at=timezone.now(),
                        description=payment_data.get("description"),
                        source_type=payment_data.get("source", {}).get("type"),
                    )

            # تحديث الفاتورة
            update_invoice_on_payment_success(payment)

            # تحديث الحجز
            if payment.booking:
                booking = payment.booking
                booking.status = "confirmed"
                booking.save()
                logger.info(f"✅ Booking confirmed")

                # إرسال الإيميل
                try:
                    service = booking.servicebooking
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
                    logger.info(f"✅ Email sent for booking {booking.id}")
                except Exception as e:
                    logger.error(f"❌ Email sending failed: {e}")

    except Exception as e:
        logger.error(f"❌ Error in handle_payment_paid: {str(e)}", exc_info=True)


def handle_payment_failed(payment_data):
    moyasar_id = payment_data.get('id')
    
    try:
        payment = Payment.objects.get(moyasar_id=moyasar_id)
        payment.status = 'failed'
        payment.save()
        logger.info(f"Payment {moyasar_id} marked as failed")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment {moyasar_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment_failed: {str(e)}")


def handle_payment_refunded(payment_data):
    moyasar_id = payment_data.get('id')
    
    try:
        payment = Payment.objects.get(moyasar_id=moyasar_id)
        payment.status = 'refunded'
        payment.save()
        logger.info(f"Payment {moyasar_id} marked as refunded")
        
    except Payment.DoesNotExist:
        logger.warning(f"Payment {moyasar_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment_refunded: {str(e)}")


def update_invoice_on_payment_success(payment):
    """
    🔥 FIXED: تحديث الفاتورة عند نجاح الدفع
    """
    try:
        # محاولة جلب الفاتورة
        if not hasattr(payment, 'invoice'):
            # إنشاء فاتورة جديدة
            invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            amount_sar = Decimal(payment.amount) / 100
            
            Invoice.objects.create(
                payment=payment,
                invoice_number=invoice_number,
                amount=amount_sar,
                currency='SAR',
                description=payment.description,
                paid_at=timezone.now(),
                status='paid',
            )
            logger.info(f"✅ Invoice created: {invoice_number}")
        else:
            invoice = payment.invoice
            if not invoice.paid_at:
                invoice.paid_at = timezone.now()
                invoice.status = 'paid'
                invoice.save()
                logger.info(f"✅ Invoice {invoice.invoice_number} marked as paid")
                
    except Exception as e:
        logger.error(f"❌ Error updating invoice: {str(e)}", exc_info=True)


@csrf_exempt
def payment_callback_view(request):
    """
    🔥 FIXED: Callback URL بعد إتمام الدفع
    """
    try:
        print(f"\n{'='*60}")
        print(f"🔔 CALLBACK RECEIVED!")
        print(f"{'='*60}")
        print(f"GET Params: {dict(request.GET)}")
        print(f"{'='*60}\n")
        
        status = request.GET.get("status")
        moyasar_id = request.GET.get("id")
        payment_session_id = request.GET.get("session_id")

        logger.info(f"📞 Callback - Status: {status}, Moyasar ID: {moyasar_id}, Session: {payment_session_id}")

        payment = None
        invoice = None
        booking = None

        if moyasar_id:
            try:
                # محاولة جلب Payment بـ session_id أولاً
                if payment_session_id:
                    try:
                        pending_payment = Payment.objects.get(id=payment_session_id, status="pending_form")
                        logger.info(f"✅ Found pending payment: {pending_payment.id}")
                        
                        # التحقق إذا كان موجود بـ moyasar_id
                        existing_payment = Payment.objects.filter(moyasar_id=moyasar_id).first()
                        
                        if existing_payment:
                            logger.info(f"⚠️ Payment {moyasar_id} already exists (from webhook)")
                            pending_payment.delete()
                            payment = existing_payment
                        else:
                            # تحديث الـ pending
                            pending_payment.moyasar_id = moyasar_id
                            pending_payment.status = "initiated"
                            pending_payment.save()
                            payment = pending_payment
                            logger.info(f"✅ Updated pending payment")
                            
                    except Payment.DoesNotExist:
                        logger.warning(f"⚠️ Pending payment {payment_session_id} not found")
                
                # إذا لم نجد payment، نجلب من Moyasar
                if not payment:
                    payment_data, status_code = fetch_payment_api(moyasar_id)
                    
                    if status_code != 200:
                        logger.error(f"❌ Failed to fetch from Moyasar: {payment_data}")
                        raise Exception("Could not verify payment")

                    logger.info(f"✅ Payment data from Moyasar: {payment_data.get('status')}")

                    # استخراج booking_id
                    metadata = payment_data.get("metadata") or {}
                    booking_id = metadata.get("booking_id")
                    
                    booking = None
                    if booking_id:
                        try:
                            booking = Booking.objects.get(id=booking_id)
                            logger.info(f"✅ Found booking: {booking.id}")
                        except Booking.DoesNotExist:
                            logger.warning(f"⚠️ Booking {booking_id} not found")

                    # حفظ أو تحديث Payment
                    with transaction.atomic():
                        payment, created = Payment.objects.get_or_create(
                            moyasar_id=moyasar_id,
                            defaults={
                                "booking": booking,
                                "amount": payment_data.get("amount"),
                                "status": payment_data.get("status"),
                                "description": payment_data.get("description"),
                                "source_type": payment_data.get("source", {}).get("type"),
                            }
                        )
                        
                        if not created:
                            old_status = payment.status
                            payment.status = payment_data.get("status")
                            payment.amount = payment_data.get("amount")
                            
                            if not payment.booking and booking:
                                payment.booking = booking
                                
                            payment.save()
                            
                            logger.info(f"✅ Updated: {old_status} → {payment.status}")

                            # فك القفل لو نجح
                            if old_status != "paid" and payment.status == "paid":
                                if payment.booking:
                                    payment.booking.status = "confirmed"
                                    payment.booking.save()
                                    update_invoice_on_payment_success(payment)
                        else:
                            logger.info(f"✅ Created payment: {moyasar_id}")
                            
                            if payment.status == "paid" and payment.booking:
                                payment.booking.status = "confirmed"
                                payment.booking.save()
                                update_invoice_on_payment_success(payment)
                
                # تحديث الحجز إذا كان الدفع ناجح
                if payment and payment.status == "paid":
                    if payment.booking and payment.booking.status != "confirmed":
                        payment.booking.status = "confirmed"
                        payment.booking.save()
                        update_invoice_on_payment_success(payment)
                        logger.info(f"✅ Booking confirmed in callback")

                # جلب الفاتورة
                invoice = getattr(payment, "invoice", None)
                booking = payment.booking if payment else None
                        
            except Exception as e:
                logger.error(f"❌ Error in callback: {e}", exc_info=True)

        # التوجيه حسب الحالة
        if payment and payment.status == "paid":
            logger.info(f"✅ → SUCCESS PAGE")
            return render(request, "tourapp/payment_success.html", {
                "payment": payment,
                "invoice": invoice,
                "booking": booking,
            })
        else:
            logger.warning(f"⚠️ → FAILED PAGE")
            return render(request, "tourapp/payment_failed.html", {
                "payment": payment,
                "status": status,
                "moyasar_id": moyasar_id,
            })

    except Exception as e:
        logger.error(f"❌ Critical error in callback: {e}", exc_info=True)
        return render(request, "tourapp/payment_failed.html", {
            "error": "حدث خطأ في معالجة الدفعة"
        })


@api_view(["GET"])
def fetch_payment_view(request, moyasar_id):
    try:
        data, status_code = fetch_payment_api(moyasar_id)

        if status_code == 200:
            try:
                payment = Payment.objects.get(moyasar_id=moyasar_id)
                old_status = payment.status
                payment.status = data.get("status")
                payment.amount = data.get("amount")
                payment.save()

                if old_status != "paid" and payment.status == "paid":
                    update_invoice_on_payment_success(payment)

            except Payment.DoesNotExist:
                payment = None

            return Response({
                "moyasar_data": data,
                "local_payment": PaymentSerializer(payment).data if payment else None
            })
        else:
            return Response({"error": data}, status=status_code)
    except Exception as e:
        logger.error(f"Error in fetch_payment_view: {str(e)}")
        return Response({"error": str(e)}, status=500)