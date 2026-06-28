from datetime import date

from custom_components.plant_care.models import (
    PlantConfig,
    days_until,
    is_calendar_due,
    is_moisture_due,
    next_after_action,
)


def test_plant_config_from_data_defaults():
    cfg = PlantConfig.from_data({"name": "Жасмин"})
    assert cfg.name == "Жасмин"
    assert cfg.emoji == "🌱"
    assert cfg.moisture_sensor is None
    assert cfg.moisture_threshold is None


def test_plant_config_non_numeric_threshold_is_none():
    # A non-numeric threshold must not raise; it falls back to None.
    cfg = PlantConfig.from_data({"name": "Жасмин", "moisture_threshold": "abc"})
    assert cfg.moisture_threshold is None


def test_days_until():
    assert days_until(date(2026, 7, 1), date(2026, 6, 28)) == 3
    assert days_until(date(2026, 6, 28), date(2026, 6, 28)) == 0
    assert days_until(date(2026, 6, 26), date(2026, 6, 28)) == -2


def test_next_after_action():
    assert next_after_action(date(2026, 6, 28), 5) == date(2026, 7, 3)


def test_is_calendar_due():
    assert is_calendar_due(date(2026, 6, 28), date(2026, 6, 28)) is True
    assert is_calendar_due(date(2026, 6, 27), date(2026, 6, 28)) is True
    assert is_calendar_due(date(2026, 6, 29), date(2026, 6, 28)) is False


def test_is_moisture_due():
    assert is_moisture_due(30.0, 35.0) is True
    assert is_moisture_due(40.0, 35.0) is False
    assert is_moisture_due(None, 35.0) is False
    assert is_moisture_due(30.0, None) is False
