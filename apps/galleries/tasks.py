import hashlib
import logging
import shutil
import tempfile
import zipfile
from datetime import timedelta
from pathlib import PurePosixPath

from celery import shared_task
from django.conf import settings
from django.core.files import File
from django.core.files.storage import storages
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation

from apps.photos.models import Photo, UploadSession, rendition_key

from .models import DownloadRequest

logger = logging.getLogger(__name__)
ZIP_DAYS = 7
SIGNER_SALT = "gallery-zip"


def zip_link(request_id: int) -> str:
    token = TimestampSigner(salt=SIGNER_SALT).sign(str(request_id))
    return reverse("public_gallery:zip_file", args=[token])


def fingerprint(photos, size: str) -> str:
    parts = [size] + [f"{p.pk}:{p.rendition_version}:{p.sha256}" for p in photos]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def photos_for_zip(gallery):
    return list(
        gallery.photos.filter(status=Photo.Status.READY)
        .select_related("section")
        .order_by("section__position", "position", "pk")
    )


def _safe(name: str) -> str:
    """One path segment for inside the ZIP: no separators, no '..', no leading dots."""
    cleaned = name.replace("/", "-").replace("\\", "-").strip().lstrip(".")
    return cleaned[:120] or "foto"


def _entries(photos, size):
    """(name inside the zip, storage, key) for each photo; chapters become folders.

    Names come from uploads and chapter titles, so each is reduced to a single safe segment:
    nothing in the archive can land outside the folder it is extracted to.
    """
    used = set()
    for photo in photos:
        base = _safe(PurePosixPath(photo.original_name.replace("\\", "/")).name)
        stem = PurePosixPath(base).stem or str(photo.uuid)
        if size == DownloadRequest.Size.ORIGINAL:
            storage, key = photo.original.storage, photo.original.name
            name = base
        else:
            width = photo.renditions.get("widths", [])[-1]
            storage = storages["renditions"]
            key = rendition_key(photo.uuid, photo.rendition_version, width, "jpg")
            name = f"{stem}.jpg"
        folder = _safe(photo.section.title) if photo.section else ""
        path = f"{folder}/{name}" if folder else name
        n = 2
        while path in used:
            path = f"{folder}/{stem}-{n}{PurePosixPath(name).suffix}".lstrip("/")
            n += 1
        used.add(path)
        yield path, storage, key


@shared_task(acks_late=True)
def build_zip(request_id: int):
    req = DownloadRequest.objects.select_related("gallery", "gallery__studio").get(pk=request_id)
    req.status = DownloadRequest.Status.BUILDING
    req.save(update_fields=["status", "updated_at"])
    gallery = req.gallery
    try:
        photos = photos_for_zip(gallery)
        with tempfile.TemporaryFile() as tmp:
            # JPEGs don't compress further; storing keeps it fast. ZIP64 for big originals.
            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
                for path, storage, key in _entries(photos, req.size):
                    with (
                        storage.open(key, "rb") as src,
                        zf.open(path, "w", force_zip64=True) as dst,
                    ):
                        shutil.copyfileobj(src, dst, 1024 * 1024)
            req.size_bytes = tmp.tell()
            tmp.seek(0)
            name = f"zips/{gallery.studio_id}/{gallery.pk}/{req.pk}-{req.size}.zip"
            req.file.save(name, File(tmp), save=False)
        req.fingerprint = fingerprint(photos, req.size)
        req.status = DownloadRequest.Status.READY
        req.expires_at = timezone.now() + timedelta(days=ZIP_DAYS)
        req.save()
    except Exception:
        logger.exception("ZIP %s failed", request_id)
        req.status = DownloadRequest.Status.FAILED
        req.save(update_fields=["status", "updated_at"])
        raise
    if req.email:
        send_zip_ready(req)


def send_zip_ready(req: DownloadRequest):
    base = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    context = {
        "gallery": req.gallery,
        "studio": req.gallery.studio,
        "link": base + zip_link(req.pk),
        "expires_at": req.expires_at,
        "size_mb": round(req.size_bytes / 1_000_000),
        "APP_NAME": settings.APP_NAME,
    }
    with translation.override(settings.LANGUAGE_CODE):
        subject = render_to_string("emails/zip_ready_subject.txt", context).strip()
        body = render_to_string("emails/zip_ready.txt", context)
    send_mail(subject, body, None, [req.email])


@shared_task
def clean_up():
    """Hourly: expired ZIPs and uploads abandoned for a day."""
    now = timezone.now()
    for req in DownloadRequest.objects.filter(expires_at__lt=now).exclude(file=""):
        req.file.delete(save=False)
        req.file = ""
        req.save(update_fields=["file", "updated_at"])
    from apps.photos.services import discard

    stale = UploadSession.objects.filter(
        status=UploadSession.Status.OPEN, updated_at__lt=now - timedelta(days=1)
    )
    for session in stale:
        discard(session)


@shared_task
def send_gallery_link(gallery_id: int):
    """The photographer shares a published gallery with its client by e-mail."""
    from .models import Gallery

    gallery = Gallery.objects.select_related("client", "studio").get(pk=gallery_id)
    if not (gallery.client and gallery.client.email and gallery.is_live):
        return
    base = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    context = {
        "gallery": gallery,
        "studio": gallery.studio,
        "client": gallery.client,
        "link": base + gallery.get_public_url(),
    }
    with translation.override(settings.LANGUAGE_CODE):
        subject = render_to_string("emails/gallery_link_subject.txt", context).strip()
        body = render_to_string("emails/gallery_link.txt", context)
    reply_to = [gallery.studio.email] if gallery.studio.email else None
    from django.core.mail import EmailMessage

    EmailMessage(subject, body, None, [gallery.client.email], reply_to=reply_to).send()
