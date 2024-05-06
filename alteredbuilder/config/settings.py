"""
Django settings for alteredbuilder project.

Generated by 'django-admin startproject' using Django 5.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import io
import os
from pathlib import Path
from urllib.parse import urlparse

import environ
import google.auth
from google.cloud import secretmanager


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Define custom logging.
# It basically overwrites the default behavior that avoids request and security logs
# when outside debug mode.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}][{levelname}] {message}", "style": "{"}
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "propagate": False,
            "level": "DEBUG",
        },
        "django.security": {
            "handlers": ["console"],
            "propagate": False,
            "level": "DEBUG",
        },
    },
}


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# Load the environmental variables with default values
env = environ.Env(
    DEBUG=(bool, False),
    SERVICE_PUBLIC_URL=(str, None),
    USE_GCS_STATICS=(bool, False),
    GCS_BUCKET_STATICS=(str, None),
    SECRET_KEY=(str, None),
)

try:
    # Attempt to retrieve GCP credentials from environment
    _, os.environ["GOOGLE_CLOUD_PROJECT"] = google.auth.default()

except google.auth.exceptions.DefaultCredentialsError:
    pass

else:
    if GCP_PROJECT_ID := env("GOOGLE_CLOUD_PROJECT", default=None):
        # Pull environment variables from Secret Manager
        client = secretmanager.SecretManagerServiceClient()
        settings_name = env("SETTINGS_NAME")
        name = f"projects/{GCP_PROJECT_ID}/secrets/{settings_name}/versions/latest"
        payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")
        env.read_env(io.StringIO(payload))

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")

if SERVICE_PUBLIC_URL := env("SERVICE_PUBLIC_URL"):
    # If SERVICE_PUBLIC_URL is set it means we're serving publicly

    ALLOWED_HOSTS = [urlparse(SERVICE_PUBLIC_URL).netloc]
    CSRF_TRUSTED_ORIGINS = [SERVICE_PUBLIC_URL]
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

else:
    # If we're in a local environment, we only allow the localhost
    ALLOWED_HOSTS = ["127.0.0.1", "0.0.0.0", "localhost"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
    "rest_framework",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
    "decks.apps.DecksConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {"default": env.db()}
DATABASES["default"].update({"CONN_MAX_AGE": 10, "TEST": {"MIGRATE": False}})


if DEBUG:
    # When in debug mode, enable django-debug-toolbar
    # https://ranjanmp.medium.com/e79585813bc6
    import socket

    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
    INSTALLED_APPS += ["debug_toolbar"]

    ip = socket.gethostbyname(socket.gethostname())
    INTERNAL_IPS = [ip[:-1] + "1"] + ["127.0.0.1"]

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

ACCOUNT_EMAIL_VERIFICATION = "none"

LOGIN_REDIRECT_URL = "/"


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Paris"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

if env("USE_GCS_STATICS") and (statics_bucket := env("GCS_BUCKET_STATICS")):
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": statics_bucket,
                "default_acl": None,
                "querystring_auth": False,
                "gzip": True,
                "object_parameters": {"cache_control": "public, max-age=86400"},
            },
        },
    }
else:
    STATIC_ROOT = BASE_DIR / "static/"

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "statics"]


# Instead of sending emails, show them in the console.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
