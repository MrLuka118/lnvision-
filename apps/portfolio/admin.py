from django.contrib import admin

from .models import Inquiry, Portfolio, PortfolioCategory, PortfolioStory, PortfolioStoryPhoto


class PortfolioStoryPhotoInline(admin.TabularInline):
    model = PortfolioStoryPhoto
    extra = 0
    raw_id_fields = ("photo",)


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("studio", "is_published", "look")
    raw_id_fields = ("portrait",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(PortfolioCategory)
class PortfolioCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "position", "studio")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")


@admin.register(PortfolioStory)
class PortfolioStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "is_featured", "studio")
    list_filter = ("is_published", "is_featured", "studio")
    raw_id_fields = ("gallery", "cover_photo")
    readonly_fields = ("created_at", "updated_at")
    inlines = [PortfolioStoryPhotoInline]


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "desired_date", "created_at", "studio")
    readonly_fields = ("created_at", "updated_at", "ip_hash", "client", "shoot")
    raw_id_fields = ("package", "client", "shoot")
