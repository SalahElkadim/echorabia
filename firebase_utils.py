import firebase_admin
from firebase_admin import credentials, storage
import json
import os

# تحميل بيانات الاتصال من المتغير البيئي
firebase_config = json.loads(os.environ['FIREBASE_CONFIG'])

# إصلاح private_key من \\n إلى \n
firebase_config['private_key'] = firebase_config['private_key'].replace('\\n', '\n')

# إنشاء الشهادة
cred = credentials.Certificate(firebase_config)

# تهيئة التطبيق (مرة واحدة فقط)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'echorabia-f8f1a.appspot.com'
    })

def upload_file_to_firebase(file, file_name):
    bucket = storage.bucket()
    blob = bucket.blob(file_name)
    blob.upload_from_file(file)

    # جعل الملف متاح للجميع (Public)
    blob.make_public()

    return blob.public_url
