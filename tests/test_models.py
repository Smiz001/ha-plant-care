from datetime import date

from custom_components.plant_care_scheduler.models import (
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


def test_feeding_enabled_defaults_true_when_absent():
    cfg = PlantConfig.from_data({"name": "X"})  # v0.3.x format, no key
    assert cfg.feeding_enabled is True


def test_feeding_enabled_false_when_set():
    cfg = PlantConfig.from_data({"name": "X", "feeding_enabled": False})
    assert cfg.feeding_enabled is False


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


from datetime import date as _date
from custom_components.plant_care_scheduler.models import treatment_finished


def test_plant_config_treatment_fields():
    from custom_components.plant_care_scheduler.models import PlantConfig
    cfg = PlantConfig.from_data({
        "name": "Клубника", "treatment_name": "Фунгицид",
        "treatment_interval": 3, "treatment_until": "2026-07-15",
    })
    assert cfg.has_treatment is True
    assert cfg.treatment_interval == 3
    assert cfg.treatment_until == _date(2026, 7, 15)
    assert PlantConfig.from_data({"name": "Олива"}).has_treatment is False


def test_from_data_resilient_to_corrupt_treatment_fields():
    # Corrupt treatment_until / treatment_interval (e.g. hand-edited storage)
    # must not raise — from_data runs in every platform setup loop.
    cfg = PlantConfig.from_data({
        "name": "Клубника",
        "treatment_name": "Фунгицид",
        "treatment_interval": "abc",       # non-numeric
        "treatment_until": "not-a-date",   # non-ISO
    })
    assert cfg.has_treatment is True
    assert cfg.treatment_interval is None
    assert cfg.treatment_until is None


def test_from_data_parses_valid_treatment_fields():
    cfg = PlantConfig.from_data({
        "name": "Клубника",
        "treatment_name": "Фунгицид",
        "treatment_interval": "3",
        "treatment_until": "2026-07-15",
    })
    from datetime import date
    assert cfg.treatment_interval == 3
    assert cfg.treatment_until == date(2026, 7, 15)


def test_treatment_finished():
    t = _date(2026, 6, 28)
    assert treatment_finished(0, None, t) is True
    assert treatment_finished(2, None, t) is False
    assert treatment_finished(None, _date(2026, 6, 27), t) is True
    assert treatment_finished(None, _date(2026, 6, 30), t) is False
    assert treatment_finished(None, None, t) is False
