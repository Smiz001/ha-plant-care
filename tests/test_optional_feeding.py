"""Tests: feeding is optional per-plant (feeding_enabled toggle).

Mirrors the conditional-treatment pattern, but gated on a boolean
(default True) instead of a non-empty name. Watering stays always-on.
"""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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
