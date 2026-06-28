from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.plant_care_scheduler.const import DOMAIN


async def test_user_creates_single_hub(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Plant Care Scheduler"

    # single_config_entry: a second attempt is aborted
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "single_instance_allowed"
