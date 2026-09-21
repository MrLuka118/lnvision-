# Slovenian formats, overriding Django's defaults (which start the week on Sunday
# and spell the month out in DATE_FORMAT).
DATE_FORMAT = "j. n. Y"
SHORT_DATE_FORMAT = "j. n. Y"
DATETIME_FORMAT = "j. n. Y, H:i"
SHORT_DATETIME_FORMAT = "j. n. Y, H:i"
TIME_FORMAT = "H:i"
MONTH_DAY_FORMAT = "j. F"
YEAR_MONTH_FORMAT = "F Y"
FIRST_DAY_OF_WEEK = 1

DATE_INPUT_FORMATS = ["%Y-%m-%d", "%d. %m. %Y", "%d.%m.%Y", "%d. %m. %y", "%d.%m.%y"]
DATETIME_INPUT_FORMATS = [
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%d. %m. %Y %H:%M",
    "%d.%m.%Y %H:%M",
]

DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
