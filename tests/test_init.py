"""Tests for Plant Care setup."""
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plant_care.const import DOMAIN
from custom_components.plant_care.coordinator import PlantCareCoordinator


def test_domain():
    assert DOMAIN == "plant_care"


async def test_setup_and_unload(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Plant Care")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, PlantCareCoordinator)

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
