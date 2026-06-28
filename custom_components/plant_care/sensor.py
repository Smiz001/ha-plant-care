"""Sensors: days until next water/feed."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlantCareEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        async_add_entities(
            [
                PlantDaysSensor(coordinator, subentry, "days_to_water", "Days to watering"),
                PlantDaysSensor(coordinator, subentry, "days_to_feed", "Days to feeding"),
            ],
            config_subentry_id=subentry.subentry_id,
        )


class PlantDaysSensor(PlantCareEntity, SensorEntity):
    _attr_native_unit_of_measurement = "d"

    def __init__(self, coordinator, subentry, key, label):
        super().__init__(coordinator, subentry)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"
        self._attr_name = label

    @property
    def native_value(self) -> int:
        return self._snap[self._key]
