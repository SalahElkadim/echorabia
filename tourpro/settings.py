import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-%e@cg%)coz(6q-fh)fvv*s5$pj+9g%sog%(8u4%)pjkn^p5#a0'

CLOUDINARY_CLOUD_NAME='dwbj2vy74'
CLOUDINARY_API_KEY='284199794227834'
CLOUDINARY_API_SECRET='yCEYIorrpcNScBUf-TjeffHQRjg'
USE_L10N = False

MOYASAR_SECRET_KEY = os.getenv("MOYASAR_SECRET_KEY")
MOYASAR_PUBLISHABLE_KEY = os.getenv("MOYASAR_PUBLISHABLE_KEY")
MOYASAR_WEBHOOK_SECRET = os.getenv("MOYASAR_WEBHOOK_SECRET")



ALLOWED_HOSTS = [
    'echorabia-production.up.railway.app',
    '127.0.0.1',
    'localhost',
    'echorabia.com', 'www.echorabia.com'
]

CSRF_TRUSTED_ORIGINS = ['https://echorabia-production.up.railway.app','https://echorabia.com', 'https://www.echorabia.com']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tourapp',
    'cloudinary',
    'cloudinary_storage',
    'rest_framework',
    'payment',
]
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dwbj2vy74',
    'API_KEY': '284199794227834',
    'API_SECRET': 'yCEYIorrpcNScBUf-TjeffHQRjg'
}
import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.config(
    cloud_name='dwbj2vy74',
    api_key='284199794227834',
    api_secret='yCEYIorrpcNScBUf-TjeffHQRjg'
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tourpro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tourpro.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.parse(
        'postgresql://postgres:iFLLjpxnvXaevDLiEZZbGSAtjEJvrDwe@shinkansen.proxy.rlwy.net:31748/railway',
        conn_max_age=600,
        engine='django.db.backends.postgresql_psycopg2'
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'tourapp.CustomUser'

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'


FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'echorabia@gmail.com'
EMAIL_HOST_PASSWORD = 'tjfj smhr ejil khyv'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
DEBUG = False
# إعدادات الأمان عند تفعيل HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# مهم جداً مع Railway ونطاق مخصص
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')