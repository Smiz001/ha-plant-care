"""Shared test helpers."""
from datetime import date

from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care_scheduler.const import (
    CONF_EMOJI, CONF_FEED_INTERVAL, CONF_MOISTURE_SENSOR, CONF_MOISTURE_THRESHOLD,
    CONF_NAME, CONF_NEXT_FEED, CONF_NEXT_WATER, CONF_SCHEMA_VERSION,
    CONF_TREATMENT_INTERVAL, CONF_TREATMENT_NAME, CONF_TREATMENT_UNTIL,
    CONF_WATER_INTERVAL, DOMAIN, SUBENTRY_TYPE,
)


async def setup_one_plant(
    hass: HomeAssistant,
    *,
    water_interval: int = 3,
    feed_interval: int = 7,
    next_water: str = "2026-06-30",
    next_feed: str = "2026-07-06",
    moisture_sensor: str | None = None,
    moisture_threshold: float | None = None,
    options: dict | None = None,
):
    """Set up the hub with exactly one plant subentry; return (entry, subentry_id)."""
    data = {
        CONF_NAME: "Жасмин",
        CONF_EMOJI: "🌼",
        CONF_WATER_INTERVAL: water_interval,
        CONF_FEED_INTERVAL: feed_interval,
        CONF_NEXT_WATER: next_water,
        CONF_NEXT_FEED: next_feed,
        CONF_MOISTURE_SENSOR: moisture_sensor,
        CONF_MOISTURE_THRESHOLD: moisture_threshold,
        CONF_SCHEMA_VERSION: 1,
    }
    sub = ConfigSubentryData(
        data=data, subentry_type=SUBENTRY_TYPE, title="Жасмин", unique_id=None
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care", subentries_data=[sub], options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sid = next(iter(entry.subentries))
    return entry, sid


async def setup_one_plant_with_treatment(
    hass: HomeAssistant,
    *,
    water_interval: int = 3,
    feed_interval: int = 7,
    next_water: str = "2026-06-30",
    next_feed: str = "2026-07-06",
):
    """Set up the hub with one plant that has a treatment configured; return (entry, subentry_id)."""
    data = {
        CONF_NAME: "Жасмин",
        CONF_EMOJI: "🌼",
        CONF_WATER_INTERVAL: water_interval,
        CONF_FEED_INTERVAL: feed_interval,
        CONF_NEXT_WATER: next_water,
        CONF_NEXT_FEED: next_feed,
        CONF_MOISTURE_SENSOR: None,
        CONF_MOISTURE_THRESHOLD: None,
        CONF_TREATMENT_NAME: "Фунгицид",
        CONF_TREATMENT_INTERVAL: 3,
        CONF_TREATMENT_UNTIL: None,
        CONF_SCHEMA_VERSION: 1,
    }
    sub = ConfigSubentryData(
        data=data, subentry_type=SUBENTRY_TYPE, title="Жасмин", unique_id=None
    )
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care", subentries_data=[sub], options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sid = next(iter(entry.subentries))
    await entry.runtime_data.async_set_treatment(sid, date(2026, 6, 28), 5)
    await hass.async_block_till_done()
    return entry, sid
