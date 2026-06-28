"""Pure, HA-independent logic for Plant Care."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .const import (
    CONF_EMOJI,
    CONF_MOISTURE_SENSOR,
    CONF_MOISTURE_THRESHOLD,
    CONF_NAME,
    CONF_TREATMENT_INTERVAL,
    CONF_TREATMENT_NAME,
    CONF_TREATMENT_UNTIL,
    DEFAULT_EMOJI,
)


@dataclass(frozen=True)
class PlantConfig:
    """Static per-plant config (from subentry.data)."""

    name: str
    emoji: str
    moisture_sensor: str | None
    moisture_threshold: float | None
    treatment_name: str | None
    treatment_interval: int | None
    treatment_until: date | None

    @property
    def has_treatment(self) -> bool:
        return bool(self.treatment_name)

    @classmethod
    def from_data(cls, data: dict) -> "PlantConfig":
        threshold = data.get(CONF_MOISTURE_THRESHOLD)
        if threshold is not None:
            try:
                threshold = float(threshold)
            except (TypeError, ValueError):
                threshold = None
        t_name = data.get(CONF_TREATMENT_NAME) or None
        t_int = data.get(CONF_TREATMENT_INTERVAL)
        if t_int is not None:
            try:
                t_int = int(t_int)
            except (TypeError, ValueError):
                t_int = None
        t_until = data.get(CONF_TREATMENT_UNTIL)
        if t_until:
            try:
                t_until = date.fromisoformat(t_until)
            except (TypeError, ValueError):
                t_until = None
        else:
            t_until = None
        return cls(
            name=data[CONF_NAME],
            emoji=data.get(CONF_EMOJI) or DEFAULT_EMOJI,
            moisture_sensor=data.get(CONF_MOISTURE_SENSOR) or None,
            moisture_threshold=threshold,
            treatment_name=t_name,
            treatment_interval=t_int,
            treatment_until=t_until,
        )


def days_until(target: date, today: date) -> int:
    """Whole days from today to target (negative if overdue)."""
    return (target - today).days


def next_after_action(today: date, interval_days: int) -> date:
    """Next due date after doing the action today."""
    return today + timedelta(days=int(interval_days))


def is_calendar_due(next_date: date, today: date) -> bool:
    """Due when the next date is today or in the past."""
    return next_date <= today


def is_moisture_due(moisture: float | None, threshold: float | None) -> bool:
    """Due when measured moisture is below threshold (both must be known)."""
    if moisture is None or threshold is None:
        return False
    return moisture < threshold


def treatment_finished(treatments_left, treatment_until, today: date) -> bool:
    """Course is done when the count is used up or the end date has passed."""
    if treatments_left is not None and treatments_left <= 0:
        return True
    if treatment_until is not None and today > treatment_until:
        return True
    return False
