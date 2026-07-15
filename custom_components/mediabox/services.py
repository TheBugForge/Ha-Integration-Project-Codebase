"""Custom services for the Mediabox integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .api import MediaboxApiError, MediaboxAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICES = {"send_key", "send_action"}


def _resolve_api_client(hass: HomeAssistant, device_id: str):
    """Resolve a device_id to the matching MediaboxApiClient.

    Raises HomeAssistantError if the device doesn't exist or doesn't belong
    to this integration.
    """
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if device is None:
        raise HomeAssistantError(f"Unknown device: {device_id}")

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.domain == DOMAIN:
            return hass.data[DOMAIN][entry_id]["api"]

    raise HomeAssistantError(
        f"Device {device_id} is not a Mediabox device"
    )


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register the send_key and send_action services (called once from async_setup)."""

    async def _handle_send_key(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        key: str = call.data["key"]
        client = _resolve_api_client(hass, device_id)
        try:
            await client.send_key(key)
        except (MediaboxApiError, MediaboxAuthError) as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def _handle_send_action(call: ServiceCall) -> None:
        device_id: str = call.data["device_id"]
        action: str = call.data["action"]
        client = _resolve_api_client(hass, device_id)
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
