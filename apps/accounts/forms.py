from allauth.account.forms import SignupForm as BaseSignupForm
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.services import ensure_studio


class SignupForm(BaseSignupForm):
    studio_name = forms.CharField(
        label=_("Studio name"),
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "organization"}),
        help_text=_("Shown to your clients. You can change it later."),
    )

    field_order = ["studio_name", "email", "password1"]

    def save(self, request):
        user = super().save(request)
        ensure_studio(user, self.cleaned_data["studio_name"])
        return user
