from django.db import models


class TelegramProfile(models.Model):
    """Links a user to a Telegram chat for new-tender notifications.

    Skeleton only: storing the chat id and an on/off switch is enough for the
    notification service to target a user. Subscription/matching rules can be
    layered on later (e.g. per-region or per-keyword filters).
    """

    user = models.OneToOneField(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="telegram_profile",
    )
    chat_id = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Telegram<{self.user}:{self.chat_id or 'unset'}>"
