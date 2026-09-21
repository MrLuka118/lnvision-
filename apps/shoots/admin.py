from django.contrib import admin

from .models import Location, Package, Shoot


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "studio")
    list_filter = ("studio",)
    search_fields = ("name", "address")
    list_select_related = ("studio",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_minutes", "delivery_days", "is_active", "studio")
    list_filter = ("is_active", "studio")
    search_fields = ("name",)
    list_select_related = ("studio",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Shoot)
class ShootAdmin(admin.ModelAdmin):
    list_display = ("title", "client", "status", "price", "package", "studio")
    list_filter = ("status", "studio")
    search_fields = ("title", "client__first_name", "client__last_name", "client__email")
    list_select_related = ("client", "package", "studio")
    raw_id_fields = ("client", "package", "location")
    readonly_fields = ("status_changed_at", "created_at", "updated_at")
