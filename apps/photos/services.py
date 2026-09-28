"""Upload sessions and the processing of photos into renditions."""

import hashlib
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.db import transaction
from django.db.models import Max

from . import exif, imaging
from .models import Photo, UploadSession, rendition_key

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".avif"}
CHUNK_SIZE = 8 * 1024 * 1024


def max_upload_bytes() -> int:
    return getattr(settings, "PHOTO_MAX_UPLOAD_BYTES", 150 * 1024 * 1024)


def upload_dir() -> Path:
    path = Path(settings.DATA_DIR) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def partial_path(session: UploadSession) -> Path:
    return upload_dir() / f"{session.uuid}.part"


def next_position(gallery) -> int:
    top = gallery.photos.aggregate(top=Max("position"))["top"]
    return 0 if top is None else top + 1


def discard(session: UploadSession, status=UploadSession.Status.FAILED):
    partial_path(session).unlink(missing_ok=True)
    session.status = status
    session.save(update_fields=["status", "updated_at"])


def finalize(session: UploadSession) -> Photo:
    """The last chunk arrived: validate, store the original privately, queue processing."""
    path = partial_path(session)
    try:
        imaging.inspect(path)
    except imaging.UnreadableImage:
        discard(session)
        raise
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    with transaction.atomic():
        photo = Photo(
            studio=session.studio,
            gallery=session.gallery,
            section=session.section,
            original_name=Path(session.filename).name[:255],
            size_bytes=session.size_bytes,
            sha256=digest.hexdigest(),
            position=next_position(session.gallery),
        )
        with path.open("rb") as fh:
            photo.original.save(session.filename, File(fh), save=False)
        photo.save()
        session.photo = photo
        session.status = UploadSession.Status.COMPLETE
        session.save(update_fields=["photo", "status", "updated_at"])
        transaction.on_commit(lambda: _queue(photo.pk))
    path.unlink(missing_ok=True)
    return photo


def _queue(photo_id: int):
    from .tasks import process_photo

    process_photo.delay(photo_id)


def delete_renditions(photo: Photo, version: int | None = None):
    storage = storages["renditions"]
    version = photo.rendition_version if version is None else version
    for width in photo.renditions.get("widths", []):
        for fmt in photo.renditions.get("formats", []):
            storage.delete(rendition_key(photo.uuid, version, width, fmt))


def process(photo: Photo) -> Photo:
    """Make the web renditions. Idempotent: re-running writes a new version and drops the old."""
    photo.status = Photo.Status.PROCESSING
    photo.save(update_fields=["status", "updated_at"])
    gallery = photo.gallery
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / f"original{Path(photo.original.name).suffix}"
        with photo.original.open("rb") as src, local.open("wb") as dst:
            shutil.copyfileobj(src, dst)

        details, taken_at = exif.read(local)
        if gallery.strip_gps and exif.has_gps(local):
            exif.strip_gps(local)
            name = photo.original.name
            photo.original.storage.delete(name)
            with local.open("rb") as fh:
                saved = photo.original.storage.save(name, File(fh))
            photo.original.name = saved

        watermark_text = f"© {photo.studio.name}" if gallery.watermark else ""
        rendered = imaging.render(local, watermark_text=watermark_text)

    old = (photo.rendition_version, dict(photo.renditions)) if photo.renditions else None
    version = photo.rendition_version + 1
    storage = storages["renditions"]
    for (width, fmt), data in rendered.files.items():
        storage.save(rendition_key(photo.uuid, version, width, fmt), ContentFile(data))

    photo.width, photo.height = rendered.width, rendered.height
    photo.exif = details
    photo.taken_at = taken_at
    photo.renditions = {
        "widths": rendered.widths,
        "formats": sorted({f for _w, f in rendered.files}),
    }
    photo.rendition_version = version
    photo.lqip = rendered.lqip
    photo.blurhash = rendered.blurhash
    photo.dominant_color = rendered.dominant_color
    photo.luminance = rendered.luminance
    photo.status = Photo.Status.READY
    photo.error = ""
    photo.save()
    if old:
        stale = Photo(uuid=photo.uuid, renditions=old[1], rendition_version=old[0])
        delete_renditions(stale)
    return photo
