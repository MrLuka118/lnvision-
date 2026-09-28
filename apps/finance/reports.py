from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import ExtractMonth

from .models import Expense, Income

ZERO = Decimal("0.00")


def total(qs):
    return qs.aggregate(value=Sum("amount"))["value"] or ZERO


def summary(studio, year, month=None):
    values = {}
    for key, model in [("income", Income), ("expenses", Expense)]:
        qs = model.objects.for_studio(studio)
        if month:
            qs = qs.filter(date__month=month)
        values[key] = total(qs.filter(date__year=year))
        values[f"previous_{key}"] = total(qs.filter(date__year=year - 1))
    values["profit"] = values["income"] - values["expenses"]
    values["previous_profit"] = values["previous_income"] - values["previous_expenses"]
    for key in ["income", "expenses", "profit"]:
        previous = values[f"previous_{key}"]
        values[f"{key}_change"] = (
            (values[key] - previous) / abs(previous) * 100 if previous else None
        )
    return values


def monthly(studio, year):
    result = [{"month": month, "income": ZERO, "expenses": ZERO} for month in range(1, 13)]
    for key, model in [("income", Income), ("expenses", Expense)]:
        rows = (
            model.objects.for_studio(studio)
            .filter(date__year=year)
            .annotate(month=ExtractMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        for row in rows:
            result[row["month"] - 1][key] = row["total"]
    for row in result:
        row["profit"] = row["income"] - row["expenses"]
    return result


def by_category(studio, year):
    return (
        Expense.objects.for_studio(studio)
        .filter(date__year=year)
        .values("category__name", "category__colour")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )


def top_clients(studio, year):
    return (
        Income.objects.for_studio(studio)
        .filter(date__year=year, client__isnull=False)
        .values("client_id", "client__first_name", "client__last_name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )
