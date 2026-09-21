from .base import *  # noqa: F403
from .base import env

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}

if env("STORAGE_BACKEND", default="filesystem") == "s3":
    _s3 = {
        "endpoint_url": env("S3_ENDPOINT_URL"),
        "access_key": env("S3_ACCESS_KEY_ID"),
        "secret_key": env("S3_SECRET_ACCESS_KEY"),
        "region_name": env("S3_REGION", default="auto"),
        "signature_version": "s3v4",
        "file_overwrite": False,
    }
    STORAGES["default"] = {  # noqa: F405
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3,
            "bucket_name": env("S3_PRIVATE_BUCKET"),
            "default_acl": "private",
            "querystring_auth": True,
            "querystring_expire": 600,
        },
    }
    STORAGES["renditions"] = {  # noqa: F405
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3,
            "bucket_name": env("S3_PUBLIC_BUCKET"),
            "custom_domain": env("S3_PUBLIC_DOMAIN"),
            "querystring_auth": False,
            "object_parameters": {"CacheControl": "public, max-age=31536000, immutable"},
        },
    }
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["img-src"].append(  # noqa: F405
        f"https://{env('S3_PUBLIC_DOMAIN')}"
    )
