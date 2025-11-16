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
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        service = booking.servicebooking
        
        # حساب المبلغ
        amount_sar = booking.price.total_price
        amount_halalah = int(amount_sar * 100)
        
        logger.info(f"🎬 Payment page for booking {booking_id}, amount: {amount_halalah}")
        
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
                
                logger.info(f"✅ Created pending payment: ID={pending_payment.id}, Moyasar ID={pending_payment.moyasar_id}")
                payment_session_id = str(pending_payment.id)
                
        except Exception as e:
            logger.error(f"❌ Failed to create pending payment: {e}", exc_info=True)
            return render(request, "error.html", {"message": "Failed to initialize payment"})
        
        context = {
            "moyasar_key": settings.MOYASAR_PUBLISHABLE_KEY,
            "booking_id": booking.id,
            "amount": amount_halalah,
            "payment_session_id": payment_session_id,
        }
        
        logger.info(f"✅ Rendering payment page with session_id: {payment_session_id}")
        return render(request, "payment.html", context)
        
    except Exception as e:
        logger.error(f"❌ Error in payment_page: {e}", exc_info=True)
        return render(request, "error.html", {"message": str(e)})


@csrf_exempt
@require_POST
def moyasar_webhook(request):
    """
    🔥 FIXED: نرجع response بسرعة قبل ما Moyasar تقطع
    """
    try:
        payload = json.loads(request.body)
        event_type = payload.get('type')
        payment_data = payload.get('data', {})
        moyasar_id = payment_data.get('id')
        
        logger.info(f"📞 Webhook received: {event_type} for {moyasar_id}")
        
        # ✅ نرجع response فوراً (خلال milliseconds)
        response = HttpResponse("OK", status=200)
        
        # ✅ بعد ما نرجع response، نشتغل في background
        if event_type == 'payment_paid':
            # نحفظ البيانات في الـ database بسرعة
            try:
                handle_payment_paid_fast(payment_data)
            except Exception as e:
                logger.error(f"❌ Webhook processing error: {str(e)}", exc_info=True)
        elif event_type == 'payment_failed':
            handle_payment_failed(payment_data)
        elif event_type == 'payment_refunded':
            handle_payment_refunded(payment_data)
        
        return response

    except Exception as e:
        logger.error(f"❌ Webhook parse error: {str(e)}", exc_info=True)
        return HttpResponse("OK", status=200)


def handle_payment_paid_fast(payment_data):
    """
    🔥 FIXED: معالجة webhook للدفع الناجح
    """
    try:
        moyasar_id = payment_data.get("id")
        if not moyasar_id:
            return

        logger.info(f"🔔 Processing payment_paid: {moyasar_id}")

        # استخراج session_id من callback_url
        callback_url = payment_data.get('callback_url', '')
        session_id = None
        
        if 'session_id=' in callback_url:
            try:
                session_id = callback_url.split('session_id=')[1].split('&')[0]
            except:
                pass

        # استخراج booking من description
        description = payment_data.get('description', '')
        booking = None
        if 'Booking #' in description:
            try:
                booking_id = description.split('Booking #')[1].split(' ')[0].split('-')[0]
                booking = Booking.objects.get(id=booking_id)
            except:
                pass

        with transaction.atomic():
            payment = None
            
            # محاولة جلب بـ session_id
            if session_id:
                try:
                    payment = Payment.objects.select_for_update().get(id=session_id)
                    payment.moyasar_id = moyasar_id
                    payment.status = "paid"
                    payment.paid_at = timezone.now()
                    payment.amount = payment_data.get("amount", payment.amount)
                    
                    if not payment.booking and booking:
                        payment.booking = booking
                    
                    payment.save()
                    logger.info(f"✅ Updated payment {session_id} to paid")
                except Payment.DoesNotExist:
                    logger.warning(f"⚠️ Session {session_id} not found")
            
            # إذا مش موجود، نحاول بـ moyasar_id
            if not payment:
                try:
                    payment = Payment.objects.get(moyasar_id=moyasar_id)
                    payment.status = "paid"
                    payment.paid_at = timezone.now()
                    payment.save()
                    logger.info(f"✅ Updated payment by moyasar_id")
                except Payment.DoesNotExist:
                    # إنشاء جديد
                    payment = Payment.objects.create(
                        moyasar_id=moyasar_id,
                        booking=booking,
                        amount=payment_data.get("amount"),
                        status="paid",
                        paid_at=timezone.now(),
                        description=payment_data.get("description"),
                        source_type=payment_data.get("source", {}).get("type"),
                    )
                    logger.info(f"✅ Created new payment")

            # ✅ FIX: تحديث الحجز بدون update_fields
            if payment.booking:
                payment.booking.confirmed = True
                payment.booking.save()  # ✅ بدون update_fields=['status']
                logger.info(f"✅ Booking confirmed")
                # 🔥 Send confirmation email

        # ✅ إنشاء الفاتورة (سريع)
        try:
            update_invoice_on_payment_success(payment)
        except Exception as e:
            logger.error(f"❌ Invoice creation failed: {e}")

    except Exception as e:
        logger.error(f"❌ Error in handle_payment_paid: {str(e)}", exc_info=True)


