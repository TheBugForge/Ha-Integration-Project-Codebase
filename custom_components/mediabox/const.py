"""Constants for the Mediabox integration."""

from homeassistant.const import Platform

DOMAIN = "mediabox"

CONF_ADDRESS = "address"
CONF_API_KEY = "api_key"
CONF_NAME = "name"

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.TEXT]
