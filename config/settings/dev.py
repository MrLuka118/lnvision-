from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
INTERNAL_IPS = ["127.0.0.1"]

if env.bool("VITE_DEV_MODE", default=False):
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["script-src"] = [SELF, NONCE, "http://localhost:5173"]
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["connect-src"] += [
        "http://localhost:5173",
        "ws://localhost:5173",
    ]
    CONTENT_SECURITY_POLICY["DIRECTIVES"]["style-src"] = [SELF, UNSAFE_INLINE]
