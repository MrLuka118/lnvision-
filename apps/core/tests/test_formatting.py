from decimal import Decimal

import pytest

from apps.core.templatetags.formatting import eur


class TestEurFilter:
    """Tests for the eur template filter."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1234.5, "1.234,50\xa0€"),
            (0, "0,00\xa0€"),
            (Decimal("-12.3"), "\u221212,30\xa0€"),
            (1234567.891, "1.234.567,89\xa0€"),
            (None, ""),
            ("abc", ""),
        ],
    )
    def test_eur_formatting(self, value, expected):
        """eur filter formats numbers with Slovenian grouping."""
        assert eur(value) == expected

    def test_eur_zero_decimals(self):
        """eur filter respects decimals parameter."""
        assert eur(1234.5, 0) == "1.235\xa0€"


def test_long_date_uses_the_genitive_in_slovenian():
    from datetime import date

    from django.utils import translation

    from apps.core.templatetags.formatting import long_date

    with translation.override("sl"):
        assert long_date(date(2026, 7, 18)) == "18. julija 2026"
        assert long_date(date(2026, 3, 1), False) == "1. marca"
