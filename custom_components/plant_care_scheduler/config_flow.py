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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.util import dt as dt_util

from .const import (
    CHANNEL_MOBILE_APP,
    CHANNEL_TELEGRAM,
    CONF_EMOJI,
    CONF_FEED_INTERVAL,
    CONF_FEEDING_ENABLED,
    CONF_MOBILE_APP_SERVICE,
    CONF_MOISTURE_SENSOR,
    CONF_MOISTURE_THRESHOLD,
    CONF_NAME,
    CONF_NEXT_FEED,
    CONF_NEXT_TREATMENT,
    CONF_NEXT_WATER,
    CONF_NOTIFICATIONS_ENABLED,
    CONF_NOTIFY_CHANNEL,
    CONF_RAIN_SKIP,
    CONF_REMINDER_TIME,
    CONF_SCHEMA_VERSION,
    CONF_TELEGRAM_CHAT_ID,
    CONF_TELEGRAM_CONFIG_ENTRY,
    CONF_TREATMENT_INTERVAL,
    CONF_TREATMENT_NAME,
    CONF_TREATMENT_UNTIL,
    CONF_TREATMENTS_LEFT,
    CONF_WATER_INTERVAL,
    CONF_WEATHER_ENABLED,
    CONF_WEATHER_ENTITY,
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
        vol.Optional(
            CONF_FEEDING_ENABLED,
            default=d.get(CONF_FEEDING_ENABLED, True),
        ): selector.BooleanSelector(),
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
        vol.Optional(
            CONF_WEATHER_ENABLED,
            default=d.get(CONF_WEATHER_ENABLED, False),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_RAIN_SKIP,
            default=d.get(CONF_RAIN_SKIP, False),
        ): selector.BooleanSelector(),
    }
    return vol.Schema(schema)


def _req_date(key: str, defaults: dict[str, Any]) -> vol.Required:
    """Required DateSelector field; only attach a default if one is known."""
    val = defaults.get(key)
    if val is None:
        return vol.Required(key)
    return vol.Required(key, default=val)


# (platform, unique_id suffix) of each per-plant feed entity.
_FEED_ENTITIES = (
    ("number", "feed_interval"),
    ("date", "next_feed"),
    ("sensor", "days_to_feed"),
    ("binary_sensor", "needs_feed"),
    ("button", "fed"),
)


def _remove_feed_entities(hass: HomeAssistant, subentry_id: str) -> None:
    """Unregister this plant's feed entities (used when feeding is disabled)."""
    reg = er.async_get(hass)
    for platform, suffix in _FEED_ENTITIES:
        eid = reg.async_get_entity_id(platform, DOMAIN, f"{subentry_id}_{suffix}")
        if eid:
            reg.async_remove(eid)


# (platform, unique_id suffix) of each per-plant treatment entity.
_TREATMENT_ENTITIES = (
    ("binary_sensor", "needs_treatment"),
    ("sensor", "days_to_treatment"),
    ("sensor", "treatments_left"),
    ("date", "next_treatment"),
    ("button", "mark_treated"),
)


