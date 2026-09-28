from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.clients.tests.factories import ClientFactory
from apps.finance import reports
from apps.finance.forms import ExpenseForm
from apps.finance.models import Expense, Income
from apps.finance.tests.factories import ExpenseCategoryFactory, ExpenseFactory, IncomeFactory
from apps.shoots.tests.factories import ShootFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "name",
    ["dashboard", "income_list", "expense_list", "category_list", "recurring_list", "suggestions"],
)
def test_finance_requires_login_and_renders_for_owner(name, client, auth_client):
    url = reverse("finance:" + name)
    assert client.get(url).status_code == 302
    assert auth_client.get(url).status_code == 200


def test_ledger_scopes_period_and_totals(auth_client, studio, other_studio):
    IncomeFactory(studio=studio, date=date(2026, 2, 1), amount=1234, description="OWN-PAYMENT")
    IncomeFactory(studio=studio, date=date(2026, 3, 1), description="OTHER-MONTH")
    IncomeFactory(studio=other_studio, date=date(2026, 2, 1), description="FOREIGN-PAYMENT")
    response = auth_client.get(reverse("finance:income_list"), {"leto": 2026, "mesec": 2})
    assert response.context["total"] == 1234
    assert b"OWN-PAYMENT" in response.content
    assert b"FOREIGN-PAYMENT" not in response.content
    assert b"OTHER-MONTH" not in response.content


def test_foreign_relationships_are_rejected(auth_client, studio, other_studio):
    foreign = ClientFactory(studio=other_studio)
    response = auth_client.post(
        reverse("finance:income_create"),
        {"date": "2026-09-01", "amount": "100", "client": foreign.pk, "method": "transfer"},
    )
    assert response.status_code == 400
    assert not Income.objects.for_studio(studio).exists()
    category = ExpenseCategoryFactory(studio=other_studio)
    response = auth_client.post(
        reverse("finance:expense_create"),
        {"date": "2026-09-01", "amount": "100", "category": category.pk},
    )
    assert response.status_code == 400


def test_income_creation_and_negative_amount(auth_client, studio):
    data = {"date": "2026-09-01", "amount": "100.50", "method": "transfer"}
    assert auth_client.post(reverse("finance:income_create"), data).status_code == 302
    assert Income.objects.for_studio(studio).get().amount == Decimal("100.50")
    data["amount"] = "-1"
    assert auth_client.post(reverse("finance:income_create"), data).status_code == 400


@pytest.mark.parametrize(
    "filename,content",
    [
        ("virus.exe", b"bad"),
        ("fake.jpg", b"not a photo"),
        ("fake.pdf", b"not pdf"),
        ("huge.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024)),
    ],
)
def test_receipt_validation(studio, filename, content):
    category = ExpenseCategoryFactory(studio=studio)
    form = ExpenseForm(
        data={"date": "2026-09-01", "amount": "10", "category": category.pk},
        files={"receipt": SimpleUploadedFile(filename, content)},
        studio=studio,
    )
    assert not form.is_valid()
    assert "receipt" in form.errors


def test_receipt_download_is_private(auth_client, studio):
    expense = ExpenseFactory(studio=studio, receipt=SimpleUploadedFile("receipt.pdf", b"%PDF-1.7"))
    response = auth_client.get(reverse("finance:receipt", args=[expense.pk]))
    assert response.status_code == 200
    assert response["Cache-Control"] == "private, no-store"
    assert response["Content-Disposition"].startswith("attachment")
    response.close()


def test_category_protection(auth_client, studio):
    expense = ExpenseFactory(studio=studio)
    response = auth_client.post(reverse("finance:category_delete", args=[expense.category_id]))
    assert response.status_code == 302
    assert Expense.objects.filter(pk=expense.pk).exists()


def test_suggestions_record_only_remaining_once(auth_client, studio, other_studio):
    shoot = ShootFactory(studio=studio, status="delivered", price=500)
    IncomeFactory(studio=studio, shoot=shoot, amount=200)
    response = auth_client.get(reverse("finance:suggestions"))
    assert response.context["rows"][0]["remaining"] == 300
    url = reverse("finance:suggestions")
    assert auth_client.post(url, {"shoot": shoot.pk}).status_code == 302
    assert auth_client.post(url, {"shoot": shoot.pk}).status_code == 302
    assert reports.total(Income.objects.filter(shoot=shoot)) == 500
    foreign = ShootFactory(studio=other_studio, status="delivered")
    assert auth_client.post(url, {"shoot": foreign.pk}).status_code == 404


def test_csv_scope_decimal_and_formula_safety(auth_client, studio, other_studio):
    IncomeFactory(
        studio=studio, date=date(2026, 9, 1), amount="1234.50", description='=HYPERLINK("evil")'
    )
    ExpenseFactory(studio=studio, date=date(2026, 9, 2), amount="50.25")
    IncomeFactory(studio=other_studio, date=date(2026, 9, 1), description="FOREIGN")
    response = auth_client.get(reverse("finance:export"), {"leto": 2026})
    text = response.content.decode()
    assert text.startswith("\ufeffDatum;")
    assert "1234,50" in text and "-50,25" in text
    assert "'=HYPERLINK" in text and "FOREIGN" not in text


def test_recurring_form_generates_history(auth_client, studio):
    category = ExpenseCategoryFactory(studio=studio)
    today = timezone.localdate()
    start = today.replace(day=1, month=max(1, today.month - 2))
    response = auth_client.post(
        reverse("finance:recurring_create"),
        {
            "name": "Editing software",
            "amount": "30",
            "category": category.pk,
            "interval": "monthly",
            "start_date": start,
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    assert Expense.objects.for_studio(studio).count() == today.month - start.month + 1


def test_reports_are_scoped_and_fill_missing_months(studio, other_studio):
    IncomeFactory(studio=studio, date=date(2026, 2, 1), amount=600)
    IncomeFactory(studio=studio, date=date(2025, 2, 1), amount=300)
    IncomeFactory(studio=other_studio, date=date(2026, 2, 1), amount=9999)
    ExpenseFactory(studio=studio, date=date(2026, 2, 1), amount=100)
    rows = reports.monthly(studio, 2026)
    assert len(rows) == 12
    assert rows[0]["profit"] == 0
    assert rows[1]["profit"] == 500
    summary = reports.summary(studio, 2026)
    assert summary["income_change"] == 100
    assert summary["expenses_change"] is None
    assert next(iter(reports.by_category(studio, 2026)))["total"] == 100
    assert next(iter(reports.top_clients(studio, 2026)))["total"] == 600


def test_dashboard_data_renders_and_queries_stay_bounded(
    auth_client, studio, django_assert_max_num_queries
):
    IncomeFactory.create_batch(20, studio=studio)
    ExpenseFactory.create_batch(20, studio=studio)
    with django_assert_max_num_queries(25):
        response = auth_client.get(reverse("finance:dashboard"))
    assert response.status_code == 200
    assert b"finance-chart" in response.content
    with django_assert_max_num_queries(10):
        assert auth_client.get(reverse("finance:income_list")).status_code == 200
