from homeassistant.core import HomeAssistant

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
