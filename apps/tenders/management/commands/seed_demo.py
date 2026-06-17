"""Idempotent demo seeder.

Creates:
  * Source rows for EIS + every registered commercial stub.
  * An admin superuser and a demo user (demo sees ONLY EIS).
  * The hourly Celery-beat periodic task.
  * Tenders: a live EIS fetch first; if that yields nothing (offline), it
    falls back to bundled real-shaped EIS samples so the demo is never empty.

Safe to run repeatedly.
"""
from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sources.adapters import registered_keys, get_adapter
from apps.sources.adapters.sample_data import eis_sample_tenders
from apps.sources.models import Source, UserSourcePermission
from apps.tenders.services import collect_from_source, upsert_tender

# Friendly display names for known adapter keys.
SOURCE_NAMES = {
    "eis": "ЕИС (zakupki.gov.ru)",
    "sberbank_ast": "Sberbank-AST",
    "rts_tender": "RTS-tender",
    "b2b_center": "B2B-Center",
    "fabrikant": "Fabrikant",
    "otc": "OTC.ru",
}


class Command(BaseCommand):
    help = "Seed demo data: sources, users, permissions, periodic task, tenders."

    def handle(self, *args, **options):
        self.stdout.write("Seeding sources ...")
        sources = self._seed_sources()

        self.stdout.write("Seeding users & permissions ...")
        admin, demo = self._seed_users(sources["eis"])

        self.stdout.write("Setting up periodic collection task ...")
        self._seed_periodic_task()

        self.stdout.write("Collecting EIS tenders ...")
        self._seed_tenders(sources["eis"])

        self.stdout.write(self.style.SUCCESS("Demo seed complete."))
        self.stdout.write(
            "  Admin login: %s / %s"
            % (
                os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin"),
                os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin12345"),
            )
        )
        self.stdout.write("  Demo login: demo / demo12345  (EIS only)")

    # ------------------------------------------------------------------ #

    def _seed_sources(self) -> dict[str, Source]:
        created: dict[str, Source] = {}
        for key in registered_keys():
            adapter_cls = get_adapter(key)
            source, _ = Source.objects.update_or_create(
                code=key,
                defaults={
                    "name": SOURCE_NAMES.get(key, adapter_cls.label or key),
                    "adapter_key": key,
                    "is_enabled": True,
                    "website_url": "https://zakupki.gov.ru" if key == "eis" else "",
                },
            )
            created[key] = source
        return created

    def _seed_users(self, eis: Source) -> tuple[User, User]:
        admin_username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        admin_password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin12345")
        admin, created = User.objects.get_or_create(
            username=admin_username,
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.local"},
        )
        if created:
            admin.set_password(admin_password)
            admin.save()

        demo, created = User.objects.get_or_create(
            username="demo",
            defaults={"is_staff": False, "is_superuser": False, "email": "demo@example.local"},
        )
        if created:
            demo.set_password("demo12345")
            demo.save()

        # Demo user sees ONLY EIS.
        UserSourcePermission.objects.update_or_create(
            user=demo, source=eis, defaults={"can_view": True, "granted_by": admin}
        )
        return admin, demo

    def _seed_periodic_task(self):
        from django_celery_beat.models import CrontabSchedule, PeriodicTask

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=settings.TENDER_FETCH_CRON_MINUTE,
            hour=settings.TENDER_FETCH_CRON_HOUR,
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )
        PeriodicTask.objects.update_or_create(
            name="Collect all sources (hourly)",
            defaults={
                "crontab": schedule,
                "task": "tenders.collect_all_sources",
                "enabled": True,
            },
        )

    def _seed_tenders(self, eis: Source):
        result = collect_from_source(eis, limit=settings.TENDER_FETCH_PAGE_SIZE)
        if result.ok and result.fetched > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Live EIS fetch: {result.created} new, {result.updated} updated."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                "  Live EIS fetch returned nothing"
                + (f" ({result.error})" if result.error else "")
                + " — loading bundled sample tenders."
            )
        )
        with transaction.atomic():
            count = sum(1 for item in eis_sample_tenders() if upsert_tender(eis, item))
        self.stdout.write(self.style.SUCCESS(f"  Loaded {count} sample EIS tenders."))
