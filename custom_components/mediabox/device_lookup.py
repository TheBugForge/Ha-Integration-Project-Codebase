"""Shared device-to-config-entry resolution for the Mediabox integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


def resolve_entry_id(hass: HomeAssistant, device_id: str) -> str:
    """Resolve a device_id to the matching mediabox config entry_id.

    Raises HomeAssistantError if the device doesn't exist or doesn't belong
    to this integration.
    """
    from homeassistant.exceptions import HomeAssistantError

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if device is None:
        raise HomeAssistantError(f"Unknown device: {device_id}")

    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.domain == DOMAIN:
            return entry_id

    raise HomeAssistantError(
        f"Device {device_id} is not a Mediabox device"
    )
