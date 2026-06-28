"""Tests: conditional treatment entities (binary_sensor / sensor / button)."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant, setup_one_plant_with_treatment


async def test_treatment_entities_present_and_button(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant_with_treatment(hass)
    reg = er.async_get(hass)
    needs = reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_treatment")
    btn = reg.async_get_entity_id("button", "plant_care_scheduler", f"{sid}_mark_treated")
    left = reg.async_get_entity_id("sensor", "plant_care_scheduler", f"{sid}_treatments_left")
    assert needs and btn and left
    assert hass.states.get(needs).state == "on"
    assert hass.states.get(left).state == "5"
    await hass.services.async_call("button", "press", {"entity_id": btn}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(left).state == "4"
    assert hass.states.get(needs).state == "off"


async def test_no_treatment_entities_without_treatment(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("binary_sensor", "plant_care_scheduler", f"{sid}_needs_treatment") is None
    assert reg.async_get_entity_id("button", "plant_care_scheduler", f"{sid}_mark_treated") is None
