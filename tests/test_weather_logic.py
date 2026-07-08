from custom_components.plant_care_scheduler.models import heat_factor, heat_shift, is_rainy, PlantConfig


def test_heat_factor_hot_cold_clamp():
    assert heat_factor(25) == 1.0
    assert round(heat_factor(35), 3) == 0.7
    assert heat_factor(100) == 0.6
    assert heat_factor(-100) == 1.2


def test_heat_shift_sign():
    assert heat_shift(10, 35) == 3     # hot -> ~3 days earlier
    assert heat_shift(10, 25) == 0
    assert heat_shift(10, 15) == -2    # factor 1.3 clamped to 1.2 -> round(10*(1-1.2)) = -2


def test_is_rainy():
    assert is_rainy("rainy", 0) is True
    assert is_rainy("sunny", 5) is True
    assert is_rainy("sunny", 0) is False
    assert is_rainy("sunny", None) is False


def test_weather_flags_default_false():
    cfg = PlantConfig.from_data({"name": "X"})
    assert cfg.weather_enabled is False and cfg.rain_skip is False
