"""Date entities: next water/feed (editable)."""
from __future__ import annotations

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_NEXT_FEED, CONF_NEXT_WATER
from .entity import PlantCareEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        async_add_entities(
            [
                PlantDate(coordinator, subentry, CONF_NEXT_WATER, "next_water"),
                PlantDate(coordinator, subentry, CONF_NEXT_FEED, "next_feed"),
            ],
            config_subentry_id=subentry.subentry_id,
        )


class PlantDate(PlantCareEntity, DateEntity):
    def __init__(self, coordinator, subentry, key, slug):
        super().__init__(coordinator, subentry)
        self._key = key
        self._attr_translation_key = slug
        self._attr_unique_id = f"{subentry.subentry_id}_{slug}"

    @property
    def native_value(self) -> date:
        return self._snap[self._key]

    async def async_set_value(self, value: date) -> None:
        await self.coordinator.async_set_value(self._subentry_id, self._key, value)
