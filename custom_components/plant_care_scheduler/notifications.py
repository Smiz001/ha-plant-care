"""Built-in actionable reminders (opt-in)."""
from __future__ import annotations

import logging

from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_NOTIFICATIONS_ENABLED, CONF_NOTIFY_CHANNEL, CONF_REMINDER_TIME,
    CONF_TELEGRAM_CONFIG_ENTRY, CONF_TELEGRAM_CHAT_ID, CONF_MOBILE_APP_SERVICE,
    CONF_WEATHER_ENTITY, CHANNEL_TELEGRAM, CHANNEL_MOBILE_APP, DEFAULT_REMINDER_TIME, ACTIONS,
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


async def async_setup_notifications(hass, entry, coordinator) -> None:
    """Register the daily reminder trigger + tap listeners when enabled (opt-in)."""
    if not entry.options.get(CONF_NOTIFICATIONS_ENABLED):
        return
    rt = dt_util.parse_time(entry.options.get(CONF_REMINDER_TIME, DEFAULT_REMINDER_TIME)) \
        or dt_util.parse_time(DEFAULT_REMINDER_TIME)

    async def _daily(now):
        coordinator.async_update_listeners()  # keep dashboard in sync with the reminder
        # Refresh weather right before deciding what's due, so a rain-skip/heat-adjust
        # reflects current conditions even if the hourly refresh hasn't landed yet.
        await coordinator.async_refresh_weather(entry.options.get(CONF_WEATHER_ENTITY))
        await async_send_due_reminders(hass, entry, coordinator, dict(entry.options))

    entry.async_on_unload(
        async_track_time_change(hass, _daily, hour=rt.hour, minute=rt.minute, second=0)
    )
    for unsub in register_callbacks(hass, entry, coordinator, dict(entry.options)):
        entry.async_on_unload(unsub)


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
            "message": text, "inline_keyboard": [[[caption, payload]]],
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


async def async_handle_action(hass, coordinator, payload) -> None:
    """Apply a reminder tap: parse the payload and mark the plant done/treated.

    A stale or malformed tap must never raise — the user pressed a button on an
    old notification and there's nothing to surface back to them.
    """
    decoded = decode_action(payload)
    if decoded is None:
        return
    sid, action = decoded
    # Guard unknown subentry: a tap on a notification for a since-removed plant.
    if sid not in coordinator.config_entry.subentries:
        return
    try:
        if action in ("water", "feed"):
            await coordinator.async_mark_done(sid, action)
        elif action == "treatment":
            sub = coordinator.config_entry.subentries[sid]
            cfg = PlantConfig.from_data(dict(sub.data))
            await coordinator.async_mark_treated(sid, cfg.treatment_interval)
    except Exception:  # a stale tap (e.g. plant un-seeded) must not raise
        _LOGGER.warning(
            "plant_care: failed to apply reminder action %s for %s",
            action, sid, exc_info=True,
        )


async def _tg_handle(hass, coordinator, opts, ns, data) -> None:
    """Handle a Telegram callback: mark the plant, then ack + edit the message.

    Both the answer_callback_query and edit_message calls are best-effort; a
    failure there must not undo the mark or raise.
    """
    await async_handle_action(hass, coordinator, data)
    cfg_entry = opts.get(CONF_TELEGRAM_CONFIG_ENTRY)
    if not cfg_entry:
        return
    try:
        if hass.services.has_service("telegram_bot", "answer_callback_query"):
            await hass.services.async_call("telegram_bot", "answer_callback_query", {
                "callback_query_id": ns.attributes.get("id"),
                "config_entry_id": cfg_entry,
                "message": "✅",
            }, blocking=False)
    except Exception:
        _LOGGER.debug("plant_care: telegram answer_callback_query failed", exc_info=True)
    try:
        message = ns.attributes.get("message") or {}
        message_id = message.get("message_id")
        chat_id = ns.attributes.get("chat_id")
        if (
            message_id is not None
            and chat_id is not None
            and hass.services.has_service("telegram_bot", "edit_message")
        ):
            # Keep the original reminder text and append a ✅ + date (like the
            # legacy YAML), instead of replacing the whole message.
            orig = message.get("text") or ""
            stamp = dt_util.now().strftime("%d.%m")
            edited = f"{orig} — ✅ {stamp}" if orig else f"✅ {stamp}"
            await hass.services.async_call("telegram_bot", "edit_message", {
                "config_entry_id": cfg_entry,
                "message_id": message_id,
                "chat_id": chat_id,
                "message": edited,
            }, blocking=False)
    except Exception:
        _LOGGER.debug("plant_care: telegram edit_message failed", exc_info=True)


def register_callbacks(hass, entry, coordinator, opts) -> list:
    """Subscribe to reminder taps; return unsub callables (caller stores them)."""
    unsubs: list = []

    # mobile_app actionable notifications fire this bus event on tap.
    @callback
    def _mobile_app(event):
        hass.async_create_task(
            async_handle_action(hass, coordinator, event.data.get("action"))
        )

    unsubs.append(hass.bus.async_listen("mobile_app_notification_action", _mobile_app))

    tg_entry = opts.get(CONF_TELEGRAM_CONFIG_ENTRY)
    if tg_entry:
        try:
            reg = er.async_get(hass)
            event_ids = [
                e.entity_id
                for e in er.async_entries_for_config_entry(reg, tg_entry)
                if e.domain == "event"
            ]
        except Exception:
            event_ids = []
        if event_ids:
            @callback
            def _tg(event):
                ns = event.data.get("new_state")
                if not ns:
                    return
                if ns.attributes.get("event_type") != "telegram_callback":
                    return
                data = str(ns.attributes.get("data") or "")
                if not data.startswith("pcs::"):
                    return
                hass.async_create_task(_tg_handle(hass, coordinator, opts, ns, data))

            unsubs.append(async_track_state_change_event(hass, event_ids, _tg))

        # Fallback for polling/legacy bots that DO fire the bus event.
        @callback
        def _tg_bus(event):
            data = str(event.data.get("data") or "")
            if not data.startswith("pcs::"):
                return
            hass.async_create_task(async_handle_action(hass, coordinator, data))

        unsubs.append(hass.bus.async_listen("telegram_callback", _tg_bus))

    return unsubs
