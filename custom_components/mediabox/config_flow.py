"""Config flow for Mediabox integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MediaboxApiClient, MediaboxApiError
from .const import CONF_ADDRESS, CONF_API_KEY, CONF_NAME, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDRESS): str,
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_NAME, default="Mediabox"): str,
    }
)


class MediaboxConfigFlow(ConfigFlow, domain="mediabox"):
    """Handle a config flow for Mediabox."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            api_key = user_input[CONF_API_KEY]

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = MediaboxApiClient(session, address, api_key)

            try:
                reachable = await client.check_health(with_key=False)
            except MediaboxApiError:
                errors["base"] = "cannot_connect"
            else:
                if not reachable:
                    errors["base"] = "cannot_connect"
                else:
                    key_ok = await client.check_health(with_key=True)
                    if not key_ok:
                        errors["base"] = "invalid_auth"
                    else:
                        return self.async_create_entry(
                            title=user_input[CONF_NAME],
                            data={
                                CONF_ADDRESS: address,
                                CONF_API_KEY: api_key,
                                CONF_NAME: user_input[CONF_NAME],
                            },
                        )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
