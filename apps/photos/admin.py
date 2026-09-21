from django.contrib import admin

from .models import Photo, UploadSession


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("original_name", "gallery", "status", "width", "height", "studio")
    list_filter = ("status", "studio")
    search_fields = ("original_name", "gallery__title")
    list_select_related = ("gallery", "studio")
    raw_id_fields = ("gallery", "section")
    readonly_fields = (
        "uuid", "sha256", "exif", "renditions", "rendition_version", "lqip", "dominant_color",
        "luminance", "error", "created_at", "updated_at",
    )  # fmt: skip


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("filename", "gallery", "status", "received_bytes", "size_bytes", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("gallery", "section", "photo")
    readonly_fields = ("uuid", "created_at", "updated_at")
