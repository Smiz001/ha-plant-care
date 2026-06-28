from datetime import date

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care.const import (
    CONF_FEED_INTERVAL, CONF_NAME, CONF_NEXT_FEED, CONF_NEXT_WATER,
    CONF_WATER_INTERVAL, DOMAIN, SUBENTRY_TYPE,
)


async def test_add_plant_subentry(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE), context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Жасмин",
            "emoji": "🌼",
            CONF_WATER_INTERVAL: 3,
            CONF_FEED_INTERVAL: 7,
            CONF_NEXT_WATER: "2026-06-30",
            CONF_NEXT_FEED: "2026-07-06",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert len(entry.subentries) == 1
    sub = next(iter(entry.subentries.values()))
    assert sub.title == "Жасмин"
    coord = entry.runtime_data
    snap = coord.snapshot(sub.subentry_id, None, None)
    assert snap[CONF_WATER_INTERVAL] == 3
    assert snap[CONF_NEXT_WATER] == date(2026, 6, 30)
