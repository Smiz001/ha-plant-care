"""Task 6: treatment events appear on the aggregate calendar only while active."""
from homeassistant.core import HomeAssistant
from tests.helpers import setup_one_plant, setup_one_plant_with_treatment


async def test_calendar_includes_treatment_event(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant_with_treatment(hass)  # next_treatment 2026-06-28, active
    events = await hass.services.async_call(
        "calendar", "get_events",
        {
            "entity_id": "calendar.plant_care_scheduler",
            "start_date_time": "2026-06-27 00:00:00",
            "end_date_time": "2026-07-10 00:00:00",
        },
        blocking=True, return_response=True,
    )
    summaries = [e["summary"] for e in events["calendar.plant_care_scheduler"]["events"]]
    assert any("Лечение" in s for s in summaries)


async def test_calendar_no_treatment_event_for_plain_plant(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant(hass)
    events = await hass.services.async_call(
        "calendar", "get_events",
        {
            "entity_id": "calendar.plant_care_scheduler",
            "start_date_time": "2026-06-27 00:00:00",
            "end_date_time": "2026-07-10 00:00:00",
        },
        blocking=True, return_response=True,
    )
    summaries = [e["summary"] for e in events["calendar.plant_care_scheduler"]["events"]]
    assert not any("Лечение" in s for s in summaries)
