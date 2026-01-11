"""Base settings for DiveOps project."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = BASE_DIR / "src"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# Debug mode - override in dev.py
DEBUG = False

ALLOWED_HOSTS = []

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

# Django Primitives (from submodule)
PRIMITIVES_APPS = [
    # Foundation
    "django_basemodels",
    "django_singleton",
    "django_sequence",
    # Identity
    "django_parties",
    # Infrastructure
    "django_audit_log",
    "django_communication",
    # Domain
    "django_catalog",
    "django_encounters",
    "django_ledger",
    # Content
    "django_documents",
    "django_agreements",
    "django_questionnaires",
    "django_cms_core",
    # Value Objects
    "django_money",
    # UI
    "django_portal_ui",
]

# Local apps
LOCAL_APPS = [
    "diveops.core",
    "diveops.pricing",
    "diveops.invoicing",
    "diveops.store",
    "diveops.operations",
]

INSTALLED_APPS = DJANGO_APPS + PRIMITIVES_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "diveops.core.middleware.ImpersonationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "diveops.urls"

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
                "django_portal_ui.context_processors.portal_ui",
                "diveops.operations.context_processors.diveops_context",
                "diveops.core.context_processors.impersonation_context",
                "diveops.store.context_processors.cart_context",
            ],
        },
    },
]

WSGI_APPLICATION = "diveops.wsgi.application"
ASGI_APPLICATION = "diveops.asgi.application"

# Database - PostgreSQL only
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "diveops"),
        "USER": os.environ.get("POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    }
}

# Custom user model
AUTH_USER_MODEL = "core.User"

# Django Modules configuration
MODULES_ORG_MODEL = "django_parties.Organization"
CATALOG_ENCOUNTER_MODEL = "django_encounters.Encounter"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Login redirects
LOGIN_REDIRECT_URL = "/portal/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Dive Operations configuration
DIVE_SHOP_NAME = os.environ.get("DIVE_SHOP_NAME", "DiveOps")
DIVE_SHOP_TIMEZONE = os.environ.get("DIVE_SHOP_TIMEZONE", "America/New_York")
DIVE_SHOP_LATITUDE = float(os.environ.get("DIVE_SHOP_LATITUDE", "25.7617"))
DIVE_SHOP_LONGITUDE = float(os.environ.get("DIVE_SHOP_LONGITUDE", "-80.1918"))

# Portal UI configuration
PORTAL_UI = {
    "SITE_NAME": DIVE_SHOP_NAME,
    "STAFF_PORTAL_TITLE": f"{DIVE_SHOP_NAME} Staff",
    "CUSTOMER_PORTAL_TITLE": f"{DIVE_SHOP_NAME} Portal",
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "diveops": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
