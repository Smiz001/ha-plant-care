"""Hub options flow: the weather entity is optional (empty must not block save)."""
from homeassistant.core import HomeAssistant

from tests.helpers import setup_one_plant
from custom_components.plant_care_scheduler.const import (
    CONF_REMINDER_TIME,
    CONF_SNOOZE_DAYS,
    CONF_WEATHER_ENTITY,
)


async def test_options_saved_without_weather_entity(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    # submit WITHOUT choosing a weather entity — must succeed, weather stays off
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_REMINDER_TIME: "08:30:00"})
    assert result["type"] == "create_entry"
    assert not entry.options.get(CONF_WEATHER_ENTITY)


async def test_options_saved_with_weather_entity(hass: HomeAssistant):
    hass.states.async_set("weather.home", "sunny", {})
    entry, sid = await setup_one_plant(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_REMINDER_TIME: "08:30:00", CONF_WEATHER_ENTITY: "weather.home"})
    assert result["type"] == "create_entry"
    assert entry.options.get(CONF_WEATHER_ENTITY) == "weather.home"


async def test_options_snooze_days_saved(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_REMINDER_TIME: "08:30:00", CONF_SNOOZE_DAYS: 3})
    assert result["type"] == "create_entry"
    assert entry.options.get(CONF_SNOOZE_DAYS) == 3
