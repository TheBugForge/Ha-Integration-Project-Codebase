"""Tests for the Mediabox text entity."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mediabox.api import MediaboxApiError
from custom_components.mediabox.const import DOMAIN


@pytest.fixture()
def entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Mediabox",
        data={
            "address": "192.168.1.100:3000",
            "api_key": "test-key",
            "name": "Test Mediabox",
        },
        unique_id="192.168.1.100:3000",
    )


async def test_set_value_forwards_exact_string_to_api(hass, entry) -> None:
    entry.add_to_hass(hass)

    mock_client = AsyncMock()
    mock_client.set_text = AsyncMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": mock_client}

    from custom_components.mediabox.text import async_setup_entry

    entities = []
    await async_setup_entry(hass, entry, lambda e, **kw: entities.extend(e))

    await entities[0].async_set_value("hello world")
    mock_client.set_text.assert_called_once_with("hello world")


async def test_set_value_propagates_api_failure(hass, entry) -> None:
    entry.add_to_hass(hass)

    mock_client = AsyncMock()
    mock_client.set_text = AsyncMock(side_effect=MediaboxApiError("500 from backend"))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": mock_client}

    from custom_components.mediabox.text import async_setup_entry

    entities = []
    await async_setup_entry(hass, entry, lambda e, **kw: entities.extend(e))

    with pytest.raises(MediaboxApiError, match="500 from backend"):
        await entities[0].async_set_value("test")


async def test_entity_linked_to_correct_device(hass, entry) -> None:
    entry.add_to_hass(hass)

    mock_client = AsyncMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": mock_client}

    from custom_components.mediabox.text import async_setup_entry

    entities = []
    await async_setup_entry(hass, entry, lambda e, **kw: entities.extend(e))

    device_info = entities[0].device_info
    assert device_info is not None
    assert (DOMAIN, entry.entry_id) in device_info["identifiers"]
    assert device_info["name"] == "Test Mediabox"
