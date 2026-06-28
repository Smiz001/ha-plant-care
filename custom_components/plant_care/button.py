"""Buttons: mark watered / fed."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
                PlantActionButton(coordinator, subentry, "water", "watered", "Mark watered"),
                PlantActionButton(coordinator, subentry, "feed", "fed", "Mark fed"),
            ],
            config_subentry_id=subentry.subentry_id,
        )


class PlantActionButton(PlantCareEntity, ButtonEntity):
    def __init__(self, coordinator, subentry, task, slug, label):
        super().__init__(coordinator, subentry)
        self._task = task
        self._attr_translation_key = slug
        self._attr_unique_id = f"{subentry.subentry_id}_{slug}"
        self._attr_name = label

    async def async_press(self) -> None:
        await self.coordinator.async_mark_done(self._subentry_id, self._task)
