from datetime import date

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care.const import DEFAULT_WATER_INTERVAL, DOMAIN
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


@pytest.mark.parametrize("bad", ["nan", "inf"])
async def test_non_finite_moisture_falls_back_to_calendar(
    hass, entry, freezer, bad
):
    # A sensor that reports NaN/inf parses as a float but is not a usable
    # reading; it must be treated as "unknown" so an overdue plant still reads
    # "due" via the calendar instead of silently "not due".
    freezer.move_to("2026-06-28 08:00:00")
    hass.states.async_set("sensor.moist", bad)
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    # next_water in the past -> calendar says due
    coord.ensure_seed("sub1", 5, 14, date(2026, 6, 20), date(2026, 7, 6))

    snap = coord.snapshot(
        "sub1", cfg_moisture_sensor="sensor.moist", cfg_moisture_threshold=35
    )

    assert snap["moisture"] is None  # non-finite -> not a reading
    assert snap["needs_water"] is True  # calendar fallback (overdue)


async def test_snapshot_survives_partial_store_missing_interval(hass, entry, freezer):
    # A Store written by an older version (or partially corrupted) may be missing
    # an interval key; snapshot() must default it instead of raising KeyError and
    # breaking every entity for that plant.
    freezer.move_to("2026-06-28 08:00:00")
    coord = PlantCareCoordinator(hass, entry)
    await coord.async_load()
    coord.ensure_seed("sub1", 5, 14, date(2026, 6, 30), date(2026, 7, 6))
    del coord._live["sub1"]["water_interval"]

    snap = coord.snapshot("sub1", None, None)  # must not raise

    assert isinstance(snap, dict)
    assert snap["water_interval"] == DEFAULT_WATER_INTERVAL
    assert snap["feed_interval"] == 14  # still present, untouched
