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
