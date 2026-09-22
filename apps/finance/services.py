import calendar
from datetime import date

from django.utils import timezone

from .models import Expense, RecurringExpense


def occurrences(recurring: RecurringExpense, until: date) -> list[date]:
    """Return every occurrence of *recurring* that falls on or before *until*.

    Occurrence ``n`` (n = 0, 1, 2, …) is ``start_date`` plus *n* months (monthly) or
    *n* years (yearly), always counted from ``start_date``.  If the target month is
    shorter than ``start_date.day``, the last day of the month is used
    (``calendar.monthrange``).
    """
    result: list[date] = []
    start = recurring.start_date
    end = recurring.end_date
    interval = recurring.interval
    n = 0
    while True:
        if interval == RecurringExpense.Interval.MONTHLY:
            m = start.month - 1 + n
            y = start.year + m // 12
            month = (m % 12) + 1
        else:  # yearly
            y = start.year + n
            month = start.month
        last_day = calendar.monthrange(y, month)[1]
        day = min(start.day, last_day)
        dt = date(y, month, day)
        if dt > until:
            break
        if end is not None and dt > end:
            break
        result.append(dt)
        n += 1
    return result


def generate_recurring(today=None, queryset=None) -> int:
    """Create an ``Expense`` row for each missing occurrence ≤ *today*.

    *today* defaults to ``timezone.localdate()``.
    *queryset* defaults to active ``RecurringExpense`` rows across all studios.
    Returns the number of expenses that were actually created.
    """
    if today is None:
        today = timezone.localdate()
    if queryset is None:
        queryset = RecurringExpense.objects.filter(is_active=True)
    queryset = queryset.only(
        "studio_id",
        "category_id",
        "start_date",
        "end_date",
        "interval",
        "amount",
        "supplier",
        "name",
    )

    total = 0
    for rec in queryset:
        periods = occurrences(rec, today)
        if not periods:
            continue
        existing = set(
            Expense.objects.filter(recurring=rec, period__in=periods).values_list(
                "period", flat=True
            )
        )
        missing = [p for p in periods if p not in existing]
        if not missing:
            continue
        expenses = [
            Expense(
                studio_id=rec.studio_id,
                date=p,
                amount=rec.amount,
                category_id=rec.category_id,
                supplier=rec.supplier,
                description=rec.name,
                recurring=rec,
                period=p,
            )
            for p in missing
        ]
        Expense.objects.bulk_create(expenses, ignore_conflicts=True)
        total += len(missing)
    return total
