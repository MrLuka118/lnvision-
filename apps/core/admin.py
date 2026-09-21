from django.contrib import admin

from apps.core.models import Studio


@admin.register(Studio)
class StudioAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "slug", "owner__email")
    readonly_fields = ("ics_token", "created_at", "updated_at")
    raw_id_fields = ("owner",)
