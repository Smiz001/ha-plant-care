"""v0.6.0: the aggregate calendar PROJECTS recurring future occurrences within
the queried range, not just the single next date per plant/action."""
from datetime import date

from homeassistant.core import HomeAssistant

from tests.helpers import setup_one_plant, setup_one_plant_with_treatment


async def _events(hass, lo, hi):
    r = await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": "calendar.plant_care_scheduler", "start_date_time": lo, "end_date_time": hi},
        blocking=True, return_response=True,
    )
    return r["calendar.plant_care_scheduler"]["events"]


def _starts(items, needle):
    """Sorted list of date() starts whose summary contains needle."""
    out = []
    for e in items:
        if needle in e["summary"]:
            out.append(date.fromisoformat(e["start"][:10]))
    return sorted(out)


async def test_water_projects_multiple_occurrences(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-30 08:00:00")
    # water_interval=3 (helper default); next_water today
    entry, sid = await setup_one_plant(hass, water_interval=3, next_water="2026-06-30")
    # over a ~5-week window there must be MANY watering events (recurrence), not 1
    items = await _events(hass, "2026-06-30 00:00:00", "2026-08-04 00:00:00")
    water = _starts(items, "Полив")
    assert len(water) >= 4  # recurrence, not a single next-date
    assert water[0] == date(2026, 6, 30)  # soonest next date is the first occurrence


async def test_water_spacing_equals_live_interval(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-30 08:00:00")
    interval = 4
    entry, sid = await setup_one_plant(hass, water_interval=interval, next_water="2026-06-30")
    items = await _events(hass, "2026-06-30 00:00:00", "2026-08-04 00:00:00")
    water = _starts(items, "Полив")
    assert len(water) >= 4
    # consecutive occurrences are spaced by exactly the live water_interval
    for a, b in zip(water, water[1:]):
        assert (b - a).days == interval


async def test_no_occurrences_far_future_window_is_bounded(hass: HomeAssistant, freezer):
    # a sane window returns a bounded list (cap), never hangs
    freezer.move_to("2026-06-30 08:00:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-30")
    items = await _events(hass, "2026-06-30 00:00:00", "2026-07-05 00:00:00")
    assert isinstance(items, list)


async def test_feeding_off_yields_no_feed_events(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-30 08:00:00")
    entry, sid = await setup_one_plant(
        hass, feeding_enabled=False, next_feed="2026-07-06"
    )
    items = await _events(hass, "2026-06-30 00:00:00", "2026-08-04 00:00:00")
    assert _starts(items, "Подкормка") == []


async def test_feeding_on_projects_multiple_with_feed_interval(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-30 08:00:00")
    interval = 7
    entry, sid = await setup_one_plant(
        hass, feeding_enabled=True, feed_interval=interval, next_feed="2026-06-30"
    )
    items = await _events(hass, "2026-06-30 00:00:00", "2026-08-04 00:00:00")
    feed = _starts(items, "Подкормка")
    assert len(feed) >= 4
    assert feed[0] == date(2026, 6, 30)
    for a, b in zip(feed, feed[1:]):
        assert (b - a).days == interval


async def test_treatment_count_bounded(hass: HomeAssistant, freezer):
    # treatment started with treatments_left=5, interval 3 (helper); a wide
    # window yields exactly 5 "Лечение" events (not more).
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant_with_treatment(hass)  # next_treatment 2026-06-28, left=5, interval=3
    items = await _events(hass, "2026-06-27 00:00:00", "2027-06-27 00:00:00")
    treatment = _starts(items, "Лечение")
    assert len(treatment) == 5
    # spaced by the treatment interval (3)
    for a, b in zip(treatment, treatment[1:]):
        assert (b - a).days == 3


async def test_treatment_until_bounded(hass: HomeAssistant, freezer):
    # With a treatment_until set, no "Лечение" event after that date even if the
    # count would allow more.
    freezer.move_to("2026-06-28 08:00:00")
    entry, sid = await setup_one_plant_with_treatment(hass)  # interval=3, left=5
    # cap the course at an until date that allows only the first 2 occurrences
    # (2026-06-28, 2026-07-01); 2026-07-04 is after until.
    until = date(2026, 7, 2)
    sub = next(iter(entry.subentries.values()))
    new_data = dict(sub.data)
    new_data["treatment_until"] = until.isoformat()
    hass.config_entries.async_update_subentry(entry, sub, data=new_data)
    await hass.async_block_till_done()

    items = await _events(hass, "2026-06-27 00:00:00", "2027-06-27 00:00:00")
    treatment = _starts(items, "Лечение")
    assert treatment  # at least the in-range first ones
    assert all(d <= until for d in treatment)
    assert treatment == [date(2026, 6, 28), date(2026, 7, 1)]


async def test_overdue_water_start_first_in_range_occurrence(hass: HomeAssistant, freezer):
    # next_water is in the PAST relative to the query lo -> first projected
    # occurrence is the correct in-range one (spacing preserved), none before lo.
    freezer.move_to("2026-06-30 08:00:00")
    interval = 5
    entry, sid = await setup_one_plant(
        hass, water_interval=interval, next_water="2026-06-10"
    )
    # query window starts 2026-06-30; occurrences from 2026-06-10 step 5:
    # 06-10, 06-15, 06-20, 06-25, 06-30, 07-05, ...  -> first in-range == 06-30
    lo = date(2026, 6, 30)
    items = await _events(hass, "2026-06-30 00:00:00", "2026-08-04 00:00:00")
    water = _starts(items, "Полив")
    assert water  # there are occurrences in range
    assert all(d >= lo for d in water)  # none before lo
    assert water[0] == date(2026, 6, 30)  # correct in-range occurrence (spacing preserved)
    for a, b in zip(water, water[1:]):
        assert (b - a).days == interval