def send_booking_confirmation_email(booking):
    """
    🔥 FIXED: إرسال إيميل التأكيد (يشتغل في background)
    - مش هيبطئ الـ webhook
    - fail_silently=True عشان ما يكسرش الـ flow
    """
    try:
        
        subject = f'New Booking:'
        message = "new booking has been confirmed"
        send_mail(
            subject,
            message,
            from_email='sm249481@gmail.com',
            recipient_list=['salah.mohamed.elkadim@gmail.com'],
            fail_silently=False,  # ✅ مش critical
        )
        logger.info(f"✅ Email sent successfully for booking {booking.id}")
    except Exception as e:
        logger.error(f"❌ Email failed for booking {booking.id}: {e}", exc_info=True)

def handle_payment_failed(payment_data):
    """
    🔥 FIXED: معالجة webhook للدفع الفاشل
    """
    try:
        moyasar_id = payment_data.get('id')
        if not moyasar_id:
            return
        
        logger.info(f"🔔 Processing payment_failed: {moyasar_id}")
        
        # استخراج session_id
        callback_url = payment_data.get('callback_url', '')
        session_id = None
        
        if 'session_id=' in callback_url:
            try:
                session_id = callback_url.split('session_id=')[1].split('&')[0]
            except:
                pass
        
        with transaction.atomic():
            payment = None
            
            # محاولة جلب بـ session_id
            if session_id:
                try:
                    payment = Payment.objects.select_for_update().get(id=session_id)
                    payment.moyasar_id = moyasar_id
                    payment.status = "failed"
                    payment.amount = payment_data.get("amount", payment.amount)
                    payment.save()
                    logger.info(f"✅ Updated payment {session_id} to failed")
                except Payment.DoesNotExist:
                    pass
            
            if not payment:
                try:
                    payment = Payment.objects.get(moyasar_id=moyasar_id)
                    payment.status = 'failed'
                    payment.save()
                    logger.info(f"✅ Updated payment to failed")
                except Payment.DoesNotExist:
                    payment = Payment.objects.create(
                        moyasar_id=moyasar_id,
                        amount=payment_data.get("amount"),
                        status="failed",
                        description=payment_data.get("description"),
                        source_type=payment_data.get("source", {}).get("type"),
                    )
                    logger.info(f"✅ Created new failed payment")
        
    except Exception as e:
        logger.error(f"❌ Error in handle_payment_failed: {str(e)}", exc_info=True)


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
        if not hasattr(payment, 'invoice'):
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
    🔥 NEW: صفحة callback بسيطة - بدون تفاصيل
    فقط زر للتأكيد
    """
    try:
        status = request.GET.get("status")
        moyasar_id = request.GET.get("id")
        payment_session_id = request.GET.get("session_id")
        message = request.GET.get("message", "")

        logger.info(f"📞 Callback RECEIVED: status={status}, moyasar_id={moyasar_id}, session={payment_session_id}")

        # ✅ إذا الدفع فشل، نوجه مباشرة لصفحة الفشل
        if status == "failed":
            logger.warning(f"⚠️ Payment failed immediately")
            return render(request, "tourapp/payment_failed.html", {
                "status": status,
                "moyasar_id": moyasar_id,
                "message": message,
            })

        # ✅ نعرض صفحة الانتظار مع زر التأكيد
        return render(request, "tourapp/payment_callback.html", {
            "payment_session_id": payment_session_id,
            "moyasar_id": moyasar_id,
            "status": status,
        })

    except Exception as e:
        logger.error(f"❌ Error in callback: {e}", exc_info=True)
        return render(request, "tourapp/payment_failed.html", {
            "error": "حدث خطأ في معالجة الدفعة"
        })
    

@csrf_exempt
def confirm_booking_view(request, payment_session_id):
    """
    🔥 NEW: تأكيد الحجز + إرسال الإيميل + عرض التفاصيل
    """
    try:
        logger.info(f"🔔 Confirming booking for session: {payment_session_id}")
        
        payment = None
        invoice = None
        booking = None
        
        # ✅ Strategy 1: البحث بـ session_id
        try:
            payment = Payment.objects.select_related('booking', 'invoice').get(id=payment_session_id)
            logger.info(f"✅ Found payment: ID={payment.id}, status={payment.status}")
        except Payment.DoesNotExist:
            logger.error(f"❌ Payment session {payment_session_id} not found!")
        
        # ✅ Strategy 2: إذا Payment موجود بس الـ status لسه مش paid
        if payment and payment.status != 'paid':
            # نحاول نجلب من Moyasar API
            moyasar_id = payment.moyasar_id
            if moyasar_id and not moyasar_id.startswith('PENDING-'):
                logger.info(f"🔍 Fetching from Moyasar API: {moyasar_id}")
                try:
                    payment_data, status_code = fetch_payment_api(moyasar_id)
                    
                    if status_code == 200 and payment_data.get('status') == 'paid':
                        # تحديث الـ payment
                        with transaction.atomic():
                            payment.status = 'paid'
                            payment.paid_at = timezone.now()
                            payment.amount = payment_data.get("amount", payment.amount)
                            payment.save()
                            
                            # تحديث الحجز
                            if payment.booking:
                                payment.booking.confirmed = True
                                payment.booking.save()
                                logger.info(f"✅ Booking confirmed")
                            
                            # إنشاء الفاتورة
                            update_invoice_on_payment_success(payment)
                            
                        logger.info(f"✅ Payment updated from Moyasar API")
                    
                except Exception as e:
                    logger.error(f"❌ Error fetching from Moyasar: {e}", exc_info=True)
        
        # ✅ Strategy 3: آخر محاولة - نتحقق مرة أخرى
        if payment:
            payment.refresh_from_db()
            invoice = getattr(payment, "invoice", None)
            booking = payment.booking
        
        # ✅ إرسال الإيميل في background thread (عشان ما يبطئش الـ response)
        if payment and payment.status == 'paid' and booking:
            try:
                import threading
                logger.info(f"📧 Sending confirmation email in background...")
                email_thread = threading.Thread(
                    target=send_booking_confirmation_email,
                    args=(booking,),
                    daemon=True
                )
                email_thread.start()
                logger.info(f"✅ Email thread started")
            except Exception as e:
                logger.error(f"❌ Email thread failed: {e}", exc_info=True)
                # نكمل حتى لو الإيميل فشل
        
        # ✅ التوجيه حسب الحالة
        if payment and payment.status == "paid":
            logger.info(f"✅ → SUCCESS PAGE with full details")
            return render(request, "tourapp/payment_success.html", {
                "payment": payment,
                "invoice": invoice,
                "booking": booking,
            })
        else:
            logger.warning(f"⚠️ → FAILED PAGE - Payment not confirmed")
            return render(request, "tourapp/payment_failed.html", {
                "payment": payment,
                "status": payment.status if payment else "unknown",
                "message": "لم يتم تأكيد الدفع. الرجاء المحاولة مرة أخرى أو التواصل مع الدعم الفني.",
            })

    except Exception as e:
        logger.error(f"❌ Critical error in confirm_booking: {e}", exc_info=True)
        return render(request, "tourapp/payment_failed.html", {
            "error": "حدث خطأ في تأكيد الحجز"
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