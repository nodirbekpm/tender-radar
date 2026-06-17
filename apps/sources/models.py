from django.db import models


class Source(models.Model):
    """A procurement marketplace we can collect tenders from.

    Each Source maps to one adapter class (see ``apps.sources.adapters``)
    via ``adapter_key``. Sources can be globally enabled/disabled by an admin;
    a disabled source is never polled and never shown to anyone.
    """

    code = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Stable machine identifier, e.g. 'eis', 'sberbank_ast'.",
    )
    name = models.CharField(max_length=200)
    adapter_key = models.CharField(
        max_length=50,
        help_text="Key under which the adapter is registered. Defaults to `code`.",
        blank=True,
    )
    website_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    is_enabled = models.BooleanField(
        default=True,
        help_text="If off, this source is never polled and never displayed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def resolved_adapter_key(self) -> str:
        return self.adapter_key or self.code


class UserSourcePermission(models.Model):
    """Grants a single user visibility into a single source.

    The presence of a row (with ``can_view=True``) means the user may see that
    source's tenders. Admins toggle these per-user — e.g. a demo user starts
    with only EIS, and an admin can later grant 'B2B-Center'.
    """

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="source_permissions",
    )
    source = models.ForeignKey(
        Source,
        on_delete=models.CASCADE,
        related_name="user_permissions",
    )
    can_view = models.BooleanField(default=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_source_permissions",
    )

    class Meta:
        unique_together = ("user", "source")
        ordering = ["source__name"]

    def __str__(self) -> str:
        state = "can view" if self.can_view else "blocked"
        return f"{self.user} → {self.source} ({state})"
