from django.urls import path
from .views import (
    payment_page,
    payment_callback_view,
    moyasar_webhook,
    fetch_payment_view,confirm_booking_view, payment_details_view,invoice_details_view
)

urlpatterns = [
    # ✅ صفحة الدفع (الصفحة الرئيسية)
    path("pay/<int:booking_id>/", payment_page, name="payment_page"),
    
    # ✅ Callback بعد إتمام الدفع (يرجع المستخدم هنا بعد 3D Secure)
    path('callback/', payment_callback_view, name='payment-callback'),
    
    # ✅ Webhook endpoint (Moyasar يرسل التحديثات هنا)
    path('webhook/', moyasar_webhook, name='moyasar-webhook'),
    
    # ✅ جلب تفاصيل دفعة معينة (optional - للـ debugging)
    path('fetch/<str:moyasar_id>/', fetch_payment_view, name='fetch-payment'),
    path('confirm-booking/<int:payment_session_id>/', confirm_booking_view, name='confirm_booking'),
    # تفاصيل الدفع والفاتورة
    path('details/<int:payment_id>/', payment_details_view, name='payment_details'),
    path('invoice/<int:invoice_id>/', invoice_details_view, name='invoice_details'),

]