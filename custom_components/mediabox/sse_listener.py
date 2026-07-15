"""SSE-based push state listener for current-app events."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

BACKOFF_INITIAL = 1
BACKOFF_MAX = 30


class MediaboxSseListener:
    """Long-lived SSE connection that tracks the current app."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        address: str,
        api_key: str,
    ) -> None:
        self._session = session
        self._base_url = f"http://{address}"
        self._api_key = api_key
        self.current_app: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task[None] | None = None
        self._stopped = False

    def async_add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def _unsubscribe() -> None:
            try:
                self._listeners.remove(callback)
            except ValueError:
                pass

        return _unsubscribe

    def _notify_listeners(self) -> None:
        for cb in self._listeners:
            cb()

    async def async_start(self) -> None:
        self._stopped = False
        self._task = asyncio.create_task(self._run())

    async def async_stop(self) -> None:
        self._stopped = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        backoff = BACKOFF_INITIAL
        while not self._stopped:
            try:
                await self._connect_once()
                backoff = BACKOFF_INITIAL
            except asyncio.CancelledError:
                return
            except Exception:
                if self._stopped:
                    return
                _LOGGER.warning(
                    "SSE connection lost, reconnecting in %ss", backoff
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    return
                backoff = min(backoff * 2, BACKOFF_MAX)

    async def _connect_once(self) -> None:
        url = f"{self._base_url}/events/current-app"
        async with self._session.get(
            url, headers={"X-Api-Key": self._api_key}
        ) as resp:
            resp.raise_for_status()
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n\r")
                if line.startswith("data: "):
                    app_name = line[6:]
                    self.current_app = app_name
                    self._notify_listeners()
