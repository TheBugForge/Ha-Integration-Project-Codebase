"""Thin async REST client for the Mediabox backend."""

from __future__ import annotations

from urllib.parse import quote

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=5)


class MediaboxApiError(Exception):
    """Raised on network failure, timeout, or an unexpected non-2xx response."""


class MediaboxAuthError(MediaboxApiError):
    """Raised specifically on a 401 from an authenticated call."""


class MediaboxApiClient:
    """Async HTTP client wrapping the Mediabox backend REST surface."""

    def __init__(
        self, session: aiohttp.ClientSession, address: str, api_key: str
    ) -> None:
        self._session = session
        self._base_url = f"http://{address}"
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._api_key}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        auth: bool = True,
    ) -> aiohttp.ClientResponse:
        url = f"{self._base_url}{path}"
        headers = self._headers() if auth else {}
        try:
            resp = await self._session.request(
                method, url, headers=headers, timeout=TIMEOUT
            )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise MediaboxApiError(str(exc)) from exc

        if resp.status == 401 and auth:
            raise MediaboxAuthError(f"401 Unauthorized: {url}")

        if resp.status == 401 and not auth:
            return resp

        if resp.status < 200 or resp.status >= 300:
            raise MediaboxApiError(f"{resp.status} from {url}")

        return resp

    async def check_health(self, with_key: bool) -> bool:
        """Check backend health.

        with_key=False sends no X-Api-Key header (pure reachability check).
        with_key=True sends the key and returns True on 200, False on 401.
        """
        try:
            resp = await self._request("GET", "/health", auth=with_key)
        except MediaboxAuthError:
            return False
        if resp.status == 200:
            return True
        raise MediaboxApiError(f"{resp.status} from health check")

    async def get_apps(self) -> list[dict]:
        """Return the list of app tile summaries."""
        resp = await self._request("GET", "/apps")
        return await resp.json()  # type: ignore[return-value]

    async def switch_app(self, app_name: str) -> None:
        """Switch to the named app."""
        encoded = quote(app_name, safe="")
        await self._request("POST", f"/switch/{encoded}")

    async def set_text(self, text: str) -> None:
        """Send text to the backend (full-state replacement)."""
        encoded = quote(text, safe="")
        await self._request("POST", f"/type/{encoded}")

    async def get_keys(self) -> list[str]:
        """Return the list of available key names."""
        resp = await self._request("GET", "/keys")
        return await resp.json()  # type: ignore[return-value]

    async def get_actions(self) -> list[str]:
        """Return the list of available action names."""
        resp = await self._request("GET", "/actions")
        return await resp.json()  # type: ignore[return-value]

    async def send_key(self, key_name: str) -> None:
        """Send a key press."""
        encoded = quote(key_name, safe="")
        await self._request("POST", f"/key/{encoded}")

    async def send_action(self, action_name: str) -> None:
        """Send an action."""
        encoded = quote(action_name, safe="")
        await self._request("POST", f"/action/{encoded}")
