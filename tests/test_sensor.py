from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_days_to_water(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("sensor", "plant_care", f"{sid}_days_to_water")
    assert ent is not None
    assert hass.states.get(ent).state == "2"  # 2026-06-30 - 2026-06-28
