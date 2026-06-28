"""Buttons: mark watered / fed."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import PlantCareEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    from .models import PlantConfig

    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        cfg = PlantConfig.from_data(dict(subentry.data))
        async_add_entities(
            [PlantActionButton(coordinator, subentry, "water", "watered")],
            config_subentry_id=subentry.subentry_id,
        )
        if cfg.feeding_enabled:
            async_add_entities(
                [PlantActionButton(coordinator, subentry, "feed", "fed")],
                config_subentry_id=subentry.subentry_id,
            )
        if cfg.has_treatment:
            async_add_entities(
                [PlantTreatmentButton(coordinator, subentry)],
                config_subentry_id=subentry.subentry_id,
            )


class PlantActionButton(PlantCareEntity, ButtonEntity):
    def __init__(self, coordinator, subentry, task, slug):
        super().__init__(coordinator, subentry)
        self._task = task
        self._attr_translation_key = slug
        self._attr_unique_id = f"{subentry.subentry_id}_{slug}"

    async def async_press(self) -> None:
        await self.coordinator.async_mark_done(self._subentry_id, self._task)


class PlantTreatmentButton(PlantCareEntity, ButtonEntity):
    _attr_translation_key = "mark_treated"

    def __init__(self, coordinator, subentry):
        super().__init__(coordinator, subentry)
        self._attr_unique_id = f"{subentry.subentry_id}_mark_treated"

    async def async_press(self) -> None:
        await self.coordinator.async_mark_treated(self._subentry_id, self._cfg.treatment_interval)
