from django.apps import AppConfig


class PhotosConfig(AppConfig):
    name = "apps.photos"
    label = "photos"

    def ready(self):
        from . import signals  # noqa: F401
