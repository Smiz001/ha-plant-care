"""Tests for button platform: mark watered / mark fed."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_watered_button_reschedules(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant(hass)  # water_interval 3
    reg = er.async_get(hass)
    btn = reg.async_get_entity_id("button", "plant_care_scheduler", f"{sid}_watered")
    date_ent = reg.async_get_entity_id("date", "plant_care_scheduler", f"{sid}_next_water")
    assert btn is not None and date_ent is not None

    await hass.services.async_call("button", "press", {"entity_id": btn}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get(date_ent).state == "2026-07-01"  # today + 3
