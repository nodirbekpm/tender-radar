from django.contrib import admin

from .models import Tender, TenderDocument


class TenderDocumentInline(admin.TabularInline):
    model = TenderDocument
    extra = 0


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = (
        "number", "title_short", "source", "fz_type", "price", "region",
        "published_at",
    )
    list_filter = ("source", "fz_type", "region")
    search_fields = ("number", "title", "customer", "external_id")
    date_hierarchy = "published_at"
    inlines = [TenderDocumentInline]
    readonly_fields = ("first_seen_at", "updated_at", "raw")

    @admin.display(description="Title")
    def title_short(self, obj):
        return (obj.title[:80] + "…") if len(obj.title) > 80 else obj.title
