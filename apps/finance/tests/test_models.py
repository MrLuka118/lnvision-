import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.finance.defaults import seed_categories
from apps.finance.models import ExpenseCategory, receipt_path

from .factories import (
    ExpenseFactory,
    InvoiceFactory,
    InvoiceLineFactory,
    RecurringExpenseFactory,
)

pytestmark = pytest.mark.django_db


def test_seed_categories_creates_six_default_categories(studio):
    seed_categories(studio)
    assert ExpenseCategory.objects.for_studio(studio).count() == 6
    # Calling again must not add more.
    seed_categories(studio)
    assert ExpenseCategory.objects.for_studio(studio).count() == 6


def test_two_expenses_for_same_recurring_and_period_raise_integrity_error(studio):
    recurring = RecurringExpenseFactory(studio=studio)
    period = datetime.date.today()
    ExpenseFactory(studio=studio, recurring=recurring, period=period)
    with pytest.raises(IntegrityError):
        ExpenseFactory(studio=studio, recurring=recurring, period=period)


def test_two_expenses_without_recurring_and_same_period_allowed(studio):
    period = datetime.date.today()
    ExpenseFactory(studio=studio, recurring=None, period=period)
    ExpenseFactory(studio=studio, recurring=None, period=period)


def test_invoice_totals(studio):
    invoice = InvoiceFactory(studio=studio, vat_rate=Decimal("22"))
    InvoiceLineFactory(
        invoice=invoice, quantity=Decimal("2"), unit_price=Decimal("100.00"), position=0
    )
    InvoiceLineFactory(
        invoice=invoice, quantity=Decimal("1"), unit_price=Decimal("49.99"), position=1
    )
    assert invoice.subtotal == Decimal("249.99")
    assert invoice.vat == Decimal("55.00")
    assert invoice.total == Decimal("304.99")


def test_invoice_number_unique_per_studio_non_empty(studio, other_studio):
    # Two empty numbers in one studio are fine.
    InvoiceFactory(studio=studio, number="")
    InvoiceFactory(studio=studio, number="")

    InvoiceFactory(studio=studio, number="2024-001")
    with pytest.raises(IntegrityError), transaction.atomic():
        InvoiceFactory(studio=studio, number="2024-001")

    # Same number in another studio is allowed.
    InvoiceFactory(studio=other_studio, number="2024-001")


def test_receipt_path_keeps_only_short_lowercase_suffix():
    class MockInstance:
        studio_id = 1

    path = receipt_path(MockInstance(), "REceipt.PDF")
    assert "receipts/1/" in path
    assert "REceipt.PDF" not in path
    assert ".pdf" in path

    # No suffix at all.
    path_no_ext = receipt_path(MockInstance(), "invoice")
    assert path_no_ext.startswith("receipts/1/")
    assert "invoice" not in path_no_ext


def test_seed_existing_studios(studio):
    # Remove any existing categories for this studio.
    ExpenseCategory.objects.filter(studio=studio).delete()

    import importlib

    from django.apps import apps

    migration_mod = importlib.import_module("apps.finance.migrations.0002_seed_default_categories")
    migration_mod.seed_existing_studios(apps, None)
    assert ExpenseCategory.objects.for_studio(studio).count() == 6

    # Calling again must not add more.
    migration_mod.seed_existing_studios(apps, None)
    assert ExpenseCategory.objects.for_studio(studio).count() == 6
