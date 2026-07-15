"""Tests for the Mediabox pointer websocket command."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mediabox.const import DOMAIN
from custom_components.mediabox.pointer_connection import PointerConnectionError
from custom_components.mediabox.pointer_websocket import handle_pointer


def _make_entry(entry_id: str, address: str, name: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=name,
        data={"address": address, "api_key": f"key-{entry_id}", "name": name},
        entry_id=entry_id,
        unique_id=address,
    )


def _register_entry(hass, entry, mock_pointer_conn=None):
    """Register a fake config entry + pointer connection in hass.data + device registry."""
    from homeassistant.helpers import device_registry as dr

    entry.add_to_hass(hass)
    conn = mock_pointer_conn or AsyncMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": AsyncMock(),
        "pointer_connection": conn,
    }
    dev_reg = dr.async_get(hass)
    return dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
    )


async def test_valid_move_command_relays_unmodified_to_correct_device(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry("entry-1", "192.168.1.10:3000", "Living Room")
    mock_conn = AsyncMock()
    device = _register_entry(hass, entry, mock_conn)

    connection = MagicMock()
    msg = {
        "id": 1,
        "type": "mediabox/pointer",
        "device_id": device.id,
        "gesture_type": "move",
        "dx": 15,
        "dy": -3,
    }

    await handle_pointer(hass, connection, msg)

    mock_conn.send_gesture.assert_called_once()
    sent = mock_conn.send_gesture.call_args[0][0]
    assert sent == {"type": "move", "dx": 15, "dy": -3}
    connection.send_result.assert_called_once_with(1)


async def test_start_and_end_commands_omit_dx_dy(hass: HomeAssistant) -> None:
    entry = _make_entry("entry-1", "192.168.1.10:3000", "Living Room")
    mock_conn = AsyncMock()
    device = _register_entry(hass, entry, mock_conn)

    connection = MagicMock()

    # Start
    msg_start = {
        "id": 1,
        "type": "mediabox/pointer",
        "device_id": device.id,
        "gesture_type": "start",
    }
    await handle_pointer(hass, connection, msg_start)

    sent_start = mock_conn.send_gesture.call_args_list[-1][0][0]
    assert sent_start == {"type": "start"}
    assert "dx" not in sent_start
    assert "dy" not in sent_start

    # End
    msg_end = {
        "id": 2,
        "type": "mediabox/pointer",
        "device_id": device.id,
        "gesture_type": "end",
    }
    await handle_pointer(hass, connection, msg_end)

    sent_end = mock_conn.send_gesture.call_args_list[-1][0][0]
    assert sent_end == {"type": "end"}
    assert "dx" not in sent_end
    assert "dy" not in sent_end

    connection.send_result.assert_called_with(2)


async def test_unknown_device_id_sends_error_not_exception(hass: HomeAssistant) -> None:
    entry = _make_entry("entry-1", "192.168.1.10:3000", "Living Room")
    _register_entry(hass, entry)

    connection = MagicMock()
    msg = {
        "id": 1,
        "type": "mediabox/pointer",
        "device_id": "nonexistent_device",
        "gesture_type": "move",
        "dx": 0,
        "dy": 0,
    }

    await handle_pointer(hass, connection, msg)

    connection.send_error.assert_called_once()
    error_args = connection.send_error.call_args[0]
    assert error_args[0] == 1  # msg id
    assert error_args[1] == "unknown_device"


async def test_command_while_backend_connection_down_sends_connection_unavailable_error(
    hass: HomeAssistant,
) -> None:
    entry = _make_entry("entry-1", "192.168.1.10:3000", "Living Room")
    mock_conn = AsyncMock()
    mock_conn.send_gesture = AsyncMock(
        side_effect=PointerConnectionError("not available")
    )
    device = _register_entry(hass, entry, mock_conn)

    connection = MagicMock()
    msg = {
        "id": 1,
        "type": "mediabox/pointer",
        "device_id": device.id,
        "gesture_type": "move",
        "dx": 5,
        "dy": 5,
    }

    await handle_pointer(hass, connection, msg)

    connection.send_error.assert_called_once()
    error_args = connection.send_error.call_args[0]
    assert error_args[0] == 1
    assert error_args[1] == "connection_unavailable"


async def test_two_devices_route_independently(hass: HomeAssistant) -> None:
    entry_a = _make_entry("entry-a", "192.168.1.10:3000", "Living Room")
    entry_b = _make_entry("entry-b", "192.168.1.20:3000", "Bedroom")

    conn_a = AsyncMock()
    conn_b = AsyncMock()

    device_a = _register_entry(hass, entry_a, conn_a)
    device_b = _register_entry(hass, entry_b, conn_b)

    connection = MagicMock()

    # Send to device B
    msg_b = {
        "id": 1,
        "type": "mediabox/pointer",
        "device_id": device_b.id,
        "gesture_type": "move",
        "dx": 10,
        "dy": 20,
    }
    await handle_pointer(hass, connection, msg_b)

    conn_b.send_gesture.assert_called_once()
    conn_a.send_gesture.assert_not_called()

    sent_b = conn_b.send_gesture.call_args[0][0]
    assert sent_b == {"type": "move", "dx": 10, "dy": 20}
    connection.send_result.assert_called_with(1)
