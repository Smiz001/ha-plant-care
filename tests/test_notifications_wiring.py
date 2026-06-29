"""The hub wires the opt-in actionable reminder (daily trigger), gated on the flag."""
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.plant_care_scheduler.const import (
    CONF_NOTIFICATIONS_ENABLED, CONF_NOTIFY_CHANNEL, CHANNEL_TELEGRAM,
    CONF_TELEGRAM_CONFIG_ENTRY, CONF_TELEGRAM_CHAT_ID, CONF_REMINDER_TIME,
)
from tests.helpers import setup_one_plant


async def test_daily_trigger_sends_when_enabled(hass: HomeAssistant, freezer):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-06-28 08:29:50")
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28", options={
        CONF_NOTIFICATIONS_ENABLED: True, CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM,
        CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42",
        CONF_REMINDER_TIME: "08:30:00",
    })
    freezer.move_to("2026-06-28 08:30:01")
    async_fire_time_changed(hass, dt_util.now())
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_no_trigger_when_disabled(hass: HomeAssistant, freezer):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-06-28 08:29:50")
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28", options={
        CONF_REMINDER_TIME: "08:30:00",  # notifications NOT enabled
    })
    freezer.move_to("2026-06-28 08:30:01")
    async_fire_time_changed(hass, dt_util.now())
    await hass.async_block_till_done()
    assert calls == []
