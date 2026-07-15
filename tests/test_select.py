"""Tests for the Mediabox select entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


async def test_options_populated_from_get_apps_at_setup(hass, entry) -> None:
    entry.add_to_hass(hass)

    mock_client = AsyncMock()
    mock_client.get_apps = AsyncMock(
        return_value=[{"name": "Plex"}, {"name": "Netflix"}]
    )

    mock_sse = MagicMock()
    mock_sse.current_app = None
    mock_sse.async_add_listener = MagicMock(return_value=lambda: None)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": mock_client,
        "sse_listener": mock_sse,
    }

    from custom_components.mediabox.select import async_setup_entry

    entities = []

    def _add_entities(new_entities, update=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, _add_entities)

    assert len(entities) == 1
    assert entities[0].options == ["Plex", "Netflix"]


async def test_current_option_reflects_sse_listener_state(hass, entry) -> None:
    entry.add_to_hass(hass)

    mock_client = AsyncMock()
    mock_client.get_apps = AsyncMock(return_value=[{"name": "Plex"}])

    mock_sse = MagicMock()
    mock_sse.current_app = "Plex"
    mock_sse.async_add_listener = MagicMock(return_value=lambda: None)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": mock_client,
        "sse_listener": mock_sse,
    }

    from custom_components.mediabox.select import async_setup_entry

    entities = []

    def _add_entities(new_entities, update=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, _add_entities)

    entity = entities[0]
    entity.async_write_ha_state = MagicMock()
    entity._handle_update()
    assert entity.current_option == "Plex"
    entity.async_write_ha_state.assert_called_once()


async def test_select_option_calls_switch_app_and_does_not_optimistically_update(
    hass, entry
) -> None:
    entry.add_to_hass(hass)

    mock_client = AsyncMock()
    mock_client.get_apps = AsyncMock(return_value=[{"name": "Plex"}])
    mock_client.switch_app = AsyncMock()

    mock_sse = MagicMock()
    mock_sse.current_app = None
    mock_sse.async_add_listener = MagicMock(return_value=lambda: None)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": mock_client,
        "sse_listener": mock_sse,
    }

    from custom_components.mediabox.select import async_setup_entry

    entities = []

    def _add_entities(new_entities, update=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, _add_entities)

    await entities[0].async_select_option("Plex")
    mock_client.switch_app.assert_called_once_with("Plex")
    assert entities[0].current_option is None
