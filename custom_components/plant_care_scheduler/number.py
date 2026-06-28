"""Number entities: water/feed interval (editable)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_FEED_INTERVAL, CONF_WATER_INTERVAL
from .entity import PlantCareEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    from .models import PlantConfig

    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        cfg = PlantConfig.from_data(dict(subentry.data))
        async_add_entities(
            [PlantIntervalNumber(coordinator, subentry, CONF_WATER_INTERVAL, "water_interval")],
            config_subentry_id=subentry.subentry_id,
        )
        if cfg.feeding_enabled:
            async_add_entities(
                [PlantIntervalNumber(coordinator, subentry, CONF_FEED_INTERVAL, "feed_interval")],
                config_subentry_id=subentry.subentry_id,
            )


class PlantIntervalNumber(PlantCareEntity, NumberEntity):
    _attr_native_min_value = 1
    _attr_native_max_value = 365
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "d"

    def __init__(self, coordinator, subentry, key, slug):
        super().__init__(coordinator, subentry)
        self._key = key
        self._attr_translation_key = slug
        self._attr_unique_id = f"{subentry.subentry_id}_{slug}"

    @property
    def native_value(self) -> float:
        return self._snap[self._key]

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_value(self._subentry_id, self._key, int(value))
