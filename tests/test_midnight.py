"""Date-derived sensors must refresh at the day rollover."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from tests.helpers import setup_one_plant


async def test_days_to_water_refreshes_at_midnight(hass: HomeAssistant, freezer):
    # Pin the timezone to UTC so the freezer's UTC strings line up with the
    # local-midnight refresh the integration schedules.
    await hass.config.async_set_time_zone("UTC")

    freezer.move_to("2026-06-28 08:00:00")  # day D
    entry, sid = await setup_one_plant(hass, next_water="2026-06-30")
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("sensor", "plant_care", f"{sid}_days_to_water")
    assert ent is not None
    assert hass.states.get(ent).state == "2"  # 2026-06-30 - 2026-06-28

    # Roll over to the next day; the registered midnight refresh should fire.
    freezer.move_to("2026-06-29 00:00:11")
    async_fire_time_changed(hass, dt_util.now())
    await hass.async_block_till_done()

    assert hass.states.get(ent).state == "1"  # decreased by 1
