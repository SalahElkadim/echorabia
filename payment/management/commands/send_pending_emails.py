from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from payment.models import Payment
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send pending booking confirmation emails'

    def handle(self, *args, **options):
        # نجيب الـ payments اللي confirmed لكن الإيميل مش متبعت
        pending = Payment.objects.filter(
            status='paid',
            booking__confirmed=True,
            email_sent=False  # ⬅️ هنضيف الـ field ده
        ).select_related('booking__servicebooking')
        
        for payment in pending:
            try:
                booking = payment.booking
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
                    ['sm249481@gmail.com'],
                    fail_silently=False,  # ⬅️ عشان نشوف الـ errors
                )
                
                # ✅ نعلّم إنه اتبعت
                payment.email_sent = True
                payment.save(update_fields=['email_sent'])
                
                logger.info(f"✅ Email sent for payment {payment.id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to send email for payment {payment.id}: {e}")