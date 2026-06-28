"""Per-plant entities must use translation_key, not a hard-coded _attr_name.

If an entity sets `_attr_name`, HA returns that and ignores `translation_key`
(so all of ru.json's entity names are dead). We load the integration in
Russian: the resolved name must then be the ru.json translation, which proves
the name comes from `translation_key` and not from a leftover English
`_attr_name` override. The registry's user-facing `name` (override) is also
None, confirming no per-entity name was forced.
"""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_number_uses_translation_key(hass: HomeAssistant):
    hass.config.language = "ru"
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent_id = reg.async_get_entity_id("number", "plant_care_scheduler", f"{sid}_water_interval")
    assert ent_id is not None
    entry_reg = reg.async_get(ent_id)
    assert entry_reg.translation_key == "water_interval"
    assert entry_reg.name is None  # no per-entity name override
    # Name resolved from ru.json -> proves translation_key drives the name,
    # not a hard-coded English _attr_name ("Water interval").
    assert entry_reg.original_name == "Полив: интервал"


async def test_sensor_uses_translation_key(hass: HomeAssistant):
    hass.config.language = "ru"
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)
    ent_id = reg.async_get_entity_id("sensor", "plant_care_scheduler", f"{sid}_days_to_water")
    assert ent_id is not None
    entry_reg = reg.async_get(ent_id)
    assert entry_reg.translation_key == "days_to_water"
    assert entry_reg.name is None
    assert entry_reg.original_name == "Полив: дней до"
