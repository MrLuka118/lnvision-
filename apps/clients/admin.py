from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "partner_name", "email", "phone", "source", "studio")
    list_filter = ("source", "studio")
    search_fields = ("first_name", "last_name", "partner_name", "email", "phone", "company")
    list_select_related = ("studio",)
    readonly_fields = ("created_at", "updated_at")
