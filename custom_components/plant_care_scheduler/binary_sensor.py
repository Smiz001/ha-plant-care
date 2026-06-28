"""Binary sensors: needs water / needs feed."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .entity import PlantCareEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    from .models import PlantConfig

    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        cfg = PlantConfig.from_data(dict(subentry.data))
        async_add_entities(
            [PlantNeedsBinary(coordinator, subentry, "needs_water")],
            config_subentry_id=subentry.subentry_id,
        )
        if cfg.feeding_enabled:
            async_add_entities(
                [PlantNeedsBinary(coordinator, subentry, "needs_feed")],
                config_subentry_id=subentry.subentry_id,
            )
        if cfg.has_treatment:
            async_add_entities(
                [PlantNeedsBinary(coordinator, subentry, "needs_treatment")],
                config_subentry_id=subentry.subentry_id,
            )


class PlantNeedsBinary(PlantCareEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, subentry, key):
        super().__init__(coordinator, subentry)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"

    @property
    def is_on(self) -> bool:
        return bool(self._snap[self._key])

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Recompute when the linked moisture sensor changes. Only the water
        # binary uses moisture; feed is calendar-only, so it must not subscribe.
        if self._cfg.moisture_sensor and self._key == "needs_water":
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._cfg.moisture_sensor], self._handle_source
                )
            )

    @callback
    def _handle_source(self, _event) -> None:
        self.async_write_ha_state()
