"""Config flow for Mediabox integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow


class MediaboxConfigFlow(ConfigFlow, domain="mediabox"):
    """Handle a config flow for Mediabox."""
