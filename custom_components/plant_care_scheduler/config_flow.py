"""Config + options flow for Plant Care."""
from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EMOJI,
    CONF_FEED_INTERVAL,
    CONF_MOISTURE_SENSOR,
    CONF_MOISTURE_THRESHOLD,
    CONF_NAME,
    CONF_NEXT_FEED,
    CONF_NEXT_TREATMENT,
    CONF_NEXT_WATER,
    CONF_NOTIFY_TARGET,
    CONF_REMINDER_TIME,
    CONF_SCHEMA_VERSION,
    CONF_TREATMENT_INTERVAL,
    CONF_TREATMENT_NAME,
    CONF_TREATMENT_UNTIL,
    CONF_TREATMENTS_LEFT,
    CONF_WATER_INTERVAL,
    DEFAULT_EMOJI,
    DEFAULT_FEED_INTERVAL,
    DEFAULT_REMINDER_TIME,
    DEFAULT_TREATMENT_INTERVAL,
    DEFAULT_WATER_INTERVAL,
    DOMAIN,
    SCHEMA_VERSION,
    SUBENTRY_TYPE,
)

DEFAULT_MOISTURE_THRESHOLD = 35


def _opt(key: str, defaults: dict[str, Any]) -> vol.Optional:
    """vol.Optional with a default only when one is actually known.

    Selectors like EntitySelector/DateSelector reject ``None``, so an absent
    optional field must NOT carry ``default=None`` — it must simply be omitted
    from the submitted data (the handler reads it via ``.get()``).
    """
    val = defaults.get(key)
    if val is None:
        return vol.Optional(key)
    return vol.Optional(key, default=val)


def _plant_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Build the add/edit-plant form schema."""
    d = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=d.get(CONF_NAME, "")): selector.TextSelector(),
        vol.Optional(
            CONF_EMOJI, default=d.get(CONF_EMOJI, DEFAULT_EMOJI)
        ): selector.TextSelector(),
        vol.Required(
            CONF_WATER_INTERVAL,
            default=d.get(CONF_WATER_INTERVAL, DEFAULT_WATER_INTERVAL),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_FEED_INTERVAL,
            default=d.get(CONF_FEED_INTERVAL, DEFAULT_FEED_INTERVAL),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        _req_date(CONF_NEXT_WATER, d): selector.DateSelector(),
        _req_date(CONF_NEXT_FEED, d): selector.DateSelector(),
        _opt(CONF_MOISTURE_SENSOR, d): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="moisture")
        ),
        vol.Optional(
            CONF_MOISTURE_THRESHOLD,
            default=d.get(CONF_MOISTURE_THRESHOLD, DEFAULT_MOISTURE_THRESHOLD),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=100, mode=selector.NumberSelectorMode.BOX
            )
        ),
    }
    return vol.Schema(schema)


def _req_date(key: str, defaults: dict[str, Any]) -> vol.Required:
    """Required DateSelector field; only attach a default if one is known."""
    val = defaults.get(key)
    if val is None:
        return vol.Required(key)
    return vol.Required(key, default=val)


class PlantCareConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-instance hub flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Plant Care Scheduler", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PlantCareOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_TYPE: PlantSubentryFlowHandler}


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


class PlantSubentryFlowHandler(ConfigSubentryFlow):
    """Add a single plant."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_EMOJI: user_input.get(CONF_EMOJI) or DEFAULT_EMOJI,
                CONF_WATER_INTERVAL: int(user_input[CONF_WATER_INTERVAL]),
                CONF_FEED_INTERVAL: int(user_input[CONF_FEED_INTERVAL]),
                CONF_NEXT_WATER: user_input[CONF_NEXT_WATER],
                CONF_NEXT_FEED: user_input[CONF_NEXT_FEED],
                CONF_MOISTURE_SENSOR: user_input.get(CONF_MOISTURE_SENSOR) or None,
                CONF_MOISTURE_THRESHOLD: user_input.get(CONF_MOISTURE_THRESHOLD),
                CONF_SCHEMA_VERSION: SCHEMA_VERSION,
            }
            return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(step_id="user", data_schema=_plant_schema())

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit name/emoji and attach/replace the moisture sensor.

        Only name, emoji, moisture sensor + threshold are editable here;
        intervals and next-dates are owned by the number/date entities, so we
        MERGE into the existing data to preserve everything else.
        """
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            new_data = {
                **subentry.data,
                CONF_NAME: user_input[CONF_NAME],
                CONF_EMOJI: user_input.get(CONF_EMOJI) or DEFAULT_EMOJI,
                CONF_MOISTURE_SENSOR: user_input.get(CONF_MOISTURE_SENSOR) or None,
                CONF_MOISTURE_THRESHOLD: user_input.get(CONF_MOISTURE_THRESHOLD),
                CONF_SCHEMA_VERSION: SCHEMA_VERSION,
            }
            # Treatment: a non-empty name starts/edits a course; an empty (or
            # missing) name stops it. The schedule (next_treatment/left) lives
            # in the coordinator Store, the config (name/interval/until) in
            # subentry.data.
            t_name = (user_input.get(CONF_TREATMENT_NAME) or "").strip()
            coord = self._get_entry().runtime_data
            if t_name:
                new_data[CONF_TREATMENT_NAME] = t_name
                new_data[CONF_TREATMENT_INTERVAL] = int(
                    user_input.get(CONF_TREATMENT_INTERVAL)
                    or DEFAULT_TREATMENT_INTERVAL
                )
                new_data[CONF_TREATMENT_UNTIL] = (
                    user_input.get(CONF_TREATMENT_UNTIL) or None
                )
                nt = user_input.get(CONF_NEXT_TREATMENT)
                left = user_input.get(CONF_TREATMENTS_LEFT)
                await coord.async_set_treatment(
                    subentry.subentry_id,
                    date.fromisoformat(nt) if nt else dt_util.now().date(),
                    int(left) if left is not None else None,
                )
            else:
                for k in (
                    CONF_TREATMENT_NAME,
                    CONF_TREATMENT_INTERVAL,
                    CONF_TREATMENT_UNTIL,
                ):
                    new_data.pop(k, None)
                await coord.async_clear_treatment(subentry.subentry_id)
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                data=new_data,
                title=new_data[CONF_NAME],
            )

        d = subentry.data
        # Moisture fields carry NO default: a default would be re-injected by
        # voluptuous when the user clears the field, making detachment impossible.
        # Instead we pre-fill via suggested values, so submitting without the
        # field omits the key (-> user_input.get(...) is None -> detached).
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=d.get(CONF_NAME, "")
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_EMOJI, default=d.get(CONF_EMOJI, DEFAULT_EMOJI)
                ): selector.TextSelector(),
                vol.Optional(CONF_MOISTURE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="moisture"
                    )
                ),
                vol.Optional(CONF_MOISTURE_THRESHOLD): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=100, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                # Treatment fields: optional, pre-filled via suggested values
                # (same mechanism as moisture) so clearing the name stops the
                # course. Only the interval carries a static default.
                vol.Optional(CONF_TREATMENT_NAME): selector.TextSelector(),
                vol.Optional(
                    CONF_TREATMENT_INTERVAL, default=DEFAULT_TREATMENT_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=365, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_NEXT_TREATMENT): selector.DateSelector(),
                vol.Optional(CONF_TREATMENTS_LEFT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=99, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(CONF_TREATMENT_UNTIL): selector.DateSelector(),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(schema, subentry.data),
        )
