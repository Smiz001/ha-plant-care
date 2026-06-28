"""Live state Store + coordinator for Plant Care."""
from __future__ import annotations

import logging
import math
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FEED_INTERVAL,
    CONF_NEXT_FEED,
    CONF_NEXT_TREATMENT,
    CONF_NEXT_WATER,
    CONF_TREATMENTS_LEFT,
    CONF_WATER_INTERVAL,
    DEFAULT_FEED_INTERVAL,
    DEFAULT_WATER_INTERVAL,
    DOMAIN,
    STORAGE_VERSION,
)
from .models import days_until, is_calendar_due, is_moisture_due, next_after_action, treatment_finished

_LOGGER = logging.getLogger(__name__)


def _iso(d: date) -> str:
    return d.isoformat()


def _parse(s: str) -> date:
    return date.fromisoformat(s)


class PlantCareCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Owns the live-value Store and exposes per-plant snapshots."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=None)
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._live: dict[str, dict] = {}
        self._warned_corrupt: set[str] = set()

    def _parse_or_today(
        self, subentry_id: str, live: dict, key: str, today: date
    ) -> date:
        """Parse a stored ISO date; fall back to today if corrupt/missing.

        A bad value would otherwise raise and break all of the plant's
        entities; treating it as "due today" keeps the plant visible and
        recoverable (the user can re-set the date).
        """
        try:
            return _parse(live[key])
        except (KeyError, ValueError, TypeError):
            # Key on the stable subentry_id, not id(live) (reused after GC).
            warn_key = f"{subentry_id}:{key}"
            if warn_key not in self._warned_corrupt:
                self._warned_corrupt.add(warn_key)
                _LOGGER.warning(
                    "plant_care: corrupt/missing stored %s (%r); using today",
                    key,
                    live.get(key),
                )
            return today

    def _plant(self, subentry_id: str) -> dict:
        try:
            return self._live[subentry_id]
        except KeyError:
            raise KeyError(
                f"Plant {subentry_id} has no live values; ensure_seed() must run first"
            ) from None

    async def async_load(self) -> None:
        self._live = await self._store.async_load() or {}

    async def _save(self) -> None:
        await self._store.async_save(self._live)

    @callback
    def ensure_seed(
        self,
        subentry_id: str,
        water_interval: int,
        feed_interval: int,
        next_water: date,
        next_feed: date,
    ) -> None:
        """Seed live values for a plant if not present yet."""
        if subentry_id in self._live:
            return
        self._live[subentry_id] = {
            CONF_WATER_INTERVAL: int(water_interval),
            CONF_FEED_INTERVAL: int(feed_interval),
            CONF_NEXT_WATER: _iso(next_water),
            CONF_NEXT_FEED: _iso(next_feed),
        }

    @callback
    def prune(self, valid_ids: set[str]) -> None:
        """Drop live values for plants that no longer exist."""
        for sid in list(self._live):
            if sid not in valid_ids:
                del self._live[sid]
        # Drop corrupt-warning keys for removed plants so the set stays bounded.
        self._warned_corrupt = {
            k for k in self._warned_corrupt if k.split(":", 1)[0] in valid_ids
        }

    def _moisture(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        try:
            val = float(state.state)
        except (TypeError, ValueError):
            return None
        # NaN/inf parse fine but are not usable readings; treat as unknown so
        # comparisons (val < threshold) don't silently report "not due".
        return val if math.isfinite(val) else None

    @callback
    def snapshot(
        self,
        subentry_id: str,
        cfg_moisture_sensor: str | None,
        cfg_moisture_threshold: float | None,
        treatment_name: str | None = None,
        treatment_interval: int | None = None,
        treatment_until=None,
    ) -> dict:
        live = self._plant(subentry_id)
        today = dt_util.now().date()
        next_water = self._parse_or_today(subentry_id, live, CONF_NEXT_WATER, today)
        next_feed = self._parse_or_today(subentry_id, live, CONF_NEXT_FEED, today)
        moisture = self._moisture(cfg_moisture_sensor)
        # Only trust the moisture reading when it is actually known. If the
        # sensor is unavailable/unknown/non-numeric, fall back to the calendar
        # so an overdue plant still reports "due" instead of silently "not due".
        if (
            cfg_moisture_sensor
            and cfg_moisture_threshold is not None
            and moisture is not None
        ):
            needs_water = is_moisture_due(moisture, cfg_moisture_threshold)
        else:
            needs_water = is_calendar_due(next_water, today)

        nt_raw = live.get(CONF_NEXT_TREATMENT)
        next_treatment = date.fromisoformat(nt_raw) if nt_raw else None
        treatments_left = live.get(CONF_TREATMENTS_LEFT)
        has_treatment = bool(treatment_name)
        finished = treatment_finished(treatments_left, treatment_until, today) if has_treatment else False
        # A treatment is only active when a schedule is configured (name set),
        # the course is not finished, AND a next_treatment date is actually
        # stored (i.e. the course has been started / not cleared).
        treatment_active = has_treatment and not finished and next_treatment is not None
        needs_treatment = bool(treatment_active and next_treatment <= today)

        return {
            # Default missing interval keys: a partial/older Store must not
            # KeyError and break every entity for this plant.
            CONF_WATER_INTERVAL: live.get(CONF_WATER_INTERVAL, DEFAULT_WATER_INTERVAL),
            CONF_FEED_INTERVAL: live.get(CONF_FEED_INTERVAL, DEFAULT_FEED_INTERVAL),
            CONF_NEXT_WATER: next_water,
            CONF_NEXT_FEED: next_feed,
            "days_to_water": days_until(next_water, today),
            "days_to_feed": days_until(next_feed, today),
            "needs_water": needs_water,
            "needs_feed": is_calendar_due(next_feed, today),
            "moisture": moisture,
            "treatment_active": treatment_active,
            "needs_treatment": needs_treatment,
            "next_treatment": next_treatment,
            "treatments_left": treatments_left,
            "days_to_treatment": (next_treatment - today).days if next_treatment else None,
            "treatment_name": treatment_name,
        }

    async def async_set_value(self, subentry_id: str, key: str, value) -> None:
        if isinstance(value, date):
            value = _iso(value)
        if key in (CONF_WATER_INTERVAL, CONF_FEED_INTERVAL):
            value = int(value)
        self._plant(subentry_id)[key] = value
        await self._save()
        self.async_update_listeners()

    async def async_mark_done(self, subentry_id: str, task: str) -> None:
        today = dt_util.now().date()
        interval = self._plant(subentry_id)[
            CONF_WATER_INTERVAL if task == "water" else CONF_FEED_INTERVAL
        ]
        key = CONF_NEXT_WATER if task == "water" else CONF_NEXT_FEED
        self._plant(subentry_id)[key] = _iso(next_after_action(today, interval))
        await self._save()
        self.async_update_listeners()

    async def async_set_treatment(self, subentry_id: str, next_treatment: date, treatments_left: int) -> None:
        p = self._plant(subentry_id)
        p[CONF_NEXT_TREATMENT] = next_treatment.isoformat()
        p[CONF_TREATMENTS_LEFT] = treatments_left
        await self._save()
        self.async_update_listeners()

    async def async_clear_treatment(self, subentry_id: str) -> None:
        p = self._plant(subentry_id)
        p.pop(CONF_NEXT_TREATMENT, None)
        p.pop(CONF_TREATMENTS_LEFT, None)
        await self._save()
        self.async_update_listeners()

    async def async_mark_treated(self, subentry_id: str, interval: int) -> None:
        p = self._plant(subentry_id)
        today = dt_util.now().date()
        if p.get(CONF_TREATMENTS_LEFT) is not None:
            p[CONF_TREATMENTS_LEFT] = int(p[CONF_TREATMENTS_LEFT]) - 1
        p[CONF_NEXT_TREATMENT] = (today + timedelta(days=int(interval))).isoformat()
        await self._save()
        self.async_update_listeners()
