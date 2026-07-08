"""The Plant Care integration."""
from __future__ import annotations

from datetime import date as date_cls, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FEED_INTERVAL,
    CONF_NEXT_FEED,
    CONF_NEXT_WATER,
    CONF_WATER_INTERVAL,
    CONF_WEATHER_ENTITY,
    DEFAULT_FEED_INTERVAL,
    DEFAULT_WATER_INTERVAL,
    PLATFORMS,
)
from .coordinator import PlantCareCoordinator
from .notifications import async_setup_notifications

type PlantCareConfigEntry = ConfigEntry[PlantCareCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PlantCareConfigEntry) -> bool:
    """Set up the hub: build the coordinator, forward platforms."""
    coordinator = PlantCareCoordinator(hass, entry)
    await coordinator.async_load()
    entry.runtime_data = coordinator

    # Seed live values for every plant subentry (idempotent: only on first add).
    today = dt_util.now().date()
    for subentry in entry.subentries.values():
        data = subentry.data
        try:
            nw = date_cls.fromisoformat(data[CONF_NEXT_WATER])
            nf = date_cls.fromisoformat(data[CONF_NEXT_FEED])
            wi = int(data[CONF_WATER_INTERVAL])
            fi = int(data[CONF_FEED_INTERVAL])
        except (KeyError, ValueError, TypeError):
            wi, fi = DEFAULT_WATER_INTERVAL, DEFAULT_FEED_INTERVAL
            nw, nf = today + timedelta(days=wi), today + timedelta(days=fi)
        coordinator.ensure_seed(subentry.subentry_id, wi, fi, nw, nf)
    coordinator.prune(set(entry.subentries))
    await coordinator._save()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the hub when subentries (plants) or options change. Value edits go
    # through the coordinator/Store and do NOT update the entry, so they don't reload.
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    # Date-derived state (days_to_*, needs_* via calendar) only updates when the
    # coordinator notifies listeners. Nothing does so at the day rollover, so
    # refresh shortly after midnight to keep those entities current.
    @callback
    def _midnight_refresh(now):
        coordinator.async_update_listeners()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight_refresh, hour=0, minute=0, second=10)
    )

    # Weather-aware watering (opt-in): fetch once at setup so the snapshot is
    # warm immediately, then keep it fresh hourly. Also refreshed right before
    # the daily reminder fires (see notifications.py) so taps act on current
    # conditions even if the hourly tick hasn't landed yet.
    weather_entity = entry.options.get(CONF_WEATHER_ENTITY)
    if weather_entity:
        await coordinator.async_refresh_weather(weather_entity)

        entry.async_on_unload(
            async_track_time_change(
                hass,
                lambda now: hass.async_create_task(
                    coordinator.async_refresh_weather(entry.options.get(CONF_WEATHER_ENTITY))
                ),
                minute=3,
                second=0,
            )
        )

    # Opt-in built-in actionable reminders (daily trigger + tap listeners).
    # No-op unless CONF_NOTIFICATIONS_ENABLED is set; re-evaluated on every
    # reload (options edits reload the entry via _async_reload).
    await async_setup_notifications(hass, entry, coordinator)

    return True


async def _async_reload(hass: HomeAssistant, entry: PlantCareConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PlantCareConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
