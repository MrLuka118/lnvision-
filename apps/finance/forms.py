from decimal import Decimal
from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _
from PIL import Image

from apps.core.forms import DateInput, StudioModelForm

from .models import Expense, ExpenseCategory, Income, RecurringExpense


class PositiveAmountForm(StudioModelForm):
    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError(_("Enter an amount greater than zero."))
        return amount


class IncomeForm(PositiveAmountForm):
    layout = [(None, [("date", "amount"), "description", ("client", "shoot"), "method"])]

    class Meta:
        model = Income
        fields = ["date", "amount", "description", "client", "shoot", "method"]
        widgets = {"date": DateInput()}

    def clean(self):
        data = super().clean()
        shoot, client = data.get("shoot"), data.get("client")
        if shoot:
            if client and shoot.client_id != client.pk:
                self.add_error("client", _("Choose the client linked to this shoot."))
            elif not client:
                data["client"] = shoot.client
        return data


class ExpenseForm(PositiveAmountForm):
    layout = [
        (
            None,
            [("date", "amount"), ("category", "supplier"), "description", "vat_amount", "receipt"],
        )
    ]

    class Meta:
        model = Expense
        fields = ["date", "amount", "category", "supplier", "description", "vat_amount", "receipt"]
        widgets = {
            "date": DateInput(),
            "receipt": forms.ClearableFileInput(
                attrs={"accept": "image/jpeg,image/png,image/webp,application/pdf"}
            ),
        }

    def clean_receipt(self):
        value = self.cleaned_data.get("receipt")
        if not value or not hasattr(value, "content_type"):
            return value
        if value.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_("Receipts must be smaller than 10 MB."))
        suffix = Path(value.name).suffix.lower()
        try:
            if suffix == ".pdf":
                if value.read(5) != b"%PDF-":
                    raise ValueError
            elif suffix in {".jpg", ".jpeg", ".png", ".webp"}:
                Image.open(value).verify()
            else:
                raise ValueError
        except (ValueError, OSError, Image.DecompressionBombError) as exc:
            raise forms.ValidationError(
                _("Upload a valid PDF, JPEG, PNG or WebP receipt.")
            ) from exc
        finally:
            value.seek(0)
        return value

    def clean(self):
        data = super().clean()
        vat, amount = data.get("vat_amount"), data.get("amount")
        if vat is not None and (vat < Decimal("0") or (amount and vat > amount)):
            self.add_error("vat_amount", _("VAT must be between zero and the expense amount."))
        return data


class CategoryForm(StudioModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ["name", "colour", "position"]
        widgets = {"colour": forms.TextInput(attrs={"type": "color"})}

    def clean_colour(self):
        import re

        colour = self.cleaned_data["colour"]
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", colour):
            raise forms.ValidationError(_("Use a six-digit hex colour."))
        return colour

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if (
            ExpenseCategory.objects.for_studio(self.studio)
            .filter(name=name)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(_("This category already exists."))
        return name


class RecurringForm(PositiveAmountForm):
    class Meta:
        model = RecurringExpense
        fields = [
            "name",
            "supplier",
            "amount",
            "category",
            "interval",
            "start_date",
            "end_date",
            "is_active",
        ]
        widgets = {"start_date": DateInput(), "end_date": DateInput()}

    def clean(self):
        data = super().clean()
        if (
            data.get("end_date")
            and data.get("start_date")
            and data["end_date"] < data["start_date"]
        ):
            self.add_error("end_date", _("The end date must follow the start date."))
        return data
