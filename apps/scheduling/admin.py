from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("__str__", "kind", "start", "end", "all_day", "is_tentative", "studio")
    list_filter = ("kind", "all_day", "is_tentative", "studio")
    search_fields = ("title", "shoot__title", "client__first_name", "client__last_name")
    list_select_related = ("shoot", "client", "studio")
    raw_id_fields = ("shoot", "client", "location")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "start"
