"""Tests for the Mediabox config flow."""

from __future__ import annotations

from unittest.mock import patch

import aiohttp
import pytest
from aioresponses import aioresponses
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mediabox.const import CONF_ADDRESS, CONF_API_KEY, CONF_NAME, DOMAIN

BASE = "http://192.168.1.50:3000"


@pytest.fixture(autouse=True)
def _mock_platforms():
    """Prevent platform setup during config flow tests."""
    with patch(
        "custom_components.mediabox.async_setup_entry", return_value=True
    ):
        yield


async def test_unreachable_address_shows_cannot_connect(hass) -> None:
    with aioresponses() as m:
        m.get(f"{BASE}/health", exception=aiohttp.ClientError("Connection refused"))
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "key", CONF_NAME: "Test"},
        )
        assert result2["type"] == "form"
        assert result2["errors"]["base"] == "cannot_connect"


async def test_wrong_key_shows_invalid_auth(hass) -> None:
    with aioresponses() as m:
        m.get(f"{BASE}/health", status=200)
        m.get(f"{BASE}/health", status=401)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "wrong", CONF_NAME: "Test"},
        )
        assert result2["type"] == "form"
        assert result2["errors"]["base"] == "invalid_auth"


async def test_valid_credentials_creates_entry(hass) -> None:
    with aioresponses() as m:
        m.get(f"{BASE}/health", status=200)
        m.get(f"{BASE}/health", status=200)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "good", CONF_NAME: "My Box"},
        )
        assert result2["type"] == "create_entry"
        assert result2["title"] == "My Box"
        assert result2["data"][CONF_ADDRESS] == "192.168.1.50:3000"
        assert result2["data"][CONF_API_KEY] == "good"


async def test_duplicate_address_aborts(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "k", CONF_NAME: "E"},
        unique_id="192.168.1.50:3000",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "k", CONF_NAME: "E"},
    )
    assert result2["type"] == "abort"
    assert result2["reason"] == "already_configured"


async def test_second_different_address_creates_independent_entry(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "k", CONF_NAME: "E"},
        unique_id="192.168.1.50:3000",
    )
    entry.add_to_hass(hass)

    with aioresponses() as m:
        m.get("http://192.168.1.51:3000/health", status=200)
        m.get("http://192.168.1.51:3000/health", status=200)
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADDRESS: "192.168.1.51:3000", CONF_API_KEY: "k2", CONF_NAME: "E2"},
        )
        assert result2["type"] == "create_entry"
        assert result2["data"][CONF_ADDRESS] == "192.168.1.51:3000"


async def test_cannot_connect_and_invalid_auth_produce_different_error_keys(hass) -> None:
    result_unreachable = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with aioresponses() as m:
        m.get(f"{BASE}/health", exception=aiohttp.ClientError("nope"))
        r1 = await hass.config_entries.flow.async_configure(
            result_unreachable["flow_id"],
            {CONF_ADDRESS: "192.168.1.50:3000", CONF_API_KEY: "k", CONF_NAME: "X"},
        )

    result_auth = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    with aioresponses() as m:
        m.get("http://192.168.1.50:3001/health", status=200)
        m.get("http://192.168.1.50:3001/health", status=401)
        r2 = await hass.config_entries.flow.async_configure(
            result_auth["flow_id"],
            {CONF_ADDRESS: "192.168.1.50:3001", CONF_API_KEY: "k", CONF_NAME: "Y"},
        )

    assert r1["errors"]["base"] == "cannot_connect"
    assert r2["errors"]["base"] == "invalid_auth"
    assert r1["errors"] != r2["errors"]