def _remove_treatment_entities(hass: HomeAssistant, subentry_id: str) -> None:
    """Unregister this plant's treatment entities (used when a course is stopped)."""
    reg = er.async_get(hass)
    for platform, suffix in _TREATMENT_ENTITIES:
        eid = reg.async_get_entity_id(platform, DOMAIN, f"{subentry_id}_{suffix}")
        if eid:
            reg.async_remove(eid)


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
    """Hub-wide options: reminder time + built-in notification settings."""

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
                    CONF_NOTIFICATIONS_ENABLED,
                    default=opts.get(CONF_NOTIFICATIONS_ENABLED, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_NOTIFY_CHANNEL,
                    default=opts.get(CONF_NOTIFY_CHANNEL, CHANNEL_TELEGRAM),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=CHANNEL_TELEGRAM, label="Telegram"
                            ),
                            selector.SelectOptionDict(
                                value=CHANNEL_MOBILE_APP, label="Mobile app"
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_TELEGRAM_CONFIG_ENTRY,
                    default=opts.get(CONF_TELEGRAM_CONFIG_ENTRY, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_TELEGRAM_CHAT_ID,
                    default=opts.get(CONF_TELEGRAM_CHAT_ID, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_MOBILE_APP_SERVICE,
                    default=opts.get(CONF_MOBILE_APP_SERVICE, ""),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_WEATHER_ENTITY,
                    default=opts.get(CONF_WEATHER_ENTITY, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
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
                CONF_FEEDING_ENABLED: bool(user_input.get(CONF_FEEDING_ENABLED, True)),
                CONF_MOISTURE_SENSOR: user_input.get(CONF_MOISTURE_SENSOR) or None,
                CONF_MOISTURE_THRESHOLD: user_input.get(CONF_MOISTURE_THRESHOLD),
                CONF_WEATHER_ENABLED: bool(user_input.get(CONF_WEATHER_ENABLED, False)),
                CONF_RAIN_SKIP: bool(user_input.get(CONF_RAIN_SKIP, False)),
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
                CONF_FEEDING_ENABLED: bool(user_input.get(CONF_FEEDING_ENABLED, True)),
                CONF_MOISTURE_SENSOR: user_input.get(CONF_MOISTURE_SENSOR) or None,
                CONF_MOISTURE_THRESHOLD: user_input.get(CONF_MOISTURE_THRESHOLD),
                CONF_WEATHER_ENABLED: bool(user_input.get(CONF_WEATHER_ENABLED, False)),
                CONF_RAIN_SKIP: bool(user_input.get(CONF_RAIN_SKIP, False)),
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
                # next_treatment/treatments_left live in the Store, not in
                # subentry.data, so the form can't pre-fill them and submits them
                # blank on a plain re-save. Read the current Store values and use
                # them as defaults so editing an active course (rename, attach
                # sensor, ...) doesn't silently restart its schedule.
                snap = coord.snapshot(subentry.subentry_id, None, None)
                nt = user_input.get(CONF_NEXT_TREATMENT)
                left = user_input.get(CONF_TREATMENTS_LEFT)
                await coord.async_set_treatment(
                    subentry.subentry_id,
                    date.fromisoformat(nt) if nt else (snap["next_treatment"] or dt_util.now().date()),
                    int(left) if left is not None else snap["treatments_left"],
                )
            else:
                for k in (
                    CONF_TREATMENT_NAME,
                    CONF_TREATMENT_INTERVAL,
                    CONF_TREATMENT_UNTIL,
                ):
                    new_data.pop(k, None)
                await coord.async_clear_treatment(subentry.subentry_id)
                # Like feeding: the platforms stop adding treatment entities on
                # reload, but HA leaves the already-registered ones as orphans
                # (auto-prune only happens on subentry removal). Remove them
                # explicitly so the device doesn't keep stale, unavailable entities.
                _remove_treatment_entities(self.hass, subentry.subentry_id)
            # Feeding turned off: the platforms will stop adding the feed
            # entities on reload, but HA leaves the already-registered ones as
            # orphans (auto-prune only happens on subentry removal). Remove them
            # explicitly so the device doesn't keep stale, unavailable entities.
            if not new_data[CONF_FEEDING_ENABLED]:
                _remove_feed_entities(self.hass, subentry.subentry_id)
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
                # Feeding toggle: a plain bool with a static True default so a
                # v0.3.x plant (no key) defaults to enabled. Pre-fills from
                # subentry.data via add_suggested_values_to_schema below.
                vol.Optional(
                    CONF_FEEDING_ENABLED, default=True
                ): selector.BooleanSelector(),
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
                # Weather toggles: plain bools with a static False default so a
                # plant without weather config stays off. Pre-fill from
                # subentry.data via add_suggested_values_to_schema below.
                vol.Optional(
                    CONF_WEATHER_ENABLED, default=False
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_RAIN_SKIP, default=False
                ): selector.BooleanSelector(),
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
