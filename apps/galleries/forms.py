from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import DateInput, DateTimeLocalInput, StudioModelForm

from .models import Gallery, GallerySection


class GalleryCreateForm(StudioModelForm):
    class Meta:
        model = Gallery
        fields = ["title", "shoot", "client", "event_date", "theme"]
        widgets = {"event_date": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shoot"].empty_label = _("Not linked to a shoot")
        self.fields["client"].empty_label = _("Taken from the shoot")
        self.fields["client"].help_text = _("Leave empty to use the shoot's client.")

    def clean(self):
        data = super().clean()
        shoot = data.get("shoot")
        if shoot and not data.get("client"):
            data["client"] = shoot.client
        return data


class GallerySettingsForm(StudioModelForm):
    password = forms.CharField(
        label=_("New password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Clients enter it once per device. Leave empty to keep the current one."),
    )
    remove_password = forms.BooleanField(label=_("Open without a password"), required=False)

    layout = [
        (None, ["title", "intro", "event_date"]),
        (_("Look"), ["theme"]),
        (_("Access"), [("password", "expires_at"), "remove_password"]),
        (
            _("What clients can do"),
            ["downloads", "allow_favorites", "allow_comments"],
        ),
        (_("Photos"), ["watermark", "strip_gps"]),
    ]

    class Meta:
        model = Gallery
        fields = [
            "title",
            "intro",
            "event_date",
            "theme",
            "expires_at",
            "downloads",
            "allow_favorites",
            "allow_comments",
            "watermark",
            "strip_gps",
        ]
        widgets = {
            "intro": forms.Textarea(attrs={"rows": 3}),
            "event_date": DateInput(),
            "expires_at": DateTimeLocalInput(),
        }
        help_texts = {
            "intro": _("A few words shown under the title on the cover."),
            "expires_at": _("After this the link shows a friendly note instead of the photos."),
            "watermark": _("Applies to photos processed from now on. Originals never change."),
        }

    def save(self, commit=True):
        gallery = super().save(commit=False)
        if self.cleaned_data.get("remove_password"):
            gallery.set_password(None)
        elif self.cleaned_data.get("password"):
            gallery.set_password(self.cleaned_data["password"])
        if commit:
            gallery.save()
        return gallery


class SectionForm(StudioModelForm):
    class Meta:
        model = GallerySection
        fields = ["title"]
