"""Built-in reminders must honor the per-plant weather flags (rain_skip)."""
from homeassistant.core import HomeAssistant

from custom_components.plant_care_scheduler.notifications import async_send_due_reminders
from custom_components.plant_care_scheduler.const import (
    CONF_NOTIFY_CHANNEL, CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY,
    CONF_TELEGRAM_CHAT_ID, CONF_RAIN_SKIP,
)
from tests.helpers import setup_one_plant


async def test_rain_skip_suppresses_reminder(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")  # due today
    # enable rain_skip on the plant (updating the subentry reloads the hub)
    sub = entry.subentries[sid]
    hass.config_entries.async_update_subentry(
        entry, sub, data={**sub.data, CONF_RAIN_SKIP: True})
    await hass.async_block_till_done()
    coord = entry.runtime_data
    coord._weather = {"condition": "rainy", "precip_today": 8.0, "temp_high": 18.0}
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    opts = {CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42"}
    await async_send_due_reminders(hass, entry, coord, opts)
    assert calls == []   # rain -> no watering reminder
