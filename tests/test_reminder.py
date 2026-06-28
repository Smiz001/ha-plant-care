"""Tests for optional daily reminder via notify service."""
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.plant_care.const import CONF_NOTIFY_TARGET
from custom_components.plant_care.notify_reminder import async_send_due_reminders
from tests.helpers import setup_one_plant


async def test_reminder_calls_notify(hass: HomeAssistant, freezer):
    freezer.move_to("2026-07-01 09:00:00")  # past next_water 06-30 -> due
    entry, sid = await setup_one_plant(
        hass, options={CONF_NOTIFY_TARGET: "notify.mock"}
    )
    # The reminder now prechecks has_service(); register a dummy so the call
    # path is exercised (async_call is still patched for the assertion).
    hass.services.async_register("notify", "mock", lambda call: None)

    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as call:
        await async_send_due_reminders(hass, entry)

    assert call.await_count >= 1
    args = call.await_args_list[0].args
    assert args[0] == "notify"


async def test_reminder_noop_without_target(hass: HomeAssistant, freezer):
    freezer.move_to("2026-07-01 09:00:00")
    entry, sid = await setup_one_plant(hass)  # no notify target
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as call:
        await async_send_due_reminders(hass, entry)
    assert call.await_count == 0


async def test_reminder_invalid_target_no_call(hass: HomeAssistant, freezer):
    # "notify." passes a naive `"." in target` check but splits to an empty
    # service -> must NOT raise and must make zero notify calls.
    freezer.move_to("2026-07-01 09:00:00")  # plant is due
    entry, sid = await setup_one_plant(
        hass, options={CONF_NOTIFY_TARGET: "notify."}
    )
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as call:
        await async_send_due_reminders(hass, entry)  # must not raise
    assert call.await_count == 0


async def test_reminder_unregistered_service_no_call(hass: HomeAssistant, freezer):
    # A well-formed target whose notify service is not registered must short
    # out with a single warning, not spam a traceback per due plant per day.
    freezer.move_to("2026-07-01 09:00:00")  # plant is due
    entry, sid = await setup_one_plant(
        hass, options={CONF_NOTIFY_TARGET: "notify.does_not_exist"}
    )
    with patch(
        "homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock
    ) as call:
        await async_send_due_reminders(hass, entry)  # must not raise
    assert call.await_count == 0
