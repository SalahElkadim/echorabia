from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import base64, requests
from tourapp.models import Booking
from .models import Payment

@method_decorator(csrf_exempt, name='dispatch')
class CreatePaymentAPIView(APIView):

    def post(self, request):
        booking_id = request.data.get('booking_id')

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        if not booking.servicebooking:
            return Response({'error': 'Booking has no associated service'}, status=status.HTTP_400_BAD_REQUEST)

        amount = booking.servicebooking.cost * 100  # Moyasar بالهللة

        # إنشاء الدفع باستخدام API Moyasar
        url = "https://api.moyasar.com/v1/payments"
        api_key = settings.MOYASAR_SECRET_KEY  # sk_test_xxxxxxxx
        auth_header = base64.b64encode(f"{api_key}:".encode()).decode()

        headers = {
            "Authorization": f"Basic {auth_header}"
        }
        data = {
            "amount": amount,
            "currency": "SAR",
            "description": "test",
            "callback_url": request.build_absolute_uri('/api/payment/callback/'),
            "source": {
            "type": "creditcard"
    }
}



        response = requests.post(url, data=data, headers=headers)
        if response.status_code != 201:
            return Response({'error': 'Failed to create payment', 'details': response.json()},
                            status=response.status_code)

        payment_data = response.json()

        # حفظ الـ payment ID في موديلنا
        payment_record = Payment.objects.create(
            booking=booking,
            amount=booking.servicebooking.cost,
            status='pending',
            transaction_id=payment_data['id']
        )

        return Response({
            'payment_id': payment_data['id'],
        "status": payment_data["status"]
        }, status=status.HTTP_201_CREATED)



# استقبال Webhook من بوابة الدفع
class PaymentCallbackAPIView(APIView):
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        status_str = request.data.get('status')  # 'paid' أو 'failed'

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        payment.status = status_str
        payment.save()

        if status_str == 'paid':
            payment.booking.confirmed = True
            payment.booking.save()

        return Response({'success': True})
