from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Photo


@receiver(post_delete, sender=Photo)
def remove_files(sender, instance: Photo, **kwargs):
    """However a photo goes (its own delete, its gallery's, a whole account's), its files go too,
    once the database change is committed."""
    from .services import delete_renditions

    def cleanup():
        delete_renditions(instance)
        if instance.original:
            instance.original.storage.delete(instance.original.name)

    transaction.on_commit(cleanup)
