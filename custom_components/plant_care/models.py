"""Pure, HA-independent logic for Plant Care."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .const import CONF_EMOJI, CONF_MOISTURE_SENSOR, CONF_MOISTURE_THRESHOLD, CONF_NAME, DEFAULT_EMOJI


@dataclass(frozen=True)
class PlantConfig:
    """Static per-plant config (from subentry.data)."""

    name: str
    emoji: str
    moisture_sensor: str | None
    moisture_threshold: float | None

    @classmethod
    def from_data(cls, data: dict) -> "PlantConfig":
        threshold = data.get(CONF_MOISTURE_THRESHOLD)
        return cls(
            name=data[CONF_NAME],
            emoji=data.get(CONF_EMOJI) or DEFAULT_EMOJI,
            moisture_sensor=data.get(CONF_MOISTURE_SENSOR) or None,
            moisture_threshold=float(threshold) if threshold is not None else None,
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
