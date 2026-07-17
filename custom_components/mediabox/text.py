"""Text entity for search/type input."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADDRESS, CONF_NAME, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Mediabox text entity."""
    client = hass.data[DOMAIN][entry.entry_id]["api"]
    async_add_entities([MediaboxSearchText(entry, client)])


class MediaboxSearchText(TextEntity):
    """Text entity for sending search/type input to the backend."""

    _attr_has_entity_name = True
    _attr_name = "Search"
    _attr_mode = TextMode.TEXT

    def __init__(self, entry: ConfigEntry, client) -> None:
        self._client = client
        self._attr_unique_id = f"{entry.entry_id}_search"
        self._attr_native_value = ""
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_NAME],
            configuration_url=f"http://{entry.data[CONF_ADDRESS]}",
        )

    async def async_set_value(self, value: str) -> None:
        await self._client.set_text(value)
        self._attr_native_value = value
        self.async_write_ha_state()
