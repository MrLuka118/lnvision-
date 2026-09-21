from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from apps.core.models import TenantModel


class Event(TenantModel):
    """Everything on the calendar: shoots, meetings, deadlines and personal time."""

    class Kind(models.TextChoices):
        SHOOT = "shoot", _("Shoot")
        MEETING = "meeting", _("Client meeting")
        EDITING_DEADLINE = "editing_deadline", _("Editing deadline")
        DELIVERY_DEADLINE = "delivery_deadline", _("Delivery deadline")
        PERSONAL = "personal", _("Personal")

    # ColorChecker Classic patches (sRGB hex, also in tokens.css). Used for the calendar,
    # where FullCalendar needs literal colours.
    KIND_COLOURS = {
        Kind.SHOOT: "#e0a32e",
        Kind.MEETING: "#627a9d",
        Kind.EDITING_DEADLINE: "#8580b1",
        Kind.DELIVERY_DEADLINE: "#c15a63",
        Kind.PERSONAL: "#576c43",
    }

    kind = models.CharField(_("type"), max_length=24, choices=Kind.choices, default=Kind.SHOOT)
    title = models.CharField(_("title"), max_length=160, blank=True)
    start = models.DateTimeField(_("starts"))
    end = models.DateTimeField(_("ends"), null=True, blank=True)
    all_day = models.BooleanField(_("all day"), default=False)
    is_tentative = models.BooleanField(
        _("tentative"), default=False, help_text=_("Not confirmed yet, e.g. an inquiry.")
    )
    shoot = models.ForeignKey(
        "shoots.Shoot",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("shoot"),
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("client"),
    )
    location = models.ForeignKey(
        "shoots.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("location"),
    )
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("event")
        verbose_name_plural = _("events")
        ordering = ["start"]
        indexes = [models.Index(fields=["studio", "start"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(end__isnull=True) | Q(end__gte=F("start")),
                name="event_ends_after_start",
            )
        ]

    def __str__(self):
        return self.display_title

    # Deadlines are named after their shoot, with this in front, so they read apart from it.
    DEADLINE_PREFIX = {
        Kind.EDITING_DEADLINE: pgettext_lazy("deadline", "Editing"),
        Kind.DELIVERY_DEADLINE: pgettext_lazy("deadline", "Delivery"),
    }

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        if self.shoot_id:
            prefix = self.DEADLINE_PREFIX.get(self.kind)
            return f"{prefix}: {self.shoot.title}" if prefix else self.shoot.title
        if self.client_id:
            return self.client.display_name
        return self.get_kind_display()

    @property
    def colour(self) -> str:
        return self.KIND_COLOURS.get(self.kind, "#8f8f8f")
