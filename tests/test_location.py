from types import SimpleNamespace

import pytest

from custom_components.hydro_monitor.core.location import (
    async_get_home_location,
)


@pytest.mark.asyncio
async def test_get_home_location():
    hass = SimpleNamespace(
        config=SimpleNamespace(
            latitude=48.1372,
            longitude=11.5756,
            elevation=520,
            location_name="Munich",
        )
    )

    location = await async_get_home_location(hass)

    assert location.latitude == 48.1372
    assert location.longitude == 11.5756
    assert location.elevation == 520
    assert location.name == "Munich"
