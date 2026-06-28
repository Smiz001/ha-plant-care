"""A v0.2.1 plant (no treatment fields) loads unchanged; no treatment entities."""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant


async def test_v021_plant_loads_with_no_treatment_entities(hass: HomeAssistant):
    # setup_one_plant builds a subentry WITHOUT any treatment_* keys — exactly
    # the v0.2.1 on-disk shape. It must load cleanly and keep all its original
    # entities, with their unique_ids unchanged (history/dashboard preserved).
    entry, sid = await setup_one_plant(hass)
    reg = er.async_get(hass)

    # Original v0.2.1 entities still present:
    for platform, suffix in (
        ("number", "water_interval"),
        ("number", "feed_interval"),
        ("date", "next_water"),
        ("date", "next_feed"),
        ("sensor", "days_to_water"),
        ("sensor", "days_to_feed"),
        ("binary_sensor", "needs_water"),
        ("binary_sensor", "needs_feed"),
    ):
        assert reg.async_get_entity_id(platform, "plant_care_scheduler", f"{sid}_{suffix}") is not None, (
            f"missing {platform}.{suffix}"
        )

    # NO treatment entities for a plant without a treatment:
    for platform, suffix in (
        ("binary_sensor", "needs_treatment"),
        ("sensor", "days_to_treatment"),
        ("sensor", "treatments_left"),
        ("date", "next_treatment"),
        ("button", "mark_treated"),
    ):
        assert reg.async_get_entity_id(platform, "plant_care_scheduler", f"{sid}_{suffix}") is None, (
            f"unexpected {platform}.{suffix}"
        )
