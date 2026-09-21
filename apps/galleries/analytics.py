import hashlib
import hmac

from django.conf import settings
from django.utils import timezone

from .models import GalleryEvent

DEVICES = [("iphone", "iPhone"), ("ipad", "iPad"), ("android", "Android"), ("mac os", "Mac"),
           ("windows", "Windows"), ("linux", "Linux")]  # fmt: skip


def ip_hash(request) -> str:
    """Tells repeat visits apart for a day without storing the address (salt rotates daily)."""
    ip = request.META.get("REMOTE_ADDR", "")
    salt = hmac.new(
        settings.SECRET_KEY.encode(), timezone.localdate().isoformat().encode(), hashlib.sha256
    ).digest()
    return hashlib.sha256(salt + ip.encode()).hexdigest()[:16]


def device(request) -> str:
    agent = request.headers.get("User-Agent", "").lower()
    return next((label for needle, label in DEVICES if needle in agent), "")


def record(request, gallery, kind, visitor=None, photo=None, owner=False):
    if owner:
        return None  # the photographer previewing isn't a client
    return GalleryEvent.objects.create(
        studio_id=gallery.studio_id,
        gallery=gallery,
        visitor=visitor,
        photo=photo,
        kind=kind,
        ip_hash=ip_hash(request),
        device=device(request),
    )
