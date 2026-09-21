from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import OuterRef, Subquery
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel, TenantQuerySet


class Location(TenantModel):
    name = models.CharField(_("name"), max_length=120)
    address = models.TextField(_("address"), blank=True)
    maps_url = models.URLField(_("map link"), blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("location")
        verbose_name_plural = _("locations")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Package(TenantModel):
    name = models.CharField(_("name"), max_length=120)
    description = models.TextField(_("description"), blank=True)
    price = models.DecimalField(_("price"), max_digits=10, decimal_places=2)
    duration_minutes = models.PositiveIntegerField(_("duration (minutes)"), default=120)
    photo_count = models.PositiveIntegerField(_("photos included"), null=True, blank=True)
    editing_days = models.PositiveSmallIntegerField(
        _("editing deadline (days after the shoot)"), default=14
    )
    delivery_days = models.PositiveSmallIntegerField(
        _("delivery deadline (days after the shoot)"), default=21
    )
    is_active = models.BooleanField(_("offered"), default=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("package")
        verbose_name_plural = _("packages")
        ordering = ["position", "name"]

    def __str__(self):
        return self.name

    @property
    def duration(self) -> timedelta:
        return timedelta(minutes=self.duration_minutes)


class ShootQuerySet(TenantQuerySet):
    def with_dates(self):
        """Annotate `starts_at` / `ends_at` from the shoot's main calendar event (no N+1)."""
        from apps.scheduling.models import Event

        main = Event.objects.filter(shoot=OuterRef("pk"), kind=Event.Kind.SHOOT).order_by("start")
        return self.annotate(
            starts_at=Subquery(main.values("start")[:1]),
            ends_at=Subquery(main.values("end")[:1]),
        )


class Shoot(TenantModel):
    class Status(models.TextChoices):
        INQUIRY = "inquiry", _("Inquiry")
        CONFIRMED = "confirmed", _("Confirmed")
        SHOT = "shot", _("Shot")
        EDITING = "editing", _("Editing")
        DELIVERED = "delivered", _("Delivered")
        PAID = "paid", _("Paid")
        CANCELLED = "cancelled", _("Cancelled")

    # The happy path, in order. Cancelled sits outside it.
    PIPELINE = [
        Status.INQUIRY,
        Status.CONFIRMED,
        Status.SHOT,
        Status.EDITING,
        Status.DELIVERED,
        Status.PAID,
    ]
    # ColorChecker patch per status (see tokens.css).
    STATUS_COLOURS = {
        Status.INQUIRY: "var(--color-cc-light-skin)",
        Status.CONFIRMED: "var(--color-cc-blue-sky)",
        Status.SHOT: "var(--color-cc-orange-yellow)",
        Status.EDITING: "var(--color-cc-blue-flower)",
        Status.DELIVERED: "var(--color-cc-bluish-green)",
        Status.PAID: "var(--color-cc-yellow-green)",
        Status.CANCELLED: "var(--ink-3)",
    }

    # RESTRICT, not PROTECT: a client with shoots can't be deleted on their own, but deleting
    # the whole studio (account deletion) still removes everything.
    client = models.ForeignKey(
        "clients.Client", on_delete=models.RESTRICT, related_name="shoots", verbose_name=_("client")
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shoots",
        verbose_name=_("package"),
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shoots",
        verbose_name=_("location"),
    )
    title = models.CharField(_("title"), max_length=160)
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.INQUIRY
    )
    status_changed_at = models.DateTimeField(null=True, blank=True, editable=False)
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Taken from the package when left empty."),
    )
    notes = models.TextField(_("notes"), blank=True)
    inquiry_message = models.TextField(_("inquiry message"), blank=True, editable=False)

    objects = ShootQuerySet.as_manager()

    class Meta:
        verbose_name = _("shoot")
        verbose_name_plural = _("shoots")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["studio", "status"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("shoots:detail", args=[self.pk])

    @property
    def status_colour(self) -> str:
        return self.STATUS_COLOURS.get(self.status, "var(--ink-3)")

    @property
    def pipeline_index(self) -> int:
        try:
            return self.PIPELINE.index(self.status)
        except ValueError:
            return -1
