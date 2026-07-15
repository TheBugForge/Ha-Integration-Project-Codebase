"""Registers the mediabox/pointer websocket_command."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .device_lookup import resolve_entry_id
from .pointer_connection import PointerConnectionError

POINTER_SCHEMA: dict = {
    vol.Required("type"): "mediabox/pointer",
    vol.Required("device_id"): cv.string,
    vol.Required("gesture_type"): vol.In(["start", "move", "end"]),
    vol.Optional("dx"): int,
    vol.Optional("dy"): int,
}


@websocket_api.websocket_command(POINTER_SCHEMA)
async def handle_pointer(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    device_id: str = msg["device_id"]
    gesture_type: str = msg["gesture_type"]

    try:
        entry_id = resolve_entry_id(hass, device_id)
    except Exception as exc:
        connection.send_error(msg["id"], "unknown_device", str(exc))
        return

    pointer_conn = hass.data[DOMAIN][entry_id].get("pointer_connection")
    if pointer_conn is None:
        connection.send_error(
            msg["id"],
            "connection_unavailable",
            "Pointer connection not initialized",
        )
        return

    payload: dict[str, Any] = {"type": gesture_type}
    if "dx" in msg:
        payload["dx"] = msg["dx"]
    if "dy" in msg:
        payload["dy"] = msg["dy"]

    try:
        await pointer_conn.send_gesture(payload)
    except PointerConnectionError as exc:
        connection.send_error(
            msg["id"], "connection_unavailable", str(exc)
        )
        return

    connection.send_result(msg["id"])


def async_register_pointer_command(hass: HomeAssistant) -> None:
    """Register the mediabox/pointer websocket command (domain-wide, once)."""
    websocket_api.async_register_command(hass, handle_pointer)
