"""Select entity for current-app / app-switching."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, LAUNCHER_APP_NAME
from .sse_listener import MediaboxSseListener


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Mediabox select entity."""
    client = hass.data[DOMAIN][entry.entry_id]["api"]
    sse_listener: MediaboxSseListener = hass.data[DOMAIN][entry.entry_id][
        "sse_listener"
    ]

    apps = await client.get_apps()
    options = [app["name"] for app in apps]
    # GET /apps deliberately excludes the launcher (hidden from the box's own
    # tile grid) — but it's still a real, always-switchable app, and the
    # current-app SSE stream reports it whenever the box is at its home
    # screen. Add it back so the entity can both display and select it.
    if LAUNCHER_APP_NAME not in options:
        options.append(LAUNCHER_APP_NAME)

    async_add_entities(
        [MediaboxAppSelect(entry, client, sse_listener, options)],
    )


class MediaboxAppSelect(SelectEntity):
    """Select entity for switching the current app."""

    _attr_has_entity_name = True
    _attr_name = "Current App"

    def __init__(
        self,
        entry: ConfigEntry,
        client,
        sse_listener: MediaboxSseListener,
        options: list[str],
    ) -> None:
        self._client = client
        self._sse_listener = sse_listener
        self._attr_unique_id = f"{entry.entry_id}_current_app"
        self._attr_options = options
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_NAME],
            configuration_url=f"http://{entry.data[CONF_ADDRESS]}",
        )
        self._unsubscribe: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        self._unsubscribe = self._sse_listener.async_add_listener(
            self._handle_update
        )
        self._handle_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    def _handle_update(self) -> None:
        self._attr_current_option = self._sse_listener.current_app
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        await self._client.switch_app(option)
