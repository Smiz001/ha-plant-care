"""Plant removal: prune live values, entities, and device on subentry remove."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.plant_care.const import DOMAIN
from tests.helpers import setup_one_plant


async def test_remove_subentry_prunes_everything(hass: HomeAssistant):
    entry, sid = await setup_one_plant(hass)

    # Present before removal: live values, device, water_interval entity.
    assert sid in entry.runtime_data._live
    assert dr.async_get(hass).async_get_device({(DOMAIN, sid)}) is not None
    ent_reg = er.async_get(hass)
    assert (
        ent_reg.async_get_entity_id("number", "plant_care", f"{sid}_water_interval")
        is not None
    )

    # async_remove_subentry is synchronous in this HA version (returns bool);
    # the removal triggers a reload, so wait for it to settle.
    assert hass.config_entries.async_remove_subentry(entry, sid)
    await hass.async_block_till_done()

    # Gone afterwards: live values pruned, entity unregistered, device removed.
    assert sid not in entry.runtime_data._live
    assert (
        ent_reg.async_get_entity_id("number", "plant_care", f"{sid}_water_interval")
        is None
    )
    assert dr.async_get(hass).async_get_device({(DOMAIN, sid)}) is None
