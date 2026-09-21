from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel


class Client(TenantModel):
    class Source(models.TextChoices):
        PORTFOLIO = "portfolio", _("Portfolio inquiry")
        REFERRAL = "referral", _("Referral")
        INSTAGRAM = "instagram", _("Instagram")
        OTHER = "other", _("Other")

    first_name = models.CharField(_("first name"), max_length=80)
    last_name = models.CharField(_("last name"), max_length=80, blank=True)
    partner_name = models.CharField(
        _("partner"),
        max_length=120,
        blank=True,
        help_text=_("For couples: the second person, shown next to the client's name."),
    )
    company = models.CharField(_("company"), max_length=120, blank=True)
    email = models.EmailField(_("email"), blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    address = models.TextField(_("address"), blank=True)
    vat_id = models.CharField(_("tax number"), max_length=32, blank=True)
    source = models.CharField(
        _("came from"), max_length=20, choices=Source.choices, default=Source.OTHER
    )
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("client")
        verbose_name_plural = _("clients")
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["studio", "email"]),
            models.Index(fields=["studio", "first_name", "last_name"]),
        ]

    def __str__(self):
        return self.display_name

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self) -> str:
        if self.partner_name:
            return _("%(client)s and %(partner)s") % {
                "client": self.full_name,
                "partner": self.partner_name,
            }
        return self.full_name

    @property
    def initials(self) -> str:
        return (self.first_name[:1] + self.last_name[:1]).upper()

    def get_absolute_url(self):
        return reverse("clients:detail", args=[self.pk])
