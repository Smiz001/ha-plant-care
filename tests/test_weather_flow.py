"""Tests: weather-aware watering config exposed in the plant reconfigure flow."""
from homeassistant.core import HomeAssistant

from custom_components.plant_care_scheduler.models import PlantConfig
from tests.helpers import setup_one_plant


async def test_reconfigure_enables_weather(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "plant"), context={"source": "reconfigure", "subentry_id": sid})
    await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Жасмин", "emoji": "🌼", "weather_enabled": True, "rain_skip": True})
    await hass.async_block_till_done()
    sub = entry.subentries[sid]
    cfg = PlantConfig.from_data(dict(sub.data))
    assert cfg.weather_enabled is True and cfg.rain_skip is True
