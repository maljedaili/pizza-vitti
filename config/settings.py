import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-me')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,pizza-vitti.onrender.com,pizza-vitti.kayen.fr,pizza-vitti.kayan.fr').split(',')]
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')
WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER', '')
GOOGLE_REVIEW_URL = os.getenv('GOOGLE_REVIEW_URL', 'https://www.google.com/search?q=Pizza+Vitti+Bordeaux+avis')
INSTAGRAM_URL = os.getenv('INSTAGRAM_URL', 'https://www.instagram.com/')
FACEBOOK_URL = os.getenv('FACEBOOK_URL', 'https://www.facebook.com/')
GOOGLE_PLAY_URL = os.getenv('GOOGLE_PLAY_URL', '')
KITCHEN_PASSWORD = os.getenv('KITCHEN_PASSWORD', '123')
OWNER_DASHBOARD_USERNAME = os.getenv('OWNER_DASHBOARD_USERNAME', 'admin')
OWNER_DASHBOARD_PASSWORD = os.getenv('OWNER_DASHBOARD_PASSWORD', '')
OWNER_DASHBOARD_PASSWORD_HASH = os.getenv(
    'OWNER_DASHBOARD_PASSWORD_HASH',
    'pbkdf2_sha256$870000$ZAM7PoIlG2qUZ1Da4cJfwA$OQEEyAiH1EBf5ilBOFpk8jJDizThAs/G3IrcgTFj1ug=',
)
ANDROID_APP_PACKAGE = os.getenv('ANDROID_APP_PACKAGE', 'fr.kayen.pizzavitti')
ANDROID_CERT_SHA256_FINGERPRINTS = [
    fingerprint.strip().upper()
    for fingerprint in os.getenv(
        'ANDROID_CERT_SHA256_FINGERPRINTS',
        '2E:AF:ED:BC:64:E1:4A:51:0A:D1:93:43:EB:50:69:FF:14:30:E2:16:7E:24:C6:6F:AB:EE:86:9E:9B:E0:85:6D',
    ).split(',')
    if fingerprint.strip()
]
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Pizza Vitti <no-reply@pizza-vitti.fr>')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django.contrib.sitemaps', 'django.contrib.sites',
    'allauth', 'allauth.account', 'allauth.socialaccount', 'allauth.socialaccount.providers.google',
    'shop'
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'allauth.account.middleware.AccountMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug', 'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages',
        'shop.context_processors.site_settings', 'shop.context_processors.cart_info'
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    parsed = urlparse(DATABASE_URL)
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql', 'NAME': parsed.path.lstrip('/'),
        'USER': parsed.username, 'PASSWORD': parsed.password, 'HOST': parsed.hostname, 'PORT': parsed.port or 5432,
    }}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_PASSWORD_VALIDATORS = []
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_FORMS = {'signup': 'shop.forms.CustomerSignupForm'}
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
