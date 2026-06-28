"""Live state Store + coordinator for Plant Care."""
from __future__ import annotations

import logging
from datetime import date

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FEED_INTERVAL,
    CONF_NEXT_FEED,
    CONF_NEXT_WATER,
    CONF_WATER_INTERVAL,
    DOMAIN,
    STORAGE_VERSION,
)
from .models import days_until, is_calendar_due, is_moisture_due, next_after_action

_LOGGER = logging.getLogger(__name__)


def _iso(d: date) -> str:
    return d.isoformat()


def _parse(s: str) -> date:
    return date.fromisoformat(s)


class PlantCareCoordinator(DataUpdateCoordinator[dict[str, dict]]):
    """Owns the live-value Store and exposes per-plant snapshots."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=None)
        self.entry = entry
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._live: dict[str, dict] = {}

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

    def _moisture(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @callback
    def snapshot(
        self,
        subentry_id: str,
        cfg_moisture_sensor: str | None,
        cfg_moisture_threshold: float | None,
    ) -> dict:
        live = self._live[subentry_id]
        today = dt_util.now().date()
        next_water = _parse(live[CONF_NEXT_WATER])
        next_feed = _parse(live[CONF_NEXT_FEED])
        moisture = self._moisture(cfg_moisture_sensor)
        if cfg_moisture_sensor and cfg_moisture_threshold is not None:
            needs_water = is_moisture_due(moisture, cfg_moisture_threshold)
        else:
            needs_water = is_calendar_due(next_water, today)
        return {
            CONF_WATER_INTERVAL: live[CONF_WATER_INTERVAL],
            CONF_FEED_INTERVAL: live[CONF_FEED_INTERVAL],
            CONF_NEXT_WATER: next_water,
            CONF_NEXT_FEED: next_feed,
            "days_to_water": days_until(next_water, today),
            "days_to_feed": days_until(next_feed, today),
            "needs_water": needs_water,
            "needs_feed": is_calendar_due(next_feed, today),
            "moisture": moisture,
        }

    async def async_set_value(self, subentry_id: str, key: str, value) -> None:
        if isinstance(value, date):
            value = _iso(value)
        if key in (CONF_WATER_INTERVAL, CONF_FEED_INTERVAL):
            value = int(value)
        self._live[subentry_id][key] = value
        await self._save()
        self.async_update_listeners()

    async def async_mark_done(self, subentry_id: str, task: str) -> None:
        today = dt_util.now().date()
        interval = self._live[subentry_id][
            CONF_WATER_INTERVAL if task == "water" else CONF_FEED_INTERVAL
        ]
        key = CONF_NEXT_WATER if task == "water" else CONF_NEXT_FEED
        self._live[subentry_id][key] = _iso(next_after_action(today, interval))
        await self._save()
        self.async_update_listeners()
