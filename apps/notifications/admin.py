from django.contrib import admin

from .models import TelegramProfile


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "chat_id", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "chat_id")
    autocomplete_fields = ("user",)
