"""Entity ids must be English-style regardless of the HA system language."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.plant_care_scheduler.const import DOMAIN
from tests.helpers import setup_one_plant_with_treatment


async def test_entity_ids_are_language_independent(hass: HomeAssistant):
    hass.config.language = "ru"  # simulate a Russian HA
    entry, sid = await setup_one_plant_with_treatment(hass)
    reg = er.async_get(hass)
    # unique_id (stable, code-defined) -> entity_id (must stay English-style)
    cases = {
        ("number", f"{sid}_water_interval"): "_water_interval",
        ("number", f"{sid}_feed_interval"): "_feed_interval",
        ("date", f"{sid}_next_water"): "_next_watering",
        ("date", f"{sid}_next_feed"): "_next_feeding",
        ("date", f"{sid}_next_treatment"): "_next_treatment",
        ("sensor", f"{sid}_days_to_water"): "_days_to_watering",
        ("sensor", f"{sid}_days_to_feed"): "_days_to_feeding",
        ("sensor", f"{sid}_days_to_treatment"): "_days_to_treatment",
        ("sensor", f"{sid}_treatments_left"): "_treatments_left",
        ("binary_sensor", f"{sid}_needs_water"): "_needs_watering",
        ("binary_sensor", f"{sid}_needs_feed"): "_needs_feeding",
        ("binary_sensor", f"{sid}_needs_treatment"): "_needs_treatment",
        ("button", f"{sid}_watered"): "_mark_watered",
        ("button", f"{sid}_fed"): "_mark_fed",
        ("button", f"{sid}_mark_treated"): "_mark_treated",
    }
    for (platform, uid), suffix in cases.items():
        eid = reg.async_get_entity_id(platform, DOMAIN, uid)
        assert eid is not None, f"missing entity for unique_id {uid}"
        assert eid.endswith(suffix), f"{uid}: entity_id {eid} should end with {suffix}"
