import firebase_admin
from firebase_admin import credentials, storage
import json
import os

# تحميل بيانات الاتصال
firebase_config = json.loads(os.environ['FIREBASE_CONFIG'])
cred = credentials.Certificate(firebase_config)
# تهيئة التطبيق (مرة واحدة فقط)
firebase_admin.initialize_app(cred, {
    'storageBucket': f"{firebase_config['project_id']}.appspot.com"
})

def upload_file_to_firebase(file, file_name):
    bucket = storage.bucket()
    blob = bucket.blob(file_name)
    blob.upload_from_file(file)

    # جعل الملف متاح للجميع (Public)
    blob.make_public()

    return blob.public_url
