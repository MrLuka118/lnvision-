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
