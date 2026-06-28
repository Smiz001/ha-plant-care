from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_interval_numbers(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("number", "plant_care", f"{sid}_water_interval")
    assert ent is not None
    assert hass.states.get(ent).state == "3"

    await hass.services.async_call(
        "number", "set_value", {"entity_id": ent, "value": 4}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(ent).state == "4"
