from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care.const import DOMAIN
from custom_components.plant_care.coordinator import PlantCareCoordinator


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    e = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care")
    e.add_to_hass(hass)
    return e


async def test_seed_and_snapshot(hass: HomeAssistant, entry: MockConfigEntry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed(
        "sub1", water_interval=5, feed_interval=14,
        next_water=date(2026, 6, 30), next_feed=date(2026, 7, 6),
    )
    snap = coord.snapshot("sub1", cfg_moisture_sensor=None, cfg_moisture_threshold=None)
    assert snap["water_interval"] == 5
    assert snap["next_water"] == date(2026, 6, 30)
    assert snap["days_to_water"] == 2
    assert snap["needs_water"] is False


async def test_mark_done_reschedules(hass, entry, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 5, 14, date(2026, 6, 28), date(2026, 7, 6))
    await coord.async_mark_done("sub1", "water")
    snap = coord.snapshot("sub1", None, None)
    assert snap["next_water"] == date(2026, 7, 3)  # today + 5
    assert snap["needs_water"] is False


async def test_snapshot_survives_corrupt_stored_date(hass, entry, freezer):
    # A corrupt/missing stored date must not break all of the plant's entities;
    # snapshot() should return a valid dict and read "due" (fall back to today).
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 5, 14, date(2026, 6, 30), date(2026, 7, 6))
    # Corrupt the stored next_water via the coordinator's internal store dict.
    coord._live["sub1"]["next_water"] = "not-a-date"

    snap = coord.snapshot("sub1", None, None)  # must not raise

    assert isinstance(snap, dict)
    assert snap["next_water"] == date(2026, 6, 28)  # fell back to today
    assert snap["needs_water"] is True  # today <= today -> due
    assert snap["next_feed"] == date(2026, 7, 6)  # other date untouched
