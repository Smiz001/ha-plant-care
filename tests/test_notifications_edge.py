"""Edge-case guards for built-in notifications (resilience locked in)."""
from homeassistant.core import HomeAssistant

from custom_components.plant_care_scheduler.notifications import (
    async_handle_action,
    async_send_due_reminders,
)
from custom_components.plant_care_scheduler.const import (
    CHANNEL_MOBILE_APP,
    CHANNEL_TELEGRAM,
    CONF_MOBILE_APP_SERVICE,
    CONF_NOTIFY_CHANNEL,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_CONFIG_ENTRY,
)
from tests.helpers import setup_one_plant


async def test_telegram_missing_fields_no_send_no_raise(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    # channel telegram but no config_entry/chat_id
    await async_send_due_reminders(hass, entry, entry.runtime_data, {CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM})
    assert calls == []


async def test_mobile_app_missing_service_no_raise(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    # mobile_app channel, service not registered -> must not raise
    await async_send_due_reminders(hass, entry, entry.runtime_data,
                                   {CONF_NOTIFY_CHANNEL: CHANNEL_MOBILE_APP, CONF_MOBILE_APP_SERVICE: "notify.nope"})


async def test_handle_action_garbage_no_raise(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    await async_handle_action(hass, entry.runtime_data, "totally::bad")  # no raise
