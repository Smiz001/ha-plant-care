"""The hub refreshes weather at setup, hourly, and before the daily reminder."""
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.plant_care_scheduler.const import (
    CONF_WEATHER_ENTITY, CONF_NOTIFICATIONS_ENABLED, CONF_NOTIFY_CHANNEL, CHANNEL_TELEGRAM,
    CONF_TELEGRAM_CONFIG_ENTRY, CONF_TELEGRAM_CHAT_ID, CONF_REMINDER_TIME,
)
from tests.helpers import setup_one_plant


async def test_weather_refreshed_at_setup(hass: HomeAssistant):
    hass.states.async_set("weather.home", "sunny", {})

    async def _fc(call):
        return {"weather.home": {"forecast": [{"precipitation": 0.0, "temperature": 28.0}]}}

    hass.services.async_register("weather", "get_forecasts", _fc, supports_response=SupportsResponse.ONLY)
    entry, sid = await setup_one_plant(hass, options={CONF_WEATHER_ENTITY: "weather.home"})
    assert entry.runtime_data._weather == {"condition": "sunny", "precip_today": 0.0, "temp_high": 28.0}


async def test_daily_reminder_refreshes_weather(hass: HomeAssistant, freezer):
    await hass.config.async_set_time_zone("UTC")
    freezer.move_to("2026-06-28 08:29:50")
    hass.states.async_set("weather.home", "rainy", {})

    async def _fc(call):
        return {"weather.home": {"forecast": [{"precipitation": 6.0, "temperature": 19.0}]}}

    hass.services.async_register("weather", "get_forecasts", _fc, supports_response=SupportsResponse.ONLY)
    hass.services.async_register("telegram_bot", "send_message", lambda c: None)
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28", options={
        CONF_WEATHER_ENTITY: "weather.home",
        CONF_NOTIFICATIONS_ENABLED: True, CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM,
        CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42",
        CONF_REMINDER_TIME: "08:30:00",
    })
    entry.runtime_data._weather = None  # clear, prove the daily callback refreshes it
    freezer.move_to("2026-06-28 08:30:01")
    async_fire_time_changed(hass, dt_util.now())
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.runtime_data._weather == {"condition": "rainy", "precip_today": 6.0, "temp_high": 19.0}
