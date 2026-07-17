"""Constants for the Mediabox integration."""

from homeassistant.const import Platform

DOMAIN = "mediabox"

CONF_ADDRESS = "address"
CONF_API_KEY = "api_key"
CONF_NAME = "name"

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.TEXT]

# The launcher app always exists on the backend (DD-01 — "always active by
# default," never a real Idle state) but is deliberately excluded from
# GET /apps (backend task-03c's Hidden flag) since that endpoint feeds the
# box's own tile grid, not this integration. The select entity's options
# list needs it added back explicitly, or the entity shows "unknown"
# whenever the box is actually at its home screen.
LAUNCHER_APP_NAME = "launcher"
