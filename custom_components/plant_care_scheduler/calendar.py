"""One aggregate calendar across all plants (hub-owned)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_FEED_INTERVAL,
    CONF_NEXT_FEED,
    CONF_NEXT_WATER,
    CONF_WATER_INTERVAL,
)
from .coordinator import PlantCareCoordinator
from .models import PlantConfig


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([PlantCareCalendar(entry.runtime_data, entry)])


def _event(d: date, summary: str) -> CalendarEvent:
    return CalendarEvent(start=d, end=d + timedelta(days=1), summary=summary)


def _project(
    first: date | None,
    interval: int | None,
    lo: date,
    hi: date,
    summary: str,
    cap: int = 370,
) -> list[CalendarEvent]:
    """Project a recurring all-day event from `first` every `interval` days
    into the half-open window [lo, hi). Without a positive interval, only the
    single date is emitted (when in range)."""
    out: list[CalendarEvent] = []
    if not interval or interval <= 0:
        if first is not None and lo <= first < hi:
            out.append(_event(first, summary))
        return out
    o = first
    if o < lo:
        steps = (lo - o).days // interval
        o = first + timedelta(days=steps * interval)
        while o < lo:
            o += timedelta(days=interval)
    n = 0
    while o < hi and n < cap:
        out.append(_event(o, summary))
        o += timedelta(days=interval)
        n += 1
    return out


def _project_treatment(
    first: date | None,
    interval: int | None,
    left: int | None,
    until: date | None,
    lo: date,
    hi: date,
    summary: str,
    cap: int = 370,
) -> list[CalendarEvent]:
    """Project a finite treatment course. Bounded by `left` (occurrence count,
    counting pre-window ones too) and `until` (no occurrence after that date)."""
    out: list[CalendarEvent] = []
    if first is None:
        return out
    if not interval or interval <= 0:
        if lo <= first < hi and (until is None or first <= until):
            out.append(_event(first, summary))
        return out
    o = first
    produced = 0  # occurrences from `first` (counts toward `left`, incl. pre-lo)
    n = 0
    while n < cap:
        if left is not None and produced >= left:
            break
        if until is not None and o > until:
            break
        if o >= hi:
            break
        if o >= lo:
            out.append(_event(o, summary))
            n += 1
        produced += 1
        o += timedelta(days=interval)
    return out


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
                subentry.subentry_id, cfg.moisture_sensor, cfg.moisture_threshold,
                cfg.treatment_name, cfg.treatment_interval, cfg.treatment_until,
            )
            pairs = [(CONF_NEXT_WATER, "Полив")]
            if cfg.feeding_enabled:
                pairs.append((CONF_NEXT_FEED, "Подкормка"))
            for key, verb in pairs:
                d: date = snap[key]
                events.append(
                    CalendarEvent(
                        start=d,
                        end=d + timedelta(days=1),
                        summary=f"{cfg.emoji} {verb}: {cfg.name}",
                    )
                )
            if snap["treatment_active"]:
                td: date = snap["next_treatment"]
                events.append(
                    CalendarEvent(
                        start=td,
                        end=td + timedelta(days=1),
                        summary=f"🩹 Лечение: {cfg.name}",
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
        events: list[CalendarEvent] = []
        for subentry in self._entry.subentries.values():
            cfg = PlantConfig.from_data(dict(subentry.data))
            snap = self.coordinator.snapshot(
                subentry.subentry_id, cfg.moisture_sensor, cfg.moisture_threshold,
                cfg.treatment_name, cfg.treatment_interval, cfg.treatment_until,
            )
            events += _project(
                snap[CONF_NEXT_WATER], snap[CONF_WATER_INTERVAL], lo, hi,
                f"{cfg.emoji} Полив: {cfg.name}",
            )
            if cfg.feeding_enabled:
                events += _project(
                    snap[CONF_NEXT_FEED], snap[CONF_FEED_INTERVAL], lo, hi,
                    f"{cfg.emoji} Подкормка: {cfg.name}",
                )
            if snap["treatment_active"]:
                events += _project_treatment(
                    snap["next_treatment"], cfg.treatment_interval,
                    snap["treatments_left"], cfg.treatment_until, lo, hi,
                    f"🩹 Лечение: {cfg.name}",
                )
        return events
