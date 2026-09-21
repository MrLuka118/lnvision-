import uuid
from pathlib import PurePosixPath

from django.core.files.storage import storages
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel

# Widths generated for every photo (never upscaled) and the formats per width.
RENDITION_WIDTHS = [480, 960, 1600, 2400]
RENDITION_FORMATS = ["avif", "jpg"]


def original_path(photo, filename):
    suffix = PurePosixPath(filename).suffix.lower()[:6]
    return f"originals/{photo.studio_id}/{photo.gallery_id}/{photo.uuid}{suffix}"


def rendition_key(photo_uuid, version: int, width: int, fmt: str) -> str:
    """Public, unguessable key: the photo's UUID is the only secret, like the gallery link."""
    return f"r/{photo_uuid}/{version}/{width}.{fmt}"


class Photo(TenantModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting")
        PROCESSING = "processing", _("Processing")
        READY = "ready", _("Ready")
        FAILED = "failed", _("Failed")

    gallery = models.ForeignKey(
        "galleries.Gallery", on_delete=models.CASCADE, related_name="photos"
    )
    section = models.ForeignKey(
        "galleries.GallerySection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
    )
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    original = models.FileField(upload_to=original_path, max_length=255)
    original_name = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    exif = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)
    renditions = models.JSONField(default=dict, blank=True)
    rendition_version = models.PositiveIntegerField(default=0)
    lqip = models.TextField(blank=True)
    dominant_color = models.CharField(max_length=7, blank=True)
    luminance = models.FloatField(null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("photo")
        verbose_name_plural = _("photos")
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["gallery", "position"])]

    def __str__(self):
        return self.original_name

    @property
    def is_ready(self) -> bool:
        return self.status == self.Status.READY

    @property
    def aspect_ratio(self) -> float:
        if self.width and self.height:
            return self.width / self.height
        return 1.5

    @property
    def is_bright(self) -> bool:
        """Bright enough that controls on clear glass above it need the dimming layer."""
        return self.luminance is not None and self.luminance >= 0.45

    def rendition_url(self, width: int, fmt: str = "jpg") -> str:
        key = rendition_key(self.uuid, self.rendition_version, width, fmt)
        return storages["renditions"].url(key)

    def srcset(self, fmt: str = "jpg") -> str:
        widths = self.renditions.get("widths", [])
        return ", ".join(f"{self.rendition_url(w, fmt)} {w}w" for w in widths)

    @property
    def srcset_avif(self) -> str:
        return self.srcset("avif") if "avif" in self.renditions.get("formats", []) else ""

    @property
    def srcset_jpg(self) -> str:
        return self.srcset("jpg")

    @property
    def src(self) -> str:
        width = self.best_width(960)
        return self.rendition_url(width, "jpg") if width else ""

    @property
    def display_width(self) -> int:
        widths = self.renditions.get("widths", [])
        return widths[-1] if widths else (self.width or 0)

    @property
    def display_height(self) -> int:
        return round(self.display_width / self.aspect_ratio) if self.display_width else 0

    @property
    def display_src(self) -> str:
        return self.rendition_url(self.display_width, "jpg") if self.display_width else ""

    def best_width(self, target: int) -> int | None:
        widths = self.renditions.get("widths", [])
        if not widths:
            return None
        return next((w for w in widths if w >= target), widths[-1])


class UploadSession(TenantModel):
    """One file arriving in chunks. The partial file lives on local disk until complete."""

    class Status(models.TextChoices):
        OPEN = "open", _("Uploading")
        COMPLETE = "complete", _("Complete")
        FAILED = "failed", _("Failed")

    gallery = models.ForeignKey(
        "galleries.Gallery", on_delete=models.CASCADE, related_name="uploads"
    )
    section = models.ForeignKey(
        "galleries.GallerySection", on_delete=models.SET_NULL, null=True, blank=True
    )
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    filename = models.CharField(max_length=255)
    size_bytes = models.BigIntegerField()
    received_bytes = models.BigIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    photo = models.OneToOneField(Photo, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"])]
