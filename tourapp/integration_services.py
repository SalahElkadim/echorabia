import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings

# بيانات الدخول اللي الوزارة هتديهالك
MT_USERNAME = getattr(settings, "MT_USERNAME", "")
MT_PASSWORD = getattr(settings, "MT_PASSWORD", "")
BASE_URL = "https://prod-api.mt.gov.sa/gateway/TLG/1.0/"  # أو الـ Sandbox لو للتجارب

# 🧭 دالة للتحقق من شركة تنظيم رحلات
def get_tour_operator_license_details(id_no, license_no, commercial_no):
    url = f"{BASE_URL}getTourOperatorLicenseDetails"
    payload = {
        "idNo": id_no,
        "licenseNo": license_no,
        "commercialRecordNo": commercial_no
    }
    response = requests.post(url, json=payload, auth=HTTPBasicAuth(MT_USERNAME, MT_PASSWORD))
    return response.json()

# 👥 دالة للتحقق من مرشد سياحي
def get_tour_guide_license_details(id_no, license_no):
    url = f"{BASE_URL}getTourGuideLicenseDetails"
    payload = {
        "idNo": id_no,
        "licenseNo": license_no
    }
    response = requests.post(url, json=payload, auth=HTTPBasicAuth(MT_USERNAME, MT_PASSWORD))
    return response.json()
