from django.conf import settings
from django.db import migrations
from django.utils.translation import override


def seed_existing_studios(apps, schema_editor):
    Studio = apps.get_model("core", "Studio")
    ExpenseCategory = apps.get_model("finance", "ExpenseCategory")
    from apps.finance.defaults import DEFAULT_CATEGORIES

    for studio in Studio.objects.all():
        if ExpenseCategory.objects.filter(studio=studio).exists():
            continue
        categories = []
        for position, (name_lazy, colour) in enumerate(DEFAULT_CATEGORIES):
            with override(settings.LANGUAGE_CODE):
                name = str(name_lazy)
            categories.append(
                ExpenseCategory(
                    studio=studio,
                    name=name,
                    colour=colour,
                    position=position,
                )
            )
        ExpenseCategory.objects.bulk_create(categories)


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0001_initial"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_existing_studios, reverse_code=migrations.RunPython.noop),
    ]
