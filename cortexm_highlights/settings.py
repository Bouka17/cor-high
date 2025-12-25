from pathlib import Path
import os

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "change-me"),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, "postgres://cortexm:cortexm@db:5432/cortexm"),
    REDIS_URL=(str, "redis://redis:6379/0"),
    STORAGE_BACKEND=(str, "local"),
)

if env.bool("DJANGO_READ_DOT_ENV", default=True):
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "channels",
    "storages",
    "highlights",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cortexm_highlights.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "cortexm_highlights.wsgi.application"
ASGI_APPLICATION = "cortexm_highlights.asgi.application"

DATABASES = {"default": env.db()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"

FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = None
FILE_UPLOAD_TEMP_DIR = str(BASE_DIR / "media" / "tmp")
os.makedirs(FILE_UPLOAD_TEMP_DIR, exist_ok=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

REDIS_URL = env("REDIS_URL")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60

# Windows Compatibility: 
# The default 'prefork' (spawn on Windows) pool has known issues with permission errors 
# on shared resources. 'solo' is the most stable pool for Windows development.
if os.name == 'nt':
    CELERY_WORKER_POOL = 'solo'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
if STORAGE_BACKEND == "s3":
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
    AWS_QUERYSTRING_AUTH = False
elif STORAGE_BACKEND == "azure":
    DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
    AZURE_ACCOUNT_NAME = env("AZURE_ACCOUNT_NAME", default="")
    AZURE_ACCOUNT_KEY = env("AZURE_ACCOUNT_KEY", default="")
    AZURE_CONTAINER = env("AZURE_CONTAINER", default="")
