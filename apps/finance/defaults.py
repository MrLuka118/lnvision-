from django.utils.translation import gettext_lazy as _

DEFAULT_CATEGORIES = [
    (_("Equipment"), "#735244"),
    (_("Software and subscriptions"), "#627a9d"),
    (_("Travel"), "#d67e2c"),
    (_("Marketing"), "#8580b1"),
    (_("Studio and rent"), "#576c43"),
    (_("Other"), "#8f8f8f"),
]


def seed_categories(studio):
    from .models import ExpenseCategory

    if ExpenseCategory.objects.for_studio(studio).exists():
        return
    for position, (name, colour) in enumerate(DEFAULT_CATEGORIES):
        ExpenseCategory.objects.create(studio=studio, name=name, colour=colour, position=position)
