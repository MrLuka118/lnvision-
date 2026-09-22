"""Settings shared by every environment. Values that differ per deploy come from the env."""

from pathlib import Path

import environ
from celery.schedules import crontab
from csp.constants import NONCE, NONE, SELF, UNSAFE_INLINE
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

# The product name lives here and only here; templates get it via a context processor.
APP_NAME = env("APP_NAME", default="Aperture Studio")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Uploads, originals and renditions. /data in Docker, ./var when run on the host.
DATA_DIR = Path(env("DATA_DIR", default=str(BASE_DIR / "var")))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django_cotton.apps.SimpleAppConfig",
    "django_htmx",
    "django_tailwind_cli",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "apps.core",
    "apps.accounts",
    "apps.clients",
    "apps.shoots",
    "apps.scheduling",
    "apps.photos",
    "apps.galleries",
    "apps.portfolio",
    "apps.finance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.core.middleware.StudioMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "csp.context_processors.nonce",
                "apps.core.context_processors.app",
            ],
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django_cotton.cotton_loader.Loader",
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                )
            ],
            "builtins": [
                "django_cotton.templatetags.cotton",
                "django.templatetags.i18n",
                "django.templatetags.static",
            ],
        },
    }
]

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "core:dashboard"

# --- allauth -------------------------------------------------------------------------------
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.SocialAccountAdapter"
ACCOUNT_FORMS = {"signup": "apps.accounts.forms.SignupForm"}
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = f"{APP_NAME}: "
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"
ACCOUNT_ALLOW_SIGNUPS = env.bool("ACCOUNT_ALLOW_SIGNUPS", default=True)
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_PROVIDERS = {}
if env("GOOGLE_CLIENT_ID", default=""):
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [
            {
                "client_id": env("GOOGLE_CLIENT_ID"),
                "secret": env("GOOGLE_CLIENT_SECRET"),
                "key": "",
            }
        ],
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }

# --- i18n ----------------------------------------------------------------------------------
# Message ids are English; Slovenian lives in locale/sl. English joins LANGUAGES once translated.
LANGUAGE_CODE = "sl"
LANGUAGES = [("sl", _("Slovenian"))]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = "Europe/Ljubljana"
USE_TZ = True
FORMAT_MODULE_PATH = ["config.formats"]
# Off on purpose: with it on, every {{ number }} in markup (ids, data attributes) gets grouped.
# Money goes through the |eur filter, which groups explicitly.
USE_THOUSAND_SEPARATOR = False
CURRENCY = "EUR"

# --- Static, media, storage ------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"

# "default" is private (originals, ZIPs, receipts). "renditions" is public web-size images
# under unguessable keys. Production swaps both for S3-compatible buckets (see prod.py).
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": DATA_DIR / "private", "base_url": None},
    },
    "renditions": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": MEDIA_ROOT, "base_url": MEDIA_URL},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

TAILWIND_CLI_VERSION = "4.3.3"
TAILWIND_CLI_PATH = env("TAILWIND_CLI_PATH", default=".django_tailwind_cli")
TAILWIND_CLI_SRC_CSS = "assets/css/app.css"
TAILWIND_CLI_DIST_CSS = "css/app.css"
TAILWIND_CLI_AUTOMATIC_DOWNLOAD = True

# --- E-mail --------------------------------------------------------------------------------
vars().update(env.email("EMAIL_URL", default="consolemail://"))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"{APP_NAME} <studio@localhost>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Celery --------------------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "apps.photos.tasks.*": {"queue": "images"},
    "apps.galleries.tasks.build_zip": {"queue": "zips"},
}
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "galleries-clean-up": {"task": "apps.galleries.tasks.clean_up", "schedule": 60 * 60},
    "finance-recurring": {
        "task": "apps.finance.tasks.generate_recurring_expenses",
        "schedule": crontab(hour=5, minute=30),
    },
}
# Absolute links in e-mails (ZIP ready, invitations).
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# --- Security ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # HTMX reads the token from the <body hx-headers> attribute instead.
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
RATELIMIT_USE_CACHE = "default"

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE],
        "style-src": [SELF, NONCE],
        # Inline style attributes carry per-photo data (aspect ratio, placeholder colour).
        "style-src-attr": [UNSAFE_INLINE],
        "img-src": [SELF, "data:", "blob:"],
        "font-src": [SELF],
        "connect-src": [SELF],
        "frame-ancestors": [NONE],
        "form-action": [SELF, "https://accounts.google.com"],
        "base-uri": [SELF],
        "object-src": [NONE],
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"pyvips": {"level": "WARNING"}},
}
