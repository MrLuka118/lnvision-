from django.contrib import admin

from .models import Gallery, GallerySection


class SectionInline(admin.TabularInline):
    model = GallerySection
    extra = 0
    fields = ("title", "position")


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "is_published", "expires_at", "theme", "studio")
    list_filter = ("is_published", "theme", "studio")
    search_fields = ("title", "client__first_name", "client__last_name")
    list_select_related = ("client", "studio")
    raw_id_fields = ("shoot", "client", "cover_photo")
    readonly_fields = ("token", "password_version", "published_at", "created_at", "updated_at")
    inlines = [SectionInline]
