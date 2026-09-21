from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel, new_token


class Gallery(TenantModel):
    """A delivery: the page a client opens from a secret link."""

    class Theme(models.TextChoices):
        DARKROOM = "darkroom", _("Darkroom")
        LIGHT_TABLE = "light-table", _("Light table")
        PHOTOBOOK = "photobook", _("Photo book")
        CONTACT_SHEET = "contact-sheet", _("Contact sheet")

    class Downloads(models.TextChoices):
        NONE = "none", _("No downloads")
        WEB = "web", _("Web size")
        ORIGINAL = "original", _("Originals")
        BOTH = "both", _("Web size and originals")

    shoot = models.ForeignKey(
        "shoots.Shoot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="galleries",
        verbose_name=_("shoot"),
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="galleries",
        verbose_name=_("client"),
    )
    title = models.CharField(_("title"), max_length=160)
    intro = models.TextField(_("introduction"), blank=True)
    event_date = models.DateField(_("date"), null=True, blank=True)

    token = models.CharField(max_length=64, unique=True, default=new_token, editable=False)
    password_hash = models.CharField(max_length=128, blank=True, editable=False)
    password_version = models.PositiveIntegerField(default=0, editable=False)
    expires_at = models.DateTimeField(_("available until"), null=True, blank=True)
    is_published = models.BooleanField(_("published"), default=False)
    published_at = models.DateTimeField(null=True, blank=True, editable=False)

    theme = models.CharField(
        _("theme"), max_length=20, choices=Theme.choices, default=Theme.DARKROOM
    )
    cover_photo = models.ForeignKey(
        "photos.Photo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("cover photo"),
    )
    downloads = models.CharField(
        _("downloads"), max_length=10, choices=Downloads.choices, default=Downloads.WEB
    )
    allow_favorites = models.BooleanField(_("clients can mark favourites"), default=True)
    allow_comments = models.BooleanField(_("clients can comment"), default=True)
    watermark = models.BooleanField(_("watermark web-size photos"), default=False)
    strip_gps = models.BooleanField(_("remove GPS location from photos"), default=True)

    class Meta:
        verbose_name = _("gallery")
        verbose_name_plural = _("galleries")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("galleries:editor", args=[self.pk])

    def get_public_url(self):
        return reverse("public_gallery:gallery", args=[self.token])

    # --- access ---------------------------------------------------------------------------
    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, raw: str | None):
        """Set, change or clear (empty) the password. Every change signs visitors out."""
        self.password_hash = make_password(raw) if raw else ""
        self.password_version += 1

    def check_password(self, raw: str) -> bool:
        return bool(self.password_hash) and check_password(raw, self.password_hash)

    def rotate_token(self):
        """New secret link; the old one stops working."""
        self.token = new_token()

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_live(self) -> bool:
        return self.is_published and not self.is_expired

    @property
    def allows_web_downloads(self) -> bool:
        return self.downloads in (self.Downloads.WEB, self.Downloads.BOTH)

    @property
    def allows_original_downloads(self) -> bool:
        return self.downloads in (self.Downloads.ORIGINAL, self.Downloads.BOTH)


class GallerySection(TenantModel):
    """A chapter of a gallery, e.g. "Priprave", "Obred", "Zabava"."""

    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(_("title"), max_length=120)
    description = models.TextField(_("description"), blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("section")
        verbose_name_plural = _("sections")
        ordering = ["position", "id"]

    def __str__(self):
        return self.title
