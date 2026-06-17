"""Telegram notification skeleton.

Disabled by default (``TELEGRAM_ENABLED=0``). When enabled and a bot token is
set, :func:`notify_new_tender` sends a message to a user's linked chat. The
sending primitive is real (Telegram Bot API); the *matching* logic (who gets
notified about which tender) is intentionally minimal and ready to extend.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger("apps.notifications")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def is_enabled() -> bool:
    return bool(settings.TELEGRAM_ENABLED and settings.TELEGRAM_BOT_TOKEN)


def send_message(chat_id: str, text: str) -> bool:
    """Low-level send. Returns True on success, never raises."""
    if not is_enabled():
        logger.debug("Telegram disabled; skipping message to %s", chat_id)
        return False
    if not chat_id:
        return False
    url = TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN)
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("Telegram send failed for chat %s: %s", chat_id, exc)
        return False


def notify_new_tender(user, tender) -> bool:
    """Notify a single user about a new tender, if they have an active chat."""
    profile = getattr(user, "telegram_profile", None)
    if not profile or not profile.is_active or not profile.chat_id:
        return False
    text = (
        f"🆕 <b>Yangi tender</b>\n"
        f"{tender.title}\n"
        f"Manba: {tender.source.name}\n"
        f"Narx: {tender.price or '—'}\n"
        f"{tender.url}"
    )
    return send_message(profile.chat_id, text)
