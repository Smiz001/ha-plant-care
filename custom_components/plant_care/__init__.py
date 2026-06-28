"""The Plant Care integration."""
from __future__ import annotations

from datetime import date as date_cls, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FEED_INTERVAL,
    CONF_NEXT_FEED,
    CONF_NEXT_WATER,
    CONF_REMINDER_TIME,
    CONF_WATER_INTERVAL,
    DEFAULT_FEED_INTERVAL,
    DEFAULT_REMINDER_TIME,
    DEFAULT_WATER_INTERVAL,
    PLATFORMS,
)
from .coordinator import PlantCareCoordinator
from .notify_reminder import async_send_due_reminders

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

    rt = dt_util.parse_time(
        entry.options.get(CONF_REMINDER_TIME, DEFAULT_REMINDER_TIME)
    ) or dt_util.parse_time(DEFAULT_REMINDER_TIME)

    async def _daily(now):
        await async_send_due_reminders(hass, entry)

    entry.async_on_unload(
        async_track_time_change(hass, _daily, hour=rt.hour, minute=rt.minute, second=0)
    )

    return True


async def _async_reload(hass: HomeAssistant, entry: PlantCareConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: PlantCareConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
