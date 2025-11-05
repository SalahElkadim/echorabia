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
    🔥 FIXED: Webhook endpoint لاستقبال التحديثات من Moyasar
    """
    try:
        payload = json.loads(request.body)
        event_type = payload.get('type')
        payment_data = payload.get('data', {})
        moyasar_id = payment_data.get('id')
        
        logger.info(f"📞 Webhook received: {event_type} for {moyasar_id}")
        
        try:
            if event_type == 'payment_paid':
                handle_payment_paid(payment_data)
            elif event_type == 'payment_failed':
                handle_payment_failed(payment_data)
            elif event_type == 'payment_refunded':
                handle_payment_refunded(payment_data)
        except Exception as e:
            logger.error(f"❌ Webhook processing error: {str(e)}", exc_info=True)
        
        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"❌ Webhook parse error: {str(e)}", exc_info=True)
        return HttpResponse("OK", status=200)


def handle_payment_paid(payment_data):
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

        # ✅ إنشاء الفاتورة (سريع)
        try:
            update_invoice_on_payment_success(payment)
        except Exception as e:
            logger.error(f"❌ Invoice creation failed: {e}")
        
        # ✅ إرسال الإيميل في background (بدون انتظار)
        if payment.booking:
            from threading import Thread
            email_thread = Thread(target=send_booking_confirmation_email, args=(payment.booking,))
            email_thread.daemon = True
            email_thread.start()
            logger.info(f"✅ Email task started in background")

    except Exception as e:
        logger.error(f"❌ Error in handle_payment_paid: {str(e)}", exc_info=True)


def send_booking_confirmation_email(booking):
    """
    🔥 FIXED: إرسال إيميل التأكيد (يشتغل في background)
    - مش هيبطئ الـ webhook
    - fail_silently=True عشان ما يكسرش الـ flow
    """
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
            fail_silently=True,  # ✅ مش critical
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
    🔥 ULTIMATE FIX: Callback URL بعد إتمام الدفع
    - ننتظر ALWAYS قبل ما نبدأ نبحث
    - polling مكثف للتأكد من تحديث الـ status
    """
    try:
        status = request.GET.get("status")
        moyasar_id = request.GET.get("id")
        payment_session_id = request.GET.get("session_id")
        message = request.GET.get("message", "")

        logger.info(f"📞 Callback RECEIVED: status={status}, moyasar_id={moyasar_id}, session={payment_session_id}")

        payment = None
        invoice = None
        booking = None
        
        # ✅ CRITICAL: ننتظر 3 ثواني في البداية لإعطاء الـ webhook فرصة
        import time
        logger.info(f"⏳ Waiting 3 seconds for webhook to process...")
        time.sleep(3)

        # ✅ Strategy 1: البحث بـ session_id (أضمن طريقة)
        if payment_session_id:
            logger.info(f"🔍 Strategy 1: Looking for session_id={payment_session_id}")
            try:
                # نحاول نلاقي الـ payment ونتأكد من تحديث الـ status
                for attempt in range(8):  # 8 محاولات × 2 ثانية = 16 ثانية
                    payment = Payment.objects.select_related('booking', 'invoice').get(id=payment_session_id)
                    logger.info(f"🔄 Attempt {attempt + 1}: Found payment ID={payment.id}, moyasar={payment.moyasar_id}, status={payment.status}")
                    
                    # ✅ إذا الـ status بقى paid، نخرج
                    if payment.status == 'paid':
                        logger.info(f"🎉 Payment is PAID! Success!")
                        break
                    
                    # ✅ إذا الـ moyasar_id اتحدث من PENDING لـ ID حقيقي، كويس!
                    if payment.moyasar_id and not payment.moyasar_id.startswith('PENDING-'):
                        logger.info(f"✅ Moyasar ID updated: {payment.moyasar_id}")
                        # نكمل polling عشان الـ status يتحدث
                    
                    # ننتظر قبل المحاولة التالية
                    if attempt < 7:
                        time.sleep(2)
                    
            except Payment.DoesNotExist:
                logger.error(f"❌ Session {payment_session_id} not found!")
        
        # ✅ Strategy 2: البحث بـ moyasar_id (لو موجود)
        if not payment and moyasar_id and not moyasar_id.startswith('PENDING-'):
            logger.info(f"🔍 Strategy 2: Looking for moyasar_id={moyasar_id}")
            
            for attempt in range(5):
                payment = Payment.objects.select_related('booking', 'invoice').filter(
                    moyasar_id=moyasar_id
                ).first()
                
                if payment and payment.status == 'paid':
                    logger.info(f"✅ Found PAID payment by moyasar_id")
                    break
                
                if attempt < 4:
                    time.sleep(2)

        # ✅ Strategy 3: آخر حل - نجلب من Moyasar API
        if not payment and moyasar_id and not moyasar_id.startswith('PENDING-'):
            logger.info(f"🔍 Strategy 3: Fetching from Moyasar API: {moyasar_id}")
            try:
                payment_data, status_code = fetch_payment_api(moyasar_id)
                
                if status_code == 200:
                    logger.info(f"✅ Moyasar API returned: status={payment_data.get('status')}")
                    
                    # استخراج booking من description
                    description = payment_data.get('description', '')
                    booking = None
                    if 'Booking #' in description:
                        try:
                            booking_id = description.split('Booking #')[1].split(' ')[0].split('-')[0]
                            booking = Booking.objects.get(id=booking_id)
                            logger.info(f"✅ Found booking: {booking_id}")
                        except Exception as e:
                            logger.error(f"❌ Failed to extract booking: {e}")

                    with transaction.atomic():
                        payment = Payment.objects.create(
                            moyasar_id=moyasar_id,
                            booking=booking,
                            amount=payment_data.get("amount"),
                            status=payment_data.get("status"),
                            description=payment_data.get("description"),
                            source_type=payment_data.get("source", {}).get("type"),
                            paid_at=timezone.now() if payment_data.get("status") == "paid" else None,
                        )
                        logger.info(f"✅ Created payment from Moyasar API: ID={payment.id}, status={payment.status}")
                        
                        if payment.status == "paid" and payment.booking:
                            payment.booking.confirmed = True
                            payment.booking.save()
                            update_invoice_on_payment_success(payment)
                            logger.info(f"✅ Booking confirmed and invoice created")
                else:
                    logger.error(f"❌ Moyasar API failed: status_code={status_code}")
            except Exception as e:
                logger.error(f"❌ Error fetching from Moyasar: {e}", exc_info=True)

        # جلب الفاتورة والحجز
        if payment:
            # ✅ أعد جلب الـ payment من الداتابيز للتأكد من آخر تحديث
            payment.refresh_from_db()
            
            invoice = getattr(payment, "invoice", None)
            booking = payment.booking
            
            # التأكد من تحديث حالة الحجز
            if payment.status == "paid" and booking and booking.confirmed != True:
                booking.confirmed = True
                booking.save()
                logger.info(f"✅ Booking {booking.id} confirmed in callback")

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
                "status": status if status else (payment.status if payment else "unknown"),
                "moyasar_id": moyasar_id,
                "message": message,
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