from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import DateTimeLocalInput, StudioModelForm
from apps.core.templatetags.formatting import eur

from . import services
from .models import Location, Package, Shoot


class ShootForm(StudioModelForm):
    starts_at = forms.DateTimeField(
        label=_("Starts"),
        required=False,
        widget=DateTimeLocalInput(),
        help_text=_("Leave empty while the date is still open."),
    )
    ends_at = forms.DateTimeField(
        label=_("Ends"),
        required=False,
        widget=DateTimeLocalInput(),
        help_text=_("Defaults to the package duration."),
    )

    layout = [
        (None, ["client", "title"]),
        (_("When and where"), [("starts_at", "ends_at"), "location"]),
        (_("Package and price"), [("package", "price")]),
        (None, ["notes"]),
    ]

    class Meta:
        model = Shoot
        fields = ["client", "title", "location", "package", "price", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
        self.fields["title"].help_text = _("Leave empty to name it after the package and client.")
        self.fields["price"].required = False
        self.fields["package"].queryset = self.fields["package"].queryset.filter(is_active=True)
        self.fields["client"].queryset = self.fields["client"].queryset.order_by(
            "first_name", "last_name"
        )
        self.fields["client"].empty_label = _("Choose a client")
        self.fields["location"].empty_label = _("No location yet")
        self.fields["package"].empty_label = _("No package")
        self.fields["package"].label_from_instance = lambda p: f"{p.name} ({eur(p.price)})"
        if not self.instance.pk:
            self.initial["price"] = None
        if self.instance.pk:
            event = services.main_event(self.instance)
            if event:
                self.initial.setdefault("starts_at", event.start)
                self.initial.setdefault("ends_at", event.end)
            # Keep a retired package selectable on the shoots that already use it.
            if self.instance.package_id:
                self.fields["package"].queryset = Package.objects.filter(studio=self.studio).filter(
                    is_active=True
                ) | Package.objects.filter(pk=self.instance.package_id)

    def clean(self):
        data = super().clean()
        starts, ends = data.get("starts_at"), data.get("ends_at")
        if starts and ends and ends < starts:
            self.add_error("ends_at", _("The shoot can't end before it starts."))
        if ends and not starts:
            self.add_error("starts_at", _("Add the start as well."))
        package, client = data.get("package"), data.get("client")
        if data.get("price") is None:
            data["price"] = package.price if package else 0
        if not data.get("title") and client:
            data["title"] = f"{package.name}: {client.display_name}" if package else str(client)
        return data

    def save(self, commit=True):
        shoot = super().save(commit=commit)
        if commit:
            services.save_main_event(
                shoot, self.cleaned_data.get("starts_at"), self.cleaned_data.get("ends_at")
            )
        return shoot


class LocationForm(StudioModelForm):
    maps_url = forms.URLField(
        label=_("Map link"),
        required=False,
        assume_scheme="https",
        help_text=_("A Google Maps or Apple Maps link, so clients find you."),
    )

    class Meta:
        model = Location
        fields = ["name", "address", "maps_url", "notes"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PackageForm(StudioModelForm):
    layout = [
        (None, ["name", "description"]),
        (_("Price and scope"), [("price", "duration_minutes"), "photo_count"]),
        (_("Deadlines"), [("editing_days", "delivery_days")]),
        (None, ["is_active"]),
    ]

    class Meta:
        model = Package
        fields = [
            "name",
            "description",
            "price",
            "duration_minutes",
            "photo_count",
            "editing_days",
            "delivery_days",
            "is_active",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
