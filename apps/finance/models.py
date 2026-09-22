import uuid
from decimal import ROUND_HALF_UP, Decimal
from pathlib import PurePosixPath

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel


def receipt_path(instance, filename):
    suffix = PurePosixPath(filename).suffix.lower()[:6]
    return f"receipts/{instance.studio_id}/{uuid.uuid4().hex}{suffix}"


def invoice_pdf_path(instance, filename):
    return f"invoices/{instance.studio_id}/{uuid.uuid4().hex}.pdf"


class ExpenseCategory(TenantModel):
    name = models.CharField(_("name"), max_length=60)
    colour = models.CharField(_("colour"), max_length=7)
    position = models.PositiveSmallIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("expense category")
        verbose_name_plural = _("expense categories")
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["studio", "name"],
                name="unique_category_name_per_studio",
            )
        ]

    def __str__(self):
        return self.name


class RecurringExpense(TenantModel):
    class Interval(models.TextChoices):
        MONTHLY = "monthly", _("Monthly")
        YEARLY = "yearly", _("Yearly")

    name = models.CharField(_("name"), max_length=120)
    supplier = models.CharField(_("supplier"), max_length=120, blank=True)
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("category"),
    )
    interval = models.CharField(
        _("interval"), max_length=8, choices=Interval.choices, default=Interval.MONTHLY
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"), null=True, blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("recurring expense")
        verbose_name_plural = _("recurring expenses")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(TenantModel):
    date = models.DateField(_("date"))
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    vat_amount = models.DecimalField(
        _("VAT included"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
        verbose_name=_("category"),
    )
    supplier = models.CharField(_("supplier"), max_length=120, blank=True)
    description = models.CharField(_("description"), max_length=200, blank=True)
    receipt = models.FileField(_("receipt"), upload_to=receipt_path, max_length=255, blank=True)
    recurring = models.ForeignKey(
        RecurringExpense,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name=_("recurring expense"),
    )
    period = models.DateField(_("period"), null=True, blank=True)

    class Meta:
        verbose_name = _("expense")
        verbose_name_plural = _("expenses")
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["recurring", "period"],
                condition=Q(recurring__isnull=False),
                name="one_expense_per_period",
            )
        ]

    def __str__(self):
        return f"{self.date} {self.supplier}"


class InvoiceSequence(TenantModel):
    year = models.PositiveSmallIntegerField(_("year"))
    last_number = models.PositiveIntegerField(_("last number"), default=0)

    class Meta:
        verbose_name = _("invoice sequence")
        verbose_name_plural = _("invoice sequences")
        constraints = [
            models.UniqueConstraint(
                fields=["studio", "year"],
                name="unique_sequence_per_year",
            )
        ]

    def __str__(self):
        return f"{self.studio} / {self.year}"


class Invoice(TenantModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ISSUED = "issued", _("Issued")
        PAID = "paid", _("Paid")

    number = models.CharField(_("number"), max_length=20, blank=True)
    year = models.PositiveSmallIntegerField(_("year"), null=True, blank=True)
    sequence = models.PositiveIntegerField(_("sequence"), null=True, blank=True)
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name=_("client"),
    )
    shoot = models.ForeignKey(
        "shoots.Shoot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
        verbose_name=_("shoot"),
    )
    issue_date = models.DateField(_("issue date"), null=True, blank=True)
    service_date = models.DateField(_("service date"), null=True, blank=True)
    due_date = models.DateField(_("due date"), null=True, blank=True)
    vat_rate = models.DecimalField(
        _("VAT rate"), max_digits=5, decimal_places=2, default=Decimal("0")
    )
    vat_note = models.CharField(_("VAT note"), max_length=200, blank=True)
    notes = models.TextField(_("notes"), blank=True)
    status = models.CharField(
        _("status"), max_length=8, choices=Status.choices, default=Status.DRAFT
    )
    pdf = models.FileField(_("PDF"), upload_to=invoice_pdf_path, max_length=255, blank=True)

    class Meta:
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        ordering = ["-issue_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["studio", "number"],
                condition=~Q(number=""),
                name="invoice_number_per_studio",
            )
        ]

    def __str__(self):
        return self.number or str(self.id)

    @property
    def subtotal(self) -> Decimal:
        lines = self.lines.all()
        if not lines:
            return Decimal("0.00")
        subtotal = sum(line.total for line in lines)
        return subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def vat(self) -> Decimal:
        subtotal = self.subtotal
        vat = (subtotal * self.vat_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return vat

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.vat).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name=_("invoice"),
    )
    description = models.CharField(_("description"), max_length=200)
    quantity = models.DecimalField(
        _("quantity"), max_digits=8, decimal_places=2, default=Decimal("1")
    )
    unit_price = models.DecimalField(_("unit price"), max_digits=10, decimal_places=2)
    position = models.PositiveIntegerField(_("position"), default=0)

    class Meta:
        verbose_name = _("invoice line")
        verbose_name_plural = _("invoice lines")
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.unit_price})"

    @property
    def total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Income(TenantModel):
    class Method(models.TextChoices):
        TRANSFER = "transfer", _("Bank transfer")
        CASH = "cash", _("Cash")
        CARD = "card", _("Card")
        OTHER = "other", _("Other")

    date = models.DateField(_("date"))
    amount = models.DecimalField(_("amount"), max_digits=10, decimal_places=2)
    description = models.CharField(_("description"), max_length=200, blank=True)
    method = models.CharField(
        _("method"),
        max_length=10,
        choices=Method.choices,
        default=Method.TRANSFER,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incomes",
        verbose_name=_("client"),
    )
    shoot = models.ForeignKey(
        "shoots.Shoot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incomes",
        verbose_name=_("shoot"),
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name=_("invoice"),
    )

    class Meta:
        verbose_name = _("income")
        verbose_name_plural = _("incomes")
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} {self.amount}"
