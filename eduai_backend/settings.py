from pathlib import Path
from datetime import timedelta
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"

ALLOWED_HOSTS: list[str] = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # uchinchi tomon paketlar
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "channels",
    # mahalliy ilovalar
    "accounts",
    "courses",
    "learning",
    "ai_pipeline",
    "analytics",                                                                      "storages",                        
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "eduai_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "eduai_backend.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Til va vaqt sozlamalari – o‘zbekcha interfeys uchun
LANGUAGE_CODE = "uz"

TIME_ZONE = "Asia/Tashkent"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# React frontend bilan ishlash uchun CORS
CORS_ALLOW_ALL_ORIGINS = True

# Swagger / OpenAPI 3.0 (drf-spectacular)
SPECTACULAR_SETTINGS = {
    "TITLE": "EduAI API",
    "DESCRIPTION": "EduAI ta'lim platformasi REST API – autentifikatsiya, kurslar, resurslar, testlar, progress va bildirishnomalar.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api",
    "SECURITY": [{"bearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Login yoki Register orqali olingan access token. Format: Bearer <token>",
            }
        }
    },
}

# ══════════════════════════════════════════════
# AI SERVICES CONFIGURATION
# ══════════════════════════════════════════════
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'sJ8GED3d0sN1d0bmD6mH')
KLING_ACCESS_KEY = os.environ.get('KLING_ACCESS_KEY')
KLING_SECRET_KEY = os.environ.get('KLING_SECRET_KEY')
# Backward compatibility
KLING_API_KEY = KLING_ACCESS_KEY

# Development mode - use mock responses if APIs fail
USE_MOCK_AI_RESPONSES = os.environ.get('USE_MOCK_AI_RESPONSES', 'true').lower() == 'true'

# ══════════════════════════════════════════════
# AWS S3 & CLOUDFRONT CONFIGURATION
# ══════════════════════════════════════════════
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-southeast-1')
AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
AWS_CLOUDFRONT_URL = os.environ.get('AWS_CLOUDFRONT_URL')

# ══════════════════════════════════════════════
# CELERY & REDIS CONFIGURATION
# ══════════════════════════════════════════════
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ══════════════════════════════════════════════
# DJANGO CHANNELS CONFIGURATION
# ══════════════════════════════════════════════
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379')],
        },
    }
}

ASGI_APPLICATION = "eduai_backend.asgi.application"

# ══════════════════════════════════════════════
# STRIPE CONFIGURATION
# ══════════════════════════════════════════════
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# ══════════════════════════════════════════════
# FILE UPLOAD CONFIGURATION
# ══════════════════════════════════════════════
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_UPLOAD_TYPES = ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'txt']

# ══════════════════════════════════════════════
# CORS CONFIGURATION
# ══════════════════════════════════════════════
CORS_ALLOWED_ORIGINS = [
    os.environ.get('FRONTEND_URL', 'http://localhost:3000'),
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# ══════════════════════════════════════════════
# JWT CONFIGURATION
# ══════════════════════════════════════════════
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ══════════════════════════════════════════════
# STORAGE CONFIGURATION
# ══════════════════════════════════════════════
if os.environ.get('USE_SUPABASE', 'false').lower() == 'true':
    # Supabase S3 sozlamalari
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = 'media'
    AWS_S3_REGION_NAME = 'ap-southeast-1'
    AWS_S3_ENDPOINT_URL = os.environ.get('SUPABASE_URL') + '/storage/v1/s3'
    AWS_S3_ADDRESSING_STYLE = 'path'
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    MEDIA_URL = (
        os.environ.get('SUPABASE_URL')
        + '/storage/v1/object/public/media/'
    )
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"