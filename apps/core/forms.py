from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Studio, TenantModel


class FormLayoutMixin:
    """Mixin that provides a sections() method for templates.

    Optional ``layout`` groups fields for the generic form template::

        layout = [
            (None, [("first_name", "last_name"), "email"]),
            (_("Billing"), ["company", "vat_id"]),
        ]

    A tuple puts fields side by side on wide screens.
    """

    layout = None

    def sections(self):
        """[{"legend": str | None, "rows": [[BoundField, ...], ...]}] for templates."""
        visible = {bf.name: bf for bf in self.visible_fields()}
        if not self.layout:
            return [{"legend": None, "rows": [[bf] for bf in visible.values()]}]
        sections, used = [], set()
        for legend, rows in self.layout:
            out = []
            for row in rows:
                names = row if isinstance(row, tuple) else (row,)
                fields = [visible[n] for n in names if n in visible]
                used.update(names)
                if fields:
                    out.append(fields)
            sections.append({"legend": legend, "rows": out})
        leftovers = [[bf] for name, bf in visible.items() if name not in used]
        if leftovers:
            sections.append({"legend": None, "rows": leftovers})
        return sections


class StudioModelForm(FormLayoutMixin, forms.ModelForm):
    """ModelForm that limits every related-object choice to the current studio.

    Without this, a form for a shoot would offer (and accept) another studio's clients.
    """

    def __init__(self, *args, studio, **kwargs):
        super().__init__(*args, **kwargs)
        self.studio = studio
        for field in self.fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is not None and issubclass(queryset.model, TenantModel):
                field.queryset = queryset.filter(studio=studio)


class StudioForm(FormLayoutMixin, forms.ModelForm):
    """Form for editing the Studio (tenant) record itself."""

    layout = [
        (None, ["name", "slug"]),
        (_("Contact"), [("email", "phone"), "address"]),
        (_("Branding"), ["accent_colour", "logo"]),
        (_("Invoicing"), [("vat_id", "iban"), ("vat_registered", "default_vat_rate")]),
    ]

    class Meta:
        model = Studio
        fields = [
            "name",
            "slug",
            "accent_colour",
            "logo",
            "email",
            "phone",
            "address",
            "vat_id",
            "iban",
            "vat_registered",
            "default_vat_rate",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "accent_colour": forms.TextInput(attrs={"type": "color"}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and hasattr(logo, "content_type"):
            if logo.size > 2 * 1024 * 1024:
                raise forms.ValidationError(_("Use a logo smaller than 2 MB."))
            from io import BytesIO

            from django.core.files.base import ContentFile
            from PIL import Image

            image = Image.open(logo)
            image.thumbnail((1000, 1000))
            output = BytesIO()
            image.convert("RGBA").save(output, format="PNG")
            return ContentFile(output.getvalue(), name="logo.png")
        return logo

    def clean_slug(self):
        return self.cleaned_data["slug"].lower()


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs, format="%Y-%m-%dT%H:%M")


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs, format="%Y-%m-%d")


class ProfileForm(FormLayoutMixin, forms.ModelForm):
    class Meta:
        from apps.accounts.models import User

        model = User
        fields = ["first_name", "last_name"]
