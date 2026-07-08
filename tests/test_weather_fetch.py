from homeassistant.core import HomeAssistant, SupportsResponse
from tests.helpers import setup_one_plant


async def test_refresh_weather_caches_today(hass: HomeAssistant):
    hass.states.async_set("weather.home", "rainy", {})

    async def _fc(call):
        return {"weather.home": {"forecast": [{"precipitation": 4.0, "temperature": 31.0}]}}

    hass.services.async_register("weather", "get_forecasts", _fc, supports_response=SupportsResponse.ONLY)
    entry, sid = await setup_one_plant(hass)
    coord = entry.runtime_data
    await coord.async_refresh_weather("weather.home")
    assert coord._weather == {"condition": "rainy", "precip_today": 4.0, "temp_high": 31.0}


async def test_refresh_weather_missing_entity_is_none(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    coord = entry.runtime_data
    await coord.async_refresh_weather("weather.nope")
    assert coord._weather is None


async def test_refresh_weather_empty_entity_is_none(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    coord = entry.runtime_data
    await coord.async_refresh_weather("")
    assert coord._weather is None
