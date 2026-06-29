"""Tests: feeding is optional per-plant (feeding_enabled toggle).

Mirrors the conditional-treatment pattern, but gated on a boolean
(default True) instead of a non-empty name. Watering stays always-on.
"""
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care_scheduler.const import (
    CONF_EMOJI, CONF_FEED_INTERVAL, CONF_FEEDING_ENABLED, CONF_MOISTURE_SENSOR,
    CONF_MOISTURE_THRESHOLD, CONF_NAME, CONF_NEXT_FEED, CONF_NEXT_WATER,
    CONF_SCHEMA_VERSION, CONF_WATER_INTERVAL, DOMAIN, SUBENTRY_TYPE,
)
from tests.helpers import setup_one_plant


async def test_no_feed_entities_when_disabled(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass, feeding_enabled=False)
    reg = er.async_get(hass)
    for platform, suffix in (("number", "feed_interval"), ("date", "next_feed"),
                             ("sensor", "days_to_feed"), ("binary_sensor", "needs_feed"),
                             ("button", "fed")):
        assert reg.async_get_entity_id(platform, "plant_care_scheduler", f"{sid}_{suffix}") is None, f"unexpected {suffix}"
    # watering still present
    assert reg.async_get_entity_id("number", "plant_care_scheduler", f"{sid}_water_interval") is not None
    assert reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_water") is not None


async def test_feed_entities_present_by_default(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)  # no key -> default enabled
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_feed") is not None
    assert reg.async_get_entity_id("button", "plant_care_scheduler", f"{sid}_fed") is not None


async def test_disable_then_reenable_feeding_restores_same_entity_id(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)  # feeding on by default
    reg = er.async_get(hass)
    before = reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_feed")
    assert before is not None

    # disable feeding
    r1 = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "plant"), context={"source": "reconfigure", "subentry_id": sid})
    await hass.config_entries.subentries.async_configure(
        r1["flow_id"], {"name": "Жасмин", "emoji": "🌼", "feeding_enabled": False})
    await hass.async_block_till_done()
    assert reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_feed") is None

    # re-enable feeding
    r2 = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "plant"), context={"source": "reconfigure", "subentry_id": sid})
    await hass.config_entries.subentries.async_configure(
        r2["flow_id"], {"name": "Жасмин", "emoji": "🌼", "feeding_enabled": True})
    await hass.async_block_till_done()
    after = reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_feed")
    assert after == before  # same entity_id restored


async def test_cross_plant_feeding_disable_isolation(hass: HomeAssistant):
    """Disabling plant A's feeding must leave plant B's feed entities intact."""
    def _plant_data(name: str, emoji: str) -> dict:
        return {
            CONF_NAME: name,
            CONF_EMOJI: emoji,
            CONF_WATER_INTERVAL: 3,
            CONF_FEED_INTERVAL: 7,
            CONF_NEXT_WATER: "2026-06-30",
            CONF_NEXT_FEED: "2026-07-06",
            CONF_MOISTURE_SENSOR: None,
            CONF_MOISTURE_THRESHOLD: None,
            CONF_SCHEMA_VERSION: 1,
        }

    sub_a = ConfigSubentryData(data=_plant_data("Жасмин", "🌼"), subentry_type=SUBENTRY_TYPE, title="Жасмин", unique_id=None)
    sub_b = ConfigSubentryData(data=_plant_data("Фикус", "🌿"), subentry_type=SUBENTRY_TYPE, title="Фикус", unique_id=None)
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care", subentries_data=[sub_a, sub_b], options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    sids = list(entry.subentries)
    sid_a, sid_b = sids[0], sids[1]

    reg = er.async_get(hass)
    # both plants have feed entities before we touch anything
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{sid_a}_needs_feed") is not None
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{sid_b}_needs_feed") is not None

    # disable feeding on plant A only
    r = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "plant"), context={"source": "reconfigure", "subentry_id": sid_a})
    await hass.config_entries.subentries.async_configure(
        r["flow_id"], {"name": "Жасмин", "emoji": "🌼", "feeding_enabled": False})
    await hass.async_block_till_done()

    # plant A's feed entities gone
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{sid_a}_needs_feed") is None
    # plant B's feed entities survive
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{sid_b}_needs_feed") is not None
    assert reg.async_get_entity_id("button", DOMAIN, f"{sid_b}_fed") is not None


async def test_calendar_skips_feed_event_when_disabled(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant(hass, feeding_enabled=False, next_water="2026-06-30", next_feed="2026-07-06")
    events = await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": "calendar.plant_care_scheduler", "start_date_time": "2026-06-27 00:00:00", "end_date_time": "2026-07-10 00:00:00"},
        blocking=True, return_response=True)
    summaries = [e["summary"] for e in events["calendar.plant_care_scheduler"]["events"]]
    assert any("Полив" in s for s in summaries)        # watering event present
    assert not any("Подкормка" in s for s in summaries) # feeding event absent
