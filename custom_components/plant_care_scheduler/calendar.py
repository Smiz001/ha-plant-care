"""One aggregate calendar across all plants (hub-owned)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_NEXT_FEED, CONF_NEXT_WATER
from .coordinator import PlantCareCoordinator
from .models import PlantConfig


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([PlantCareCalendar(entry.runtime_data, entry)])


class PlantCareCalendar(CalendarEntity):
    _attr_has_entity_name = False
    _attr_name = "Plant Care Scheduler"
    _attr_should_poll = False

    def __init__(self, coordinator: PlantCareCoordinator, entry) -> None:
        self.coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendar"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Subscribe to coordinator updates so calendar events refresh promptly
        # (value edits, mark-done, midnight refresh) instead of lagging ~60s.
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    def _all_events(self) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        for subentry in self._entry.subentries.values():
            cfg = PlantConfig.from_data(dict(subentry.data))
            snap = self.coordinator.snapshot(
                subentry.subentry_id, cfg.moisture_sensor, cfg.moisture_threshold
            )
            for key, verb in ((CONF_NEXT_WATER, "Полив"), (CONF_NEXT_FEED, "Подкормка")):
                d: date = snap[key]
                events.append(
                    CalendarEvent(
                        start=d,
                        end=d + timedelta(days=1),
                        summary=f"{cfg.emoji} {verb}: {cfg.name}",
                    )
                )
        return events

    @property
    def event(self) -> CalendarEvent | None:
        upcoming = sorted(self._all_events(), key=lambda e: e.start)
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        lo, hi = start_date.date(), end_date.date()
        return [e for e in self._all_events() if lo <= e.start < hi]
