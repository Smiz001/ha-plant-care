"""Config + options flow for Plant Care."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NOTIFY_TARGET,
    CONF_REMINDER_TIME,
    DEFAULT_REMINDER_TIME,
    DOMAIN,
)


class PlantCareConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance hub flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Plant Care", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PlantCareOptionsFlow()


class PlantCareOptionsFlow(OptionsFlow):
    """Hub-wide options: reminder time + optional notify target."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_REMINDER_TIME,
                    default=opts.get(CONF_REMINDER_TIME, DEFAULT_REMINDER_TIME),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_NOTIFY_TARGET,
                    default=opts.get(CONF_NOTIFY_TARGET, ""),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
