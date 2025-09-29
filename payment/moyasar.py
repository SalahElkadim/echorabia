import requests
import uuid
from django.conf import settings
import json

def create_payment( amount, currency="SAR", description=None, source=None, metadata=None):
    url = "https://api.moyasar.com/v1/payments"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "given_id": str(uuid.uuid4()),   # توليد UUID لكل عملية
        "amount": amount,
        "currency": currency,
        "description": description,
        "callback_url": "https://echorabia.com/payment/callback/",
        "source": source,
        "metadata": metadata,
        "apply_coupon": True
    }

    response = requests.post(
        url,
        auth=(settings.MOYASAR_SECRET_KEY, ""),  # Basic Auth: key + empty password
        json=payload
    )

    return response.json()


def fetch_payment(payment_id):
    url = f"https://api.moyasar.com/v1/payments/{payment_id}"
    headers = {
        'Accept': 'application/json',
    }
    response = requests.get(
            url,
            auth=(settings.MOYASAR_SECRET_KEY, ""),  # Basic Auth: key + empty password
    )    
    return response.json(), response.status_code


def list_payments():
    """
    جلب كل الدفعات من Moyasar
    """
    url = "https://api.moyasar.com/v1/payments"
    
    try:
        response = requests.get(
            url,
            auth=(settings.MOYASAR_SECRET_KEY, ""),  # Basic Auth: secret key + empty password
            headers={"Accept": "application/json"}
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}