"""Optional daily reminder via any HA notify service."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .const import CONF_NOTIFY_TARGET
from .models import PlantConfig

_LOGGER = logging.getLogger(__name__)


async def async_send_due_reminders(hass: HomeAssistant, entry) -> None:
    target = (entry.options.get(CONF_NOTIFY_TARGET) or "").strip()
    if not target:
        return
    if "." not in target:
        _LOGGER.warning("plant_care notify target %r is not 'domain.service'", target)
        return
    domain, service = target.split(".", 1)
    if not domain or not service:
        _LOGGER.warning(
            "plant_care notify target %r is not 'domain.service'", target
        )
        return
    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        # One misbehaving plant must not silence reminders for the rest.
        try:
            cfg = PlantConfig.from_data(dict(subentry.data))
            snap = coordinator.snapshot(
                subentry.subentry_id, cfg.moisture_sensor, cfg.moisture_threshold
            )
            msgs = []
            if snap["needs_water"]:
                msgs.append(f"{cfg.emoji} Пора полить {cfg.name}")
            if snap["needs_feed"]:
                msgs.append(f"{cfg.emoji} Пора подкормить {cfg.name}")
            for message in msgs:
                await hass.services.async_call(
                    domain, service, {"message": message}, blocking=False
                )
        except Exception:  # noqa: BLE001 - resilience: keep notifying other plants
            _LOGGER.exception(
                "plant_care reminder failed for subentry %s", subentry.subentry_id
            )
            continue
