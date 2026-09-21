import tempfile
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

DATA_DIR = Path(tempfile.mkdtemp(prefix="aperture-test-"))
MEDIA_ROOT = DATA_DIR / "media"
STORAGES = {
    **STORAGES,  # noqa: F405
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": DATA_DIR / "private", "base_url": None},
    },
    "renditions": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": MEDIA_ROOT, "base_url": "/media/"},
    },
}
