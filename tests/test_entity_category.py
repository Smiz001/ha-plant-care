from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.helpers import setup_one_plant_with_treatment


async def test_entity_categories(hass: HomeAssistant):
    entry, sid = await setup_one_plant_with_treatment(hass)
    reg = er.async_get(hass)

    def cat(platform, suffix):
        eid = reg.async_get_entity_id(platform, "plant_care_scheduler", f"{sid}_{suffix}")
        assert eid, f"missing {platform} {suffix}"
        return reg.async_get(eid).entity_category

    # CONFIG: intervals
    assert cat("number", "water_interval") == EntityCategory.CONFIG
    assert cat("number", "feed_interval") == EntityCategory.CONFIG
    # DIAGNOSTIC: derived numbers
    assert cat("sensor", "days_to_water") == EntityCategory.DIAGNOSTIC
    assert cat("sensor", "days_to_treatment") == EntityCategory.DIAGNOSTIC
    assert cat("sensor", "treatments_left") == EntityCategory.DIAGNOSTIC
    # PRIMARY (no category): the actionable + status entities
    assert cat("binary_sensor", "needs_water") is None
    assert cat("date", "next_water") is None
    assert cat("button", "watered") is None
