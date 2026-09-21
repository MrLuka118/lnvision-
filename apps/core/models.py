import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def new_token() -> str:
    """URL-safe secret with 256 bits of entropy (43 characters)."""
    return secrets.token_urlsafe(32)


class Studio(models.Model):
    """The tenant. Every business record belongs to exactly one studio."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="studio"
    )
    name = models.CharField(_("studio name"), max_length=120)
    slug = models.SlugField(
        _("portfolio address"),
        max_length=60,
        unique=True,
        help_text=_("Your public portfolio lives at /p/<address>/."),
    )
    email = models.EmailField(_("contact email"), blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    address = models.TextField(_("address"), blank=True)
    vat_id = models.CharField(_("tax number"), max_length=32, blank=True)
    iban = models.CharField(_("IBAN"), max_length=34, blank=True)
    vat_registered = models.BooleanField(_("VAT registered"), default=False)
    default_vat_rate = models.DecimalField(
        _("default VAT rate (%)"), max_digits=4, decimal_places=1, default=Decimal("22.0")
    )
    ics_token = models.CharField(max_length=64, unique=True, default=new_token, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("studio")
        verbose_name_plural = _("studios")

    def __str__(self):
        return self.name


class TenantQuerySet(models.QuerySet):
    def for_studio(self, studio):
        return self.filter(studio=studio)


class TenantModel(models.Model):
    """Base for every studio-owned model. Query through `.for_studio()`, never `.all()`."""

    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name="+", editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True
