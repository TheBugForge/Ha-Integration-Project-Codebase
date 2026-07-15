"""Tests for the Mediabox send_key / send_action services."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mediabox.api import MediaboxApiError
from custom_components.mediabox.const import DOMAIN
from custom_components.mediabox.services import (
    async_setup_services,
    async_unload_services,
)


def _make_entry(entry_id: str, address: str, name: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=name,
        data={"address": address, "api_key": f"key-{entry_id}", "name": name},
        entry_id=entry_id,
        unique_id=address,
    )


def _register_entry(hass, entry, mock_client):
    """Register a fake config entry + API client in hass.data + device registry."""
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": mock_client,
    }
    dev_reg = dr.async_get(hass)
    return dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )


async def test_send_key_routes_to_correct_device_api_client(hass: HomeAssistant) -> None:
    entry_a = _make_entry("entry-a", "192.168.1.10:3000", "Living Room")
    entry_b = _make_entry("entry-b", "192.168.1.20:3000", "Bedroom")

    client_a = AsyncMock()
    client_b = AsyncMock()

    device_a = _register_entry(hass, entry_a, client_a)
    device_b = _register_entry(hass, entry_b, client_b)

    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        "send_key",
        {"device_id": device_b.id, "key": "Play"},
        blocking=True,
    )

    client_b.send_key.assert_called_once_with("Play")
    client_a.send_key.assert_not_called()

    async_unload_services(hass)


async def test_send_action_routes_to_correct_device_api_client(hass: HomeAssistant) -> None:
    entry_a = _make_entry("entry-a", "192.168.1.10:3000", "Living Room")
    entry_b = _make_entry("entry-b", "192.168.1.20:3000", "Bedroom")

    client_a = AsyncMock()
    client_b = AsyncMock()

    device_a = _register_entry(hass, entry_a, client_a)
    _register_entry(hass, entry_b, client_b)

    await async_setup_services(hass)

    await hass.services.async_call(
        DOMAIN,
        "send_action",
        {"device_id": device_a.id, "action": "Pause"},
        blocking=True,
    )

    client_a.send_action.assert_called_once_with("Pause")
    client_b.send_action.assert_not_called()

    async_unload_services(hass)


async def test_send_key_unknown_device_id_raises_home_assistant_error(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry("entry-1", "192.168.1.10:3000", "Living Room")
    _register_entry(hass, entry, AsyncMock())

    await async_setup_services(hass)

    with pytest.raises(HomeAssistantError, match="Unknown device"):
        await hass.services.async_call(
            DOMAIN,
            "send_key",
            {"device_id": "nonexistent_device_id", "key": "Up"},
            blocking=True,
        )

    async_unload_services(hass)


async def test_send_key_backend_failure_raises_home_assistant_error_not_raw_exception(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry("entry-1", "192.168.1.10:3000", "Living Room")
    mock_client = AsyncMock()
    mock_client.send_key = AsyncMock(side_effect=MediaboxApiError("500 Internal Server Error"))
    device = _register_entry(hass, entry, mock_client)

    await async_setup_services(hass)

    with pytest.raises(HomeAssistantError, match="500 Internal Server Error"):
        await hass.services.async_call(
            DOMAIN,
            "send_key",
            {"device_id": device.id, "key": "Play"},
            blocking=True,
        )

    async_unload_services(hass)


async def test_services_registered_once_with_multiple_entries(hass: HomeAssistant) -> None:
    entry_a = _make_entry("entry-a", "192.168.1.10:3000", "Living Room")
    entry_b = _make_entry("entry-b", "192.168.1.20:3000", "Bedroom")

    _register_entry(hass, entry_a, AsyncMock())
    _register_entry(hass, entry_b, AsyncMock())

    await async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, "send_key")
    assert hass.services.has_service(DOMAIN, "send_action")

    # Calling again should not fail or duplicate
    await async_setup_services(hass)

    async_unload_services(hass)


async def test_services_unregistered_only_when_last_entry_removed(hass: HomeAssistant) -> None:
    entry_a = _make_entry("entry-a", "192.168.1.10:3000", "Living Room")
    entry_b = _make_entry("entry-b", "192.168.1.20:3000", "Bedroom")

    _register_entry(hass, entry_a, AsyncMock())
    _register_entry(hass, entry_b, AsyncMock())

    await async_setup_services(hass)
    assert hass.services.has_service(DOMAIN, "send_key")

    # Simulate removing one entry (but another still exists)
    # async_unload_services checks hass.config_entries.async_entries(DOMAIN),
    # so we mock it to return one remaining entry.
    with patch.object(
        hass.config_entries, "async_entries", return_value=[entry_b]
    ):
        hass.data[DOMAIN].pop(entry_a.entry_id)
        async_unload_services(hass)
        assert hass.services.has_service(DOMAIN, "send_key")

    # Now no entries remain — services should be unregistered
    with patch.object(
        hass.config_entries, "async_entries", return_value=[]
    ):
        hass.data[DOMAIN].pop(entry_b.entry_id)
        async_unload_services(hass)
        assert not hass.services.has_service(DOMAIN, "send_key")
        assert not hass.services.has_service(DOMAIN, "send_action")
