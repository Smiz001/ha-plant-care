from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care_scheduler.const import DOMAIN
from custom_components.plant_care_scheduler.coordinator import PlantCareCoordinator


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    e = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care")
    e.add_to_hass(hass)
    return e


async def test_heat_shifts_due_earlier(hass, entry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 10, 14, date(2026, 7, 8), date(2026, 7, 12))  # next_water in 10 days
    coord._weather = {"condition": "sunny", "precip_today": 0.0, "temp_high": 35.0}
    snap = coord.snapshot("sub1", None, None, weather_enabled=True)
    assert snap["days_to_water"] == 7          # 10 - heat_shift(10,35)=3
    assert snap["needs_water"] is False


async def test_cool_shifts_due_later(hass, entry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 10, 14, date(2026, 7, 8), date(2026, 7, 12))
    coord._weather = {"condition": "cloudy", "precip_today": 0.0, "temp_high": 15.0}
    assert coord.snapshot("sub1", None, None, weather_enabled=True)["days_to_water"] == 12   # 10 - (-2)


async def test_rain_skips_due_plant(hass, entry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 5, 14, date(2026, 6, 28), date(2026, 7, 6))  # due today
    coord._weather = {"condition": "rainy", "precip_today": 0.0, "temp_high": 20.0}
    assert coord.snapshot("sub1", None, None, rain_skip=True)["needs_water"] is False
    assert coord.snapshot("sub1", None, None, rain_skip=False)["needs_water"] is True


async def test_moisture_beats_weather(hass, entry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    hass.states.async_set("sensor.m", "10")   # dry -> below threshold -> needs water
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 5, 14, date(2026, 7, 10), date(2026, 7, 12))
    coord._weather = {"condition": "rainy", "precip_today": 9.0, "temp_high": 20.0}
    snap = coord.snapshot("sub1", "sensor.m", 35, rain_skip=True, weather_enabled=True)
    assert snap["needs_water"] is True         # moisture(10)<35 wins; rain ignored


async def test_no_weather_cache_is_plain_calendar(hass, entry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 5, 14, date(2026, 7, 3), date(2026, 7, 6))
    coord._weather = None
    snap = coord.snapshot("sub1", None, None, weather_enabled=True, rain_skip=True)
    assert snap["days_to_water"] == 5 and snap["needs_water"] is False   # unchanged
