"""The Mediabox integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MediaboxApiClient
from .const import CONF_ADDRESS, CONF_API_KEY, DOMAIN, PLATFORMS
from .pointer_connection import PersistentPointerConnection
from .pointer_websocket import async_register_pointer_command
from .services import async_setup_services, async_unload_services
from .sse_listener import MediaboxSseListener


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Mediabox domain (runs once, not per entry)."""
    await async_setup_services(hass)
    async_register_pointer_command(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mediabox from a config entry."""
    session = async_get_clientsession(hass)
    address = entry.data[CONF_ADDRESS]
    api_key = entry.data[CONF_API_KEY]

    client = MediaboxApiClient(session, address, api_key)
    sse_listener = MediaboxSseListener(session, address, api_key)
    pointer_conn = PersistentPointerConnection(session, address, api_key)

    await sse_listener.async_start()
    await pointer_conn.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": client,
        "sse_listener": sse_listener,
        "pointer_connection": pointer_conn,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        sse_listener: MediaboxSseListener = hass.data[DOMAIN][entry.entry_id][
            "sse_listener"
        ]
        pointer_conn: PersistentPointerConnection = hass.data[DOMAIN][
            entry.entry_id
        ]["pointer_connection"]
        await sse_listener.async_stop()
        await pointer_conn.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id)
        async_unload_services(hass)

    return unload_ok
