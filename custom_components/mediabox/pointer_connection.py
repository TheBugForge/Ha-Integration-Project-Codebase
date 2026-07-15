"""Persistent WebSocket connection to the backend's /pointer endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .sse_listener import BACKOFF_INITIAL, BACKOFF_MAX

_LOGGER = logging.getLogger(__name__)


class PointerConnectionError(Exception):
    """Raised when a gesture cannot be sent because the connection is down."""


class PersistentPointerConnection:
    """One per config entry — holds a single WS connection to backend /pointer."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        address: str,
        api_key: str,
    ) -> None:
        self._session = session
        self._url = f"ws://{address}/pointer"
        self._api_key = api_key
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._task: asyncio.Task[None] | None = None
        self._stopped = False
        self._started = asyncio.Event()

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
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

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
                    "Pointer connection lost, reconnecting in %ss", backoff
                )
                try:
                    await asyncio.sleep(backoff)
                except asyncio.CancelledError:
                    return
                backoff = min(backoff * 2, BACKOFF_MAX)

    async def _connect_once(self) -> None:
        self._ws = await self._session.ws_connect(
            self._url,
            headers={"X-Api-Key": self._api_key},
        )
        self._started.set()
        # Keep the connection alive — read frames until closed or error.
        async for msg in self._ws:
            pass

    async def send_gesture(self, msg: dict[str, Any]) -> None:
        """Send a gesture frame over the WebSocket.

        Raises PointerConnectionError if the connection is not currently open.
        """
        if self._ws is None or self._ws.closed:
            raise PointerConnectionError(
                "Pointer connection is not available"
            )
        await self._ws.send_str(json.dumps(msg))
