"""Constants for the Plant Care integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "plant_care_scheduler"
PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.DATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
]

SUBENTRY_TYPE = "plant"
STORAGE_VERSION = 1
SCHEMA_VERSION = 1

# subentry.data keys (static config)
CONF_NAME = "name"
CONF_EMOJI = "emoji"
CONF_MOISTURE_SENSOR = "moisture_sensor"
CONF_MOISTURE_THRESHOLD = "moisture_threshold"
CONF_FEEDING_ENABLED = "feeding_enabled"
CONF_SCHEMA_VERSION = "schema_version"

# Store keys (live values) + add-plant seed fields
CONF_WATER_INTERVAL = "water_interval"
CONF_FEED_INTERVAL = "feed_interval"
CONF_NEXT_WATER = "next_water"
CONF_NEXT_FEED = "next_feed"

# hub options
CONF_REMINDER_TIME = "reminder_time"
CONF_NOTIFY_TARGET = "notify_target"

DEFAULT_EMOJI = "🌱"
DEFAULT_REMINDER_TIME = "09:00:00"
DEFAULT_WATER_INTERVAL = 5
DEFAULT_FEED_INTERVAL = 14

# treatment (subentry.data: name/interval/until ; Store: next_treatment/treatments_left)
CONF_TREATMENT_NAME = "treatment_name"
CONF_TREATMENT_INTERVAL = "treatment_interval"
CONF_TREATMENT_UNTIL = "treatment_until"
CONF_NEXT_TREATMENT = "next_treatment"
CONF_TREATMENTS_LEFT = "treatments_left"
DEFAULT_TREATMENT_INTERVAL = 7
