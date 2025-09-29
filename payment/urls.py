from django.urls import path
from .views import CreatePaymentView,payment_callback_view,moyasar_webhook

urlpatterns = [
    path("create/", CreatePaymentView.as_view(), name="create-payment"),
     path('callback/', payment_callback_view, name='payment-callback'),
    path('webhook/', moyasar_webhook, name='moyasar-webhook'),

]
