"""The Mediabox integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MediaboxApiClient
from .const import CONF_ADDRESS, CONF_API_KEY, DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mediabox from a config entry."""
    session = async_get_clientsession(hass)
    client = MediaboxApiClient(
        session,
        entry.data[CONF_ADDRESS],
        entry.data[CONF_API_KEY],
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"api": client}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
