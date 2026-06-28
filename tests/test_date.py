from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_next_water_date(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("date", "plant_care_scheduler", f"{sid}_next_water")
    assert ent is not None
    assert hass.states.get(ent).state == "2026-06-30"

    await hass.services.async_call(
        "date", "set_value", {"entity_id": ent, "date": "2026-07-02"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(ent).state == "2026-07-02"
