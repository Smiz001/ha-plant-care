from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_needs_water_calendar(hass: HomeAssistant, freezer):
    freezer.move_to("2026-07-01 08:00:00")  # past 2026-06-30 -> due
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("binary_sensor", "plant_care", f"{sid}_needs_water")
    assert ent is not None
    assert hass.states.get(ent).state == "on"


async def test_needs_water_moisture(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")  # calendar NOT due (next 06-30)
    hass.states.async_set("sensor.test_moisture", "20")
    entry, sid = await setup_one_plant(
        hass, moisture_sensor="sensor.test_moisture", moisture_threshold=35
    )
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("binary_sensor", "plant_care", f"{sid}_needs_water")
    assert ent is not None
    # moisture 20 < threshold 35 -> due even though calendar isn't
    assert hass.states.get(ent).state == "on"


async def test_needs_water_moisture_unavailable_falls_back_to_calendar(
    hass: HomeAssistant, freezer
):
    # Moisture sensor + threshold configured, but the sensor is unavailable
    # (never set / unknown). An overdue plant must still read "due" via the
    # calendar fallback rather than silently reporting "not due".
    freezer.move_to("2026-07-01 08:00:00")  # past next_water 06-30 -> calendar due
    entry, sid = await setup_one_plant(
        hass,
        moisture_sensor="sensor.test_moisture",  # state never set -> unavailable
        moisture_threshold=35,
        next_water="2026-06-30",
    )
    reg = er.async_get(hass)
    ent = reg.async_get_entity_id("binary_sensor", "plant_care", f"{sid}_needs_water")
    assert ent is not None
    assert hass.states.get(ent).state == "on"
