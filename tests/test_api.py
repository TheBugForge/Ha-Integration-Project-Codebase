"""Tests for the Mediabox REST API client."""

from __future__ import annotations

from unittest.mock import MagicMock

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.mediabox.api import (
    MediaboxApiClient,
    MediaboxApiError,
    MediaboxAuthError,
)

ADDRESS = "192.168.1.50:3000"
API_KEY = "test-secret-key"
BASE_URL = f"http://{ADDRESS}"


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _get_mock_key(url: str, method: str = "GET") -> tuple[str, str]:
    """Build the key that aioresponses uses internally."""
    from yarl import URL

    return (method, URL(url))


# ---------------------------------------------------------------------------
# check_health
# ---------------------------------------------------------------------------


async def test_check_health_no_key_sends_no_header() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.get(_url("/health"), status=200)
            await client.check_health(with_key=False)
            key = _get_mock_key(_url("/health"))
            req = m.requests[key][0]
            assert "X-Api-Key" not in req.kwargs.get("headers", {})


async def test_check_health_with_key_returns_true_on_200() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.get(_url("/health"), status=200)
            assert await client.check_health(with_key=True) is True
            key = _get_mock_key(_url("/health"))
            req = m.requests[key][0]
            assert req.kwargs["headers"]["X-Api-Key"] == API_KEY


async def test_check_health_with_key_returns_false_on_401() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.get(_url("/health"), status=401)
            assert await client.check_health(with_key=True) is False


async def test_check_health_raises_on_connection_error() -> None:
    session = MagicMock(spec=aiohttp.ClientSession)
    session.request = MagicMock(side_effect=aiohttp.ClientError("boom"))
    client = MediaboxApiClient(session, ADDRESS, API_KEY)
    with pytest.raises(MediaboxApiError):
        await client.check_health(with_key=False)


# ---------------------------------------------------------------------------
# get_apps
# ---------------------------------------------------------------------------


async def test_get_apps_returns_parsed_list() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            apps = [{"name": "Plex"}, {"name": "Netflix"}]
            m.get(_url("/apps"), payload=apps, status=200)
            result = await client.get_apps()
            assert result == apps


# ---------------------------------------------------------------------------
# switch_app
# ---------------------------------------------------------------------------


async def test_switch_app_sends_correct_path() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.post(_url("/switch/Plex"), status=200)
            await client.switch_app("Plex")
            key = _get_mock_key(_url("/switch/Plex"), "POST")
            assert key in m.requests


# ---------------------------------------------------------------------------
# set_text
# ---------------------------------------------------------------------------


async def test_set_text_url_encodes_special_characters() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.post(_url("/type/hello%20world%2F"), status=200)
            await client.set_text("hello world/")
            key = _get_mock_key(_url("/type/hello%20world%2F"), "POST")
            assert key in m.requests


# ---------------------------------------------------------------------------
# get_keys / get_actions
# ---------------------------------------------------------------------------


async def test_get_keys_returns_parsed_list() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            keys = ["Up", "Down", "Enter"]
            m.get(_url("/keys"), payload=keys, status=200)
            assert await client.get_keys() == keys


async def test_get_actions_returns_parsed_list() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            actions = ["Play", "Pause"]
            m.get(_url("/actions"), payload=actions, status=200)
            assert await client.get_actions() == actions


# ---------------------------------------------------------------------------
# send_key / send_action error handling
# ---------------------------------------------------------------------------


async def test_send_key_raises_mediabox_auth_error_on_401() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.post(_url("/key/Up"), status=401)
            with pytest.raises(MediaboxAuthError):
                await client.send_key("Up")


async def test_send_action_raises_mediabox_api_error_on_500() -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            m.post(_url("/action/Play"), status=500)
            with pytest.raises(MediaboxApiError):
                await client.send_action("Play")


# ---------------------------------------------------------------------------
# Parametrized: every authenticated call sends X-Api-Key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "args", "path", "http_method"),
    [
        ("get_apps", (), "/apps", "GET"),
        ("get_keys", (), "/keys", "GET"),
        ("get_actions", (), "/actions", "GET"),
        ("switch_app", ("Plex",), "/switch/Plex", "POST"),
        ("set_text", ("hello",), "/type/hello", "POST"),
        ("send_key", ("Up",), "/key/Up", "POST"),
        ("send_action", ("Play",), "/action/Play", "POST"),
    ],
)
async def test_every_authenticated_call_sends_api_key_header(
    method: str,
    args: tuple,
    path: str,
    http_method: str,
) -> None:
    with aioresponses() as m:
        async with aiohttp.ClientSession() as session:
            client = MediaboxApiClient(session, ADDRESS, API_KEY)
            url = _url(path)
            if http_method == "GET":
                m.get(url, status=200)
            else:
                m.post(url, status=200)
            await getattr(client, method)(*args)
            key = _get_mock_key(url, http_method)
            req = m.requests[key][0]
            assert req.kwargs["headers"]["X-Api-Key"] == API_KEY
