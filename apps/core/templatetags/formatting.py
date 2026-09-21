from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()

MINUS = "\N{MINUS SIGN}"
NBSP = "\N{NO-BREAK SPACE}"


@register.filter
def eur(value, decimals=2):
    """1234.5 -> '1.234,50 €' (Slovenian grouping, non-breaking space before the sign)."""
    if value is None or value == "":
        return ""
    try:
        amount = Decimal(str(value))
        decimals = int(decimals)
    except (InvalidOperation, ValueError, TypeError):
        return ""
    amount = amount.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    sign = MINUS if amount < 0 else ""
    whole, _, fraction = f"{abs(amount):.{decimals}f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    number = f"{grouped},{fraction}" if decimals else grouped
    return f"{sign}{number}{NBSP}€"


@register.filter
def duration(minutes):
    """90 -> '1 h 30 min', 120 -> '2 h', 45 -> '45 min'."""
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return ""
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours}{NBSP}h {rest}{NBSP}min"
    if hours:
        return f"{hours}{NBSP}h"
    return f"{rest}{NBSP}min"


# Slovenian dates put the month in the genitive: "18. julija 2026", not "18. julij 2026".
SL_MONTHS_GENITIVE = [
    "januarja", "februarja", "marca", "aprila", "maja", "junija",
    "julija", "avgusta", "septembra", "oktobra", "novembra", "decembra",
]  # fmt: skip


@register.filter
def long_date(value, with_year=True):
    """A date written out: '18. julija 2026' in Slovenian, the locale's own form otherwise."""
    if not value:
        return ""
    from django.utils import formats, timezone, translation

    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        value = timezone.localtime(value)
    if translation.get_language() == "sl":
        text = f"{value.day}. {SL_MONTHS_GENITIVE[value.month - 1]}"
        return f"{text} {value.year}" if with_year else text
    return formats.date_format(value, "j F Y" if with_year else "j F")
