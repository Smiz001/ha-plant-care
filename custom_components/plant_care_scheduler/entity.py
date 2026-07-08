"""Base entity for Plant Care plants."""
from __future__ import annotations

from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PlantCareCoordinator
from .models import PlantConfig


class PlantCareEntity(CoordinatorEntity[PlantCareCoordinator]):
    """Base: bound to one plant subentry, grouped under its device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PlantCareCoordinator, subentry: ConfigSubentry) -> None:
        super().__init__(coordinator)
        self._subentry_id = subentry.subentry_id
        self._cfg = PlantConfig.from_data(dict(subentry.data))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=f"{self._cfg.emoji} {self._cfg.name}",
            manufacturer="Plant Care Scheduler",
            model="Plant",
        )

    @property
    def _snap(self) -> dict:
        return self.coordinator.snapshot(
            self._subentry_id,
            self._cfg.moisture_sensor,
            self._cfg.moisture_threshold,
            self._cfg.treatment_name,
            self._cfg.treatment_interval,
            self._cfg.treatment_until,
            weather_enabled=self._cfg.weather_enabled,
            rain_skip=self._cfg.rain_skip,
        )
