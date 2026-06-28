"""Tests for the plant subentry reconfigure flow."""
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.plant_care_scheduler.const import (
    CONF_EMOJI, CONF_MOISTURE_SENSOR, CONF_MOISTURE_THRESHOLD, CONF_NAME,
    CONF_NEXT_WATER,
)
from tests.helpers import setup_one_plant


async def test_reconfigure_attaches_sensor(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "plant"),
        context={"source": "reconfigure", "subentry_id": sid},
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Жасмин",
            CONF_EMOJI: "🌼",
            CONF_MOISTURE_SENSOR: "sensor.test_moisture",
            CONF_MOISTURE_THRESHOLD: 40,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    sub = entry.subentries[sid]
    assert sub.data[CONF_MOISTURE_SENSOR] == "sensor.test_moisture"
    assert sub.data[CONF_MOISTURE_THRESHOLD] == 40
    # intervals/dates preserved (not wiped by reconfigure)
    assert sub.data[CONF_NEXT_WATER] == "2026-06-30"


async def test_reconfigure_detaches_sensor(hass: HomeAssistant):
    # Start WITH a moisture sensor, then reconfigure submitting only name+emoji
    # (no moisture_sensor key) -> the sensor must be detached.
    entry, sid = await setup_one_plant(
        hass, moisture_sensor="sensor.x", moisture_threshold=40
    )
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "plant"),
        context={"source": "reconfigure", "subentry_id": sid},
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_NAME: "Жасмин", CONF_EMOJI: "🌼"},  # no moisture_sensor submitted
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    sub = entry.subentries[sid]
    assert sub.data[CONF_MOISTURE_SENSOR] is None
