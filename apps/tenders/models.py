from django.db import models


class FZType(models.TextChoices):
    FZ44 = "44", "44-ФЗ"
    FZ223 = "223", "223-ФЗ"
    OTHER = "", "Прочее / н.д."


class Tender(models.Model):
    """A single procurement notice collected from a Source.

    Deduplication key is ``(source, external_id)``: re-collecting the same
    notice updates the existing row instead of inserting a duplicate.
    """

    source = models.ForeignKey(
        "sources.Source",
        on_delete=models.CASCADE,
        related_name="tenders",
    )
    external_id = models.CharField(
        max_length=255,
        help_text="Stable id of the tender within its source (e.g. EIS regNumber).",
    )
    number = models.CharField(max_length=100, blank=True)
    title = models.TextField()
    customer = models.CharField(max_length=500, blank=True)
    price = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Initial (maximum) contract price (NMC), if known.",
    )
    region = models.CharField(max_length=255, blank=True)
    fz_type = models.CharField(
        max_length=8, choices=FZType.choices, blank=True, default=FZType.OTHER
    )
    url = models.URLField(max_length=1000, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    deadline_at = models.DateTimeField(null=True, blank=True)

    raw = models.JSONField(default=dict, blank=True)

    first_seen_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-first_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="uniq_tender_per_source",
            )
        ]
        indexes = [
            models.Index(fields=["region"]),
            models.Index(fields=["fz_type"]),
            models.Index(fields=["-published_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.source.code}] {self.number or self.external_id}"


def tender_document_path(instance, filename: str) -> str:
    return f"tender_docs/{instance.tender_id}/{filename}"


class TenderDocument(models.Model):
    """A document/attachment (e.g. ТЗ) associated with a tender.

    ``url`` is the source link; ``file`` holds the copy we downloaded into our
    own storage so the documentation survives even if the source removes it.
    """

    tender = models.ForeignKey(
        Tender,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=500, blank=True)
    url = models.URLField(max_length=1000)

    # Locally stored copy of the document.
    file = models.FileField(upload_to=tender_document_path, blank=True, null=True)
    is_downloaded = models.BooleanField(default=False)
    content_type = models.CharField(max_length=200, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    download_error = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tender", "url"],
                name="uniq_document_per_tender",
            )
        ]

    def __str__(self) -> str:
        return self.title or self.url
