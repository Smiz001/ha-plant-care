from homeassistant.core import HomeAssistant
from custom_components.plant_care_scheduler.notifications import async_send_due_reminders, async_handle_action
from custom_components.plant_care_scheduler.const import (
    CONF_NOTIFY_CHANNEL, CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY, CONF_TELEGRAM_CHAT_ID,
)
from tests.helpers import setup_one_plant


async def test_water_reminder_has_snooze_button(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    opts = {CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42"}
    await async_send_due_reminders(hass, entry, entry.runtime_data, opts)
    row = calls[0].data["inline_keyboard"][0]
    assert len(row) == 2                                   # done + snooze
    assert row[1][1] == "pcs::%s::snooze_water" % sid       # 2nd button = snooze


async def test_feed_reminder_single_button(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    # a plant due for FEED only (water not due)
    entry, sid = await setup_one_plant(hass, next_water="2026-07-20", next_feed="2026-06-28")
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    opts = {CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42"}
    await async_send_due_reminders(hass, entry, entry.runtime_data, opts)
    feed_call = [c for c in calls if "подкорм" in c.data["message"]][0]
    assert len(feed_call.data["inline_keyboard"][0]) == 1   # feed = single button


async def test_snooze_tap_postpones_not_marks(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")   # due today, default interval
    coord = entry.runtime_data
    before = coord.snapshot(sid, None, None)["next_water"]
    await async_handle_action(hass, coord, "pcs::%s::snooze_water" % sid)
    await hass.async_block_till_done()
    after = coord.snapshot(sid, None, None)["next_water"]
    assert after.strftime("%Y-%m-%d") == "2026-06-30"       # today + DEFAULT_SNOOZE_DAYS(2)
    assert after != before
