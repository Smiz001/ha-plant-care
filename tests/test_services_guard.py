"""Invalid service writes are rejected and never corrupt the live Store."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_out_of_range_interval_rejected(hass: HomeAssistant):
    # number bounds are 1..365; 0 and 999 must be rejected and the stored
    # interval must remain unchanged (no partial/corrupt write).
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("number", "plant_care", f"{sid}_water_interval")

    for bad in (0, 999):
        with pytest.raises(Exception):
            await hass.services.async_call(
                "number", "set_value", {"entity_id": ent, "value": bad}, blocking=True
            )
        assert entry.runtime_data._live[sid]["water_interval"] == 3


async def test_invalid_date_rejected(hass: HomeAssistant):
    # A non-date value must raise and leave next_water untouched.
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("date", "plant_care", f"{sid}_next_water")

    with pytest.raises(Exception):
        await hass.services.async_call(
            "date", "set_value", {"entity_id": ent, "date": "not-a-date"},
            blocking=True,
        )
    assert entry.runtime_data._live[sid]["next_water"] == "2026-06-30"
