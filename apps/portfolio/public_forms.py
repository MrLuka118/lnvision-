import time

from django import forms
from django.core import signing
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.forms import DateInput
from apps.shoots.models import Package

SALT = "portfolio-inquiry"
MIN_SECONDS = 3  # people take longer than this to write a message; scripts don't
MAX_AGE = 24 * 3600


class InquiryForm(forms.Form):
    name = forms.CharField(label=_("Your name"), max_length=120)
    email = forms.EmailField(label=_("Email"))
    phone = forms.CharField(label=_("Phone"), max_length=40, required=False)
    desired_date = forms.DateField(label=_("Preferred date"), required=False, widget=DateInput())
    package = forms.ModelChoiceField(
        label=_("What are you planning?"), queryset=Package.objects.none(), required=False
    )
    message = forms.CharField(
        label=_("Message"), max_length=4000, widget=forms.Textarea(attrs={"rows": 5})
    )
    # Bots fill every field; people never see this one.
    website = forms.CharField(required=False, label=_("Leave this empty"))
    started = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, studio, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["package"].queryset = Package.objects.for_studio(studio).filter(is_active=True)
        self.fields["package"].empty_label = _("Not sure yet")
        self.fields["website"].widget.attrs.update(tabindex="-1", autocomplete="off")
        self.fields["name"].widget.attrs.update(autocomplete="name")
        self.fields["email"].widget.attrs.update(autocomplete="email")
        self.fields["phone"].widget.attrs.update(autocomplete="tel", type="tel")
        self.fields["desired_date"].widget.attrs.update(min=timezone.localdate().isoformat())
        if not self.is_bound:
            self.initial["started"] = signing.dumps(time.time(), salt=SALT)

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())  # one line, for the e-mail subject

    def clean_desired_date(self):
        value = self.cleaned_data.get("desired_date")
        if value and value < timezone.localdate():
            raise forms.ValidationError(_("Choose a date from today on."))
        return value

    def clean(self):
        data = super().clean()
        if data.get("website"):
            raise forms.ValidationError(_("The message couldn't be sent. Try again."))
        try:
            started = signing.loads(data.get("started", ""), salt=SALT, max_age=MAX_AGE)
        except signing.BadSignature as exc:
            msg = _("The form expired. Reload the page and try again.")
            raise forms.ValidationError(msg) from exc
        if time.time() - float(started) < MIN_SECONDS:
            raise forms.ValidationError(_("The message couldn't be sent. Try again."))
        return data
