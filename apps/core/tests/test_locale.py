from datetime import date, datetime

from django.conf import settings
from django.utils.formats import date_format, get_format
from django.utils.translation import override


class TestLocalization:
    """Tests for Slovenian localization settings."""

    def test_date_format_slovenian(self):
        """Date is formatted as '21. 9. 2026' (Slovenian)."""
        with override("sl"):
            result = date_format(date(2026, 9, 21))
            assert result == "21. 9. 2026"

    def test_datetime_format_slovenian(self):
        """Datetime is formatted with Slovenian format."""
        with override("sl"):
            result = date_format(datetime(2026, 9, 21, 14, 5), "DATETIME_FORMAT")
            assert result == "21. 9. 2026, 14:05"

    def test_first_day_of_week(self):
        """Week starts on Monday (1)."""
        with override("sl"):
            assert get_format("FIRST_DAY_OF_WEEK") == 1

    def test_timezone_setting(self):
        """Timezone is set to Europe/Ljubljana."""
        assert settings.TIME_ZONE == "Europe/Ljubljana"
