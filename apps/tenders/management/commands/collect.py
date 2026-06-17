"""On-demand collection from all enabled sources.

Usage:
    python manage.py collect            # all enabled sources
    python manage.py collect --source eis
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.sources.models import Source
from apps.tenders.services import collect_all, collect_from_source


class Command(BaseCommand):
    help = "Collect tenders now from enabled sources (live)."

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Source code to collect (default: all)")
        parser.add_argument("--limit", type=int, default=settings.TENDER_FETCH_PAGE_SIZE)

    def handle(self, *args, **opts):
        limit = opts["limit"]
        if opts.get("source"):
            source = Source.objects.get(code=opts["source"])
            results = [collect_from_source(source, limit)]
        else:
            results = collect_all(limit)

        for r in results:
            style = self.style.SUCCESS if r.ok else self.style.WARNING
            self.stdout.write(style(
                f"  [{r.source_code}] ok={r.ok} fetched={r.fetched} "
                f"new={r.created} updated={r.updated}"
                + (f" error={r.error}" if r.error else "")
            ))
        total_new = sum(r.created for r in results)
        self.stdout.write(self.style.SUCCESS(f"Done. {total_new} new tender(s)."))
