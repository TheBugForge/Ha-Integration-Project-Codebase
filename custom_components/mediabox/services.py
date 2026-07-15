"""Custom services for the Mediabox integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .api import MediaboxApiError, MediaboxAuthError
from .const import DOMAIN
from .device_lookup import resolve_entry_id

_LOGGER = logging.getLogger(__name__)

SERVICES = {"send_key", "send_action"}


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the send_key and send_action services (called once from async_setup)."""

    async def _handle_send_key(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        key: str = call.data["key"]
        entry_id = resolve_entry_id(hass, device_id)
        client = hass.data[DOMAIN][entry_id]["api"]
        try:
            await client.send_key(key)
        except (MediaboxApiError, MediaboxAuthError) as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def _handle_send_action(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        action: str = call.data["action"]
        entry_id = resolve_entry_id(hass, device_id)
        client = hass.data[DOMAIN][entry_id]["api"]
        try:
            await client.send_action(action)
        except (MediaboxApiError, MediaboxAuthError) as exc:
            raise HomeAssistantError(str(exc)) from exc

    hass.services.async_register(DOMAIN, "send_key", _handle_send_key)
    hass.services.async_register(DOMAIN, "send_action", _handle_send_action)


def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister services if no config entries remain."""
    remaining = hass.config_entries.async_entries(DOMAIN)
    if not remaining:
        for name in SERVICES:
            hass.services.async_remove(DOMAIN, name)
