from homeassistant.core import HomeAssistant
from custom_components.plant_care_scheduler.notifications import async_send_due_reminders
from custom_components.plant_care_scheduler.const import (
    CONF_NOTIFY_CHANNEL, CHANNEL_TELEGRAM, CHANNEL_MOBILE_APP,
    CONF_TELEGRAM_CONFIG_ENTRY, CONF_TELEGRAM_CHAT_ID, CONF_MOBILE_APP_SERVICE,
)
from tests.helpers import setup_one_plant


async def test_sends_telegram_for_due_plant(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")  # due today
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    opts = {CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42"}
    await async_send_due_reminders(hass, entry, entry.runtime_data, opts)
    assert len(calls) == 1
    data = calls[0].data
    assert data["chat_id"] == "42" and data["config_entry_id"] == "TG"
    assert ("pcs::%s::water" % sid) in str(data["inline_keyboard"])
    assert "полить" in data["message"]


async def test_sends_mobile_app_for_due_plant(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-06-28")
    calls = []
    hass.services.async_register("notify", "mobile_app_test", lambda c: calls.append(c))
    opts = {CONF_NOTIFY_CHANNEL: CHANNEL_MOBILE_APP, CONF_MOBILE_APP_SERVICE: "notify.mobile_app_test"}
    await async_send_due_reminders(hass, entry, entry.runtime_data, opts)
    assert len(calls) == 1
    actions = calls[0].data["data"]["actions"]
    assert actions[0]["action"] == ("pcs::%s::water" % sid)


async def test_not_due_plant_no_send(hass: HomeAssistant, freezer):
    freezer.move_to("2026-06-28 08:30:00")
    entry, sid = await setup_one_plant(hass, next_water="2026-07-10", next_feed="2026-07-10")  # not due
    calls = []
    hass.services.async_register("telegram_bot", "send_message", lambda c: calls.append(c))
    opts = {CONF_NOTIFY_CHANNEL: CHANNEL_TELEGRAM, CONF_TELEGRAM_CONFIG_ENTRY: "TG", CONF_TELEGRAM_CHAT_ID: "42"}
    await async_send_due_reminders(hass, entry, entry.runtime_data, opts)
    assert calls == []
