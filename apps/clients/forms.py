from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StudioModelForm

from .models import Client


class ClientForm(StudioModelForm):
    layout = [
        (None, [("first_name", "last_name"), "partner_name"]),
        (_("Contact"), [("email", "phone"), "address"]),
        (_("For invoices"), [("company", "vat_id")]),
        (_("Other"), ["source", "notes"]),
    ]

    class Meta:
        model = Client
        fields = [
            "first_name",
            "last_name",
            "partner_name",
            "email",
            "phone",
            "address",
            "company",
            "vat_id",
            "source",
            "notes",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "email": forms.EmailInput(attrs={"autocomplete": "off"}),
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "off"}),
        }
