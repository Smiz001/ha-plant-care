"""Built-in actionable reminders (opt-in)."""
from __future__ import annotations

import logging

from .const import (
    CONF_NOTIFY_CHANNEL, CONF_TELEGRAM_CONFIG_ENTRY, CONF_TELEGRAM_CHAT_ID,
    CONF_MOBILE_APP_SERVICE, CHANNEL_TELEGRAM, CHANNEL_MOBILE_APP, ACTIONS,
)
from .models import PlantConfig

_LOGGER = logging.getLogger(__name__)

_PRES = {
    "water":     ("💧", "полить",    "✅ Полил"),
    "feed":      ("🧪", "подкормить", "✅ Подкормил"),
    "treatment": ("🩹", "обработать", "✅ Обработал"),
}
_NEEDS_KEY = {"water": "needs_water", "feed": "needs_feed", "treatment": "needs_treatment"}


def encode_action(subentry_id: str, action: str) -> str:
    """Encode a callback payload (Telegram callback_data / mobile_app action id)."""
    return f"pcs::{subentry_id}::{action}"


def decode_action(payload: str | None) -> tuple[str, str] | None:
    """Parse a callback payload back to (subentry_id, action); None if invalid."""
    if not payload:
        return None
    parts = payload.split("::")
    if len(parts) == 3 and parts[0] == "pcs" and parts[2] in ACTIONS:
        return parts[1], parts[2]
    return None


async def async_send_due_reminders(hass, entry, coordinator, opts) -> None:
    for sub in entry.subentries.values():
        cfg = PlantConfig.from_data(dict(sub.data))
        snap = coordinator.snapshot(
            sub.subentry_id, cfg.moisture_sensor, cfg.moisture_threshold,
            cfg.treatment_name, cfg.treatment_interval, cfg.treatment_until,
        )
        for action in ACTIONS:
            if action == "feed" and not cfg.feeding_enabled:
                continue
            if action == "treatment" and not snap.get("treatment_active"):
                continue
            if not snap.get(_NEEDS_KEY[action]):
                continue
            emoji, verb, caption = _PRES[action]
            text = f"{emoji} Пора *{verb}* {cfg.emoji} {cfg.name}"
            payload = encode_action(sub.subentry_id, action)
            try:
                await _dispatch(hass, opts, text, caption, payload)
            except Exception:  # one plant's failure must not stop the rest
                _LOGGER.warning("plant_care: reminder dispatch failed for %s/%s", sub.subentry_id, action, exc_info=True)


async def _dispatch(hass, opts, text, caption, payload) -> None:
    channel = opts.get(CONF_NOTIFY_CHANNEL)
    if channel == CHANNEL_TELEGRAM:
        cfg_entry = opts.get(CONF_TELEGRAM_CONFIG_ENTRY)
        chat_id = opts.get(CONF_TELEGRAM_CHAT_ID)
        if not cfg_entry or not chat_id:
            _LOGGER.warning("plant_care: telegram channel selected but config_entry_id/chat_id missing")
            return
        if not hass.services.has_service("telegram_bot", "send_message"):
            _LOGGER.warning("plant_care: telegram_bot.send_message unavailable")
            return
        await hass.services.async_call("telegram_bot", "send_message", {
            "config_entry_id": cfg_entry, "chat_id": chat_id, "parse_mode": "markdown",
            "message": text, "inline_keyboard": [[f"{caption}:{payload}"]],
        }, blocking=True)
    elif channel == CHANNEL_MOBILE_APP:
        svc = opts.get(CONF_MOBILE_APP_SERVICE) or ""
        domain, _, service = svc.partition(".")
        if not domain or not service:
            _LOGGER.warning("plant_care: mobile_app channel selected but service missing/invalid: %r", svc)
            return
        if not hass.services.has_service(domain, service):
            _LOGGER.warning("plant_care: %s unavailable", svc)
            return
        await hass.services.async_call(domain, service, {
            "message": text, "data": {"actions": [{"action": payload, "title": caption}]},
        }, blocking=True)
    else:
        _LOGGER.warning("plant_care: unknown notify channel %r", channel)
