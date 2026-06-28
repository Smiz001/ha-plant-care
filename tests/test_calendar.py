from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_calendar_lists_events(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)  # next_water 2026-06-30, next_feed 2026-07-06
    events = await hass.services.async_call(
        "calendar", "get_events",
        {
            "entity_id": "calendar.plant_care",
            "start_date_time": "2026-06-28 00:00:00",
            "end_date_time": "2026-07-10 00:00:00",
        },
        blocking=True, return_response=True,
    )
    items = events["calendar.plant_care"]["events"]
    summaries = [e["summary"] for e in items]
    assert any("Жасмин" in s for s in summaries)
    assert any("полив" in s.lower() for s in summaries)


async def test_calendar_refreshes_on_coordinator_update(hass: HomeAssistant, freezer):
    # Calendar subscribes to the coordinator (no polling): editing the next
    # watering date must update the calendar's next-event attribute promptly.
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant(
        hass, next_water="2026-06-30", next_feed="2026-07-06"
    )
    start_before = hass.states.get("calendar.plant_care").attributes["start_time"]

    # Move next watering earlier via the date entity -> coordinator notifies.
    reg = er.async_get(hass)
    date_ent = reg.async_get_entity_id("date", "plant_care", f"{sid}_next_water")
    await hass.services.async_call(
        "date", "set_value", {"entity_id": date_ent, "date": "2026-06-29"},
        blocking=True,
    )
    await hass.async_block_till_done()

    start_after = hass.states.get("calendar.plant_care").attributes["start_time"]
    assert start_after != start_before  # refreshed without polling
