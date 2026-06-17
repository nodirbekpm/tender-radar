from django.contrib import admin

from .models import Source, UserSourcePermission


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "adapter_key", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("name", "code")
    list_editable = ("is_enabled",)
    prepopulated_fields = {"code": ("name",)}


@admin.register(UserSourcePermission)
class UserSourcePermissionAdmin(admin.ModelAdmin):
    list_display = ("user", "source", "can_view", "granted_at", "granted_by")
    list_filter = ("can_view", "source")
    search_fields = ("user__username", "source__name")
    autocomplete_fields = ("user", "source")
    list_editable = ("can_view",)
