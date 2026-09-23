import datetime
from decimal import Decimal

import pytest
from django.db import connection, reset_queries

from apps.finance.models import Expense, RecurringExpense
from apps.finance.services import generate_recurring, occurrences
from apps.finance.tests.factories import ExpenseCategoryFactory, RecurringExpenseFactory


# ---------------------------------------------------------------------------
# occurrences
# ---------------------------------------------------------------------------
class DescribeOccurrences:
    def test_monthly_start_at_end_of_month(self):
        """The 31st rule: start 31 Jan → 28 Feb → 31 Mar → 30 Apr."""
        rec = RecurringExpense(
            start_date=datetime.date(2027, 1, 31),
            interval=RecurringExpense.Interval.MONTHLY,
            end_date=None,
        )
        until = datetime.date(2027, 4, 30)
        result = occurrences(rec, until)
        assert result == [
            datetime.date(2027, 1, 31),
            datetime.date(2027, 2, 28),
            datetime.date(2027, 3, 31),
            datetime.date(2027, 4, 30),
        ]

    def test_yearly_start_leap_day(self):
        """Yearly from 29 Feb 2028 → 28 Feb 2029 → 28 Feb 2030."""
        rec = RecurringExpense(
            start_date=datetime.date(2028, 2, 29),
            interval=RecurringExpense.Interval.YEARLY,
            end_date=None,
        )
        until = datetime.date(2030, 2, 28)
        result = occurrences(rec, until)
        assert result == [
            datetime.date(2028, 2, 29),
            datetime.date(2029, 2, 28),
            datetime.date(2030, 2, 28),
        ]

    def test_respects_end_date(self):
        rec = RecurringExpense(
            start_date=datetime.date(2027, 1, 1),
            interval=RecurringExpense.Interval.MONTHLY,
            end_date=datetime.date(2027, 3, 15),
        )
        until = datetime.date(2028, 1, 1)
        result = occurrences(rec, until)
        assert result == [
            datetime.date(2027, 1, 1),
            datetime.date(2027, 2, 1),
            datetime.date(2027, 3, 1),
        ]

    def test_yearly_end_date(self):
        """Yearly with an end_date that stops before the next occurrence."""
        rec = RecurringExpense(
            start_date=datetime.date(2020, 6, 30),
            interval=RecurringExpense.Interval.YEARLY,
            end_date=datetime.date(2022, 6, 15),
        )
        until = datetime.date(2025, 6, 30)
        result = occurrences(rec, until)
        assert result == [
            datetime.date(2020, 6, 30),
            datetime.date(2021, 6, 30),
        ]


# ---------------------------------------------------------------------------
# generate_recurring
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestGenerateRecurring:
    def test_inactive_recurring_is_skipped(self, studio):
        cat = ExpenseCategoryFactory(studio=studio)
        rec = RecurringExpenseFactory(
            studio=studio,
            category=cat,
            is_active=False,
            start_date=datetime.date.today() - datetime.timedelta(days=5),
            interval=RecurringExpense.Interval.MONTHLY,
        )
        count = generate_recurring()
        assert count == 0
        assert not Expense.objects.filter(recurring=rec).exists()

    def test_catch_up_four_occurrences(self, studio):
        """A recurring expense started three months ago gets four occurrences."""
        cat = ExpenseCategoryFactory(studio=studio)
        today = datetime.date(2027, 4, 20)
        start = datetime.date(2027, 1, 20)
        rec = RecurringExpenseFactory(
            studio=studio,
            category=cat,
            start_date=start,
            interval=RecurringExpense.Interval.MONTHLY,
            is_active=True,
        )
        count = generate_recurring(today=today)
        assert count == 4
        expenses = Expense.objects.filter(recurring=rec).order_by("period")
        assert expenses.count() == 4
        assert [e.period for e in expenses] == [
            datetime.date(2027, 1, 20),
            datetime.date(2027, 2, 20),
            datetime.date(2027, 3, 20),
            datetime.date(2027, 4, 20),
        ]

    def test_idempotent_no_duplicates(self, studio):
        """Running generate_recurring twice creates nothing the second time."""
        cat = ExpenseCategoryFactory(studio=studio)
        rec = RecurringExpenseFactory(
            studio=studio,
            category=cat,
            start_date=datetime.date(2027, 1, 20),
            interval=RecurringExpense.Interval.MONTHLY,
            is_active=True,
        )
        today = datetime.date(2027, 4, 20)
        first = generate_recurring(today=today)
        assert first > 0
        second = generate_recurring(today=today)
        assert second == 0
        assert Expense.objects.filter(recurring=rec).count() == first

    def test_changed_amount_affects_only_new(self, studio):
        """A change of the recurring amount does not alter expenses that were already generated."""
        cat = ExpenseCategoryFactory(studio=studio)
        today_mar = datetime.date(2027, 3, 20)
        rec = RecurringExpenseFactory(
            studio=studio,
            category=cat,
            start_date=datetime.date(2027, 1, 20),
            interval=RecurringExpense.Interval.MONTHLY,
            is_active=True,
            amount=Decimal("100.00"),
        )
        generate_recurring(today=today_mar)

        rec.amount = Decimal("200.00")
        rec.save(update_fields=["amount"])
        today_apr = datetime.date(2027, 4, 20)
        generate_recurring(today=today_apr)

        expenses = Expense.objects.filter(recurring=rec).order_by("period")
        assert expenses.count() == 4
        amounts = [e.amount for e in expenses]
        assert amounts[:3] == [Decimal("100.00"), Decimal("100.00"), Decimal("100.00")]
        assert amounts[3] == Decimal("200.00")

    def test_expenses_land_in_correct_studio(self, studio):
        """Every generated Expense belongs to the same studio as its recurring expense."""
        cat = ExpenseCategoryFactory(studio=studio)
        rec = RecurringExpenseFactory(
            studio=studio,
            category=cat,
            start_date=datetime.date(2027, 1, 1),
            interval=RecurringExpense.Interval.MONTHLY,
            is_active=True,
        )
        generate_recurring(today=datetime.date(2027, 2, 1))
        assert Expense.objects.filter(recurring=rec).exists()
        assert all(e.studio == studio for e in Expense.objects.filter(recurring=rec))

    def test_query_count_does_not_grow_with_occurrences(self, studio):
        """The number of database queries is independent of how many occurrences are created."""
        cat = ExpenseCategoryFactory(studio=studio)
        RecurringExpenseFactory(
            studio=studio,
            category=cat,
            start_date=datetime.date(2020, 1, 1),
            interval=RecurringExpense.Interval.MONTHLY,
            is_active=True,
        )

        def _gen(today):
            reset_queries()
            generate_recurring(today=today)
            return len(connection.queries)

        # one occurrence
        q1 = _gen(datetime.date(2020, 1, 2))
        # many occurrences (catch-up of ~36 months)
        q2 = _gen(datetime.date(2022, 12, 31))
        assert q1 == q2
