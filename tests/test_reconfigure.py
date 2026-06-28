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


async def test_reconfigure_starts_and_stops_treatment(hass):
    from tests.helpers import setup_one_plant
    from custom_components.plant_care_scheduler.const import (
        CONF_NAME, CONF_EMOJI, CONF_TREATMENT_NAME, CONF_TREATMENT_INTERVAL,
        CONF_NEXT_TREATMENT, CONF_TREATMENTS_LEFT, CONF_NEXT_WATER,
    )
    entry, sid = await setup_one_plant(hass)
    r = await hass.config_entries.subentries.async_init((entry.entry_id, "plant"),
        context={"source": "reconfigure", "subentry_id": sid})
    r = await hass.config_entries.subentries.async_configure(r["flow_id"], {
        CONF_NAME: "Жасмин", CONF_EMOJI: "🌼",
        CONF_TREATMENT_NAME: "Фунгицид", CONF_TREATMENT_INTERVAL: 3,
        CONF_NEXT_TREATMENT: "2026-06-30", CONF_TREATMENTS_LEFT: 5,
    })
    assert r["type"].value == "abort" and r["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    entry = hass.config_entries.async_get_entry(entry.entry_id)
    sub = entry.subentries[sid]
    assert sub.data[CONF_TREATMENT_NAME] == "Фунгицид"
    assert sub.data[CONF_NEXT_WATER] == "2026-06-30"  # water schedule preserved
    coord = entry.runtime_data
    snap = coord.snapshot(sid, None, None, treatment_name="Фунгицид", treatment_interval=3)
    assert snap["treatment_active"] is True
    assert snap["treatments_left"] == 5
    # stop treatment by clearing the name
    r = await hass.config_entries.subentries.async_init((entry.entry_id, "plant"),
        context={"source": "reconfigure", "subentry_id": sid})
    r = await hass.config_entries.subentries.async_configure(r["flow_id"],
        {CONF_NAME: "Жасмин", CONF_EMOJI: "🌼", CONF_TREATMENT_NAME: ""})
    await hass.async_block_till_done()
    sub = hass.config_entries.async_get_entry(entry.entry_id).subentries[sid]
    assert not sub.data.get(CONF_TREATMENT_NAME)
