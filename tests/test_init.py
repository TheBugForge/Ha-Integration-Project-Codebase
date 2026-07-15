"""Tests for the Mediabox integration __init__ module."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mediabox.const import DOMAIN


async def test_setup_and_unload_entry_succeeds(hass: HomeAssistant) -> None:
    """Test that async_setup_entry and async_unload_entry both succeed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Mediabox",
        data={
            "address": "192.168.1.100",
            "api_key": "test-key",
            "name": "Test Mediabox",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.entry_id not in hass.data[DOMAIN]
