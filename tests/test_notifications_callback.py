from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from custom_components.plant_care_scheduler.notifications import async_handle_action, register_callbacks
from tests.helpers import setup_one_plant


async def test_handle_action_marks_water(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    coord = entry.runtime_data
    assert coord.snapshot(sid, None, None)["needs_water"] is True
    await async_handle_action(hass, coord, "pcs::%s::water" % sid)
    await hass.async_block_till_done()
    assert coord.snapshot(sid, None, None)["needs_water"] is False   # rescheduled


async def test_handle_action_bad_payload_noop(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    coord = entry.runtime_data
    await async_handle_action(hass, coord, "garbage")          # must not raise
    await async_handle_action(hass, coord, "pcs::nope::water") # unknown sid: must not raise
    await hass.async_block_till_done()
    assert coord.snapshot(sid, None, None)["needs_water"] is True  # untouched


async def test_mobile_app_event_marks_plant(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    coord = entry.runtime_data
    from custom_components.plant_care_scheduler.const import CONF_NOTIFY_CHANNEL, CHANNEL_MOBILE_APP
    unsubs = register_callbacks(hass, entry, coord, {CONF_NOTIFY_CHANNEL: CHANNEL_MOBILE_APP})
    hass.bus.async_fire("mobile_app_notification_action", {"action": "pcs::%s::water" % sid})
    await hass.async_block_till_done()
    assert coord.snapshot(sid, None, None)["needs_water"] is False
    for u in unsubs:
        u()
