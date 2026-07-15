"""Tests for the Mediabox persistent pointer connection."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.mediabox.pointer_connection import (
    PersistentPointerConnection,
    PointerConnectionError,
)


class _FakeWsResponse:
    """Fake WebSocket response for testing."""

    def __init__(self) -> None:
        self._closed = False
        self.sent: list[str] = []
        self._waiters: list[asyncio.Future] = []

    @property
    def closed(self) -> bool:
        return self._closed

    async def close(self) -> None:
        self._closed = True
        # Wake up any pending __aiter__ iteration
        for f in self._waiters:
            if not f.done():
                f.set_result(None)

    async def send_str(self, data: str) -> None:
        if self._closed:
            raise ConnectionError("WebSocket is closed")
        self.sent.append(data)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if self._closed:
            raise StopAsyncIteration
        # Block until closed (simulates an open connection)
        f: asyncio.Future = asyncio.get_event_loop().create_future()
        self._waiters.append(f)
        await f
        raise StopAsyncIteration


async def test_connects_with_api_key_header_at_handshake() -> None:
    fake_ws = _FakeWsResponse()
    session = MagicMock()
    session.ws_connect = AsyncMock(return_value=fake_ws)

    conn = PersistentPointerConnection(session, "192.168.1.50:3000", "secret-key")
    await conn.async_start()
    await asyncio.sleep(0.05)

    session.ws_connect.assert_called_once()
    call_kwargs = session.ws_connect.call_args
    assert call_kwargs[1]["headers"] == {"X-Api-Key": "secret-key"}

    await conn.async_stop()


async def test_send_gesture_writes_correct_json_frame() -> None:
    fake_ws = _FakeWsResponse()
    session = MagicMock()
    session.ws_connect = AsyncMock(return_value=fake_ws)

    conn = PersistentPointerConnection(session, "192.168.1.50:3000", "key")
    await conn.async_start()
    # Wait for connection to be established
    await asyncio.sleep(0.05)

    await conn.send_gesture({"type": "move", "dx": 10, "dy": -5})

    import json
    sent = json.loads(fake_ws.sent[0])
    assert sent == {"type": "move", "dx": 10, "dy": -5}

    await conn.async_stop()


async def test_send_gesture_while_disconnected_raises_clear_exception() -> None:
    session = MagicMock()
    session.ws_connect = AsyncMock(side_effect=Exception("connection refused"))

    conn = PersistentPointerConnection(session, "192.168.1.50:3000", "key")
    await conn.async_start()
    await asyncio.sleep(0.05)

    with pytest.raises(PointerConnectionError, match="not available"):
        await conn.send_gesture({"type": "start"})

    await conn.async_stop()


async def test_stop_closes_connection_cleanly() -> None:
    fake_ws = _FakeWsResponse()
    session = MagicMock()
    session.ws_connect = AsyncMock(return_value=fake_ws)

    conn = PersistentPointerConnection(session, "192.168.1.50:3000", "key")
    await conn.async_start()
    await asyncio.sleep(0.05)

    await conn.async_stop()
    assert fake_ws.closed


async def test_connection_drop_triggers_reconnect_with_backoff() -> None:
    delays: list[float] = []

    async def _tracking_sleep(delay: float) -> None:
        delays.append(delay)

    call_count = 0

    def _ws_connect(url, headers=None):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            raise Exception("connection refused")
        return _FakeWsResponse()

    session = MagicMock()
    session.ws_connect = AsyncMock(side_effect=_ws_connect)

    import custom_components.mediabox.pointer_connection as mod

    real_sleep_fn = asyncio.sleep
    original_ref = mod.asyncio.sleep
    try:
        mod.asyncio.sleep = _tracking_sleep  # type: ignore[assignment]
        conn = PersistentPointerConnection(session, "192.168.1.50:3000", "key")
        await conn.async_start()
        await real_sleep_fn(0.1)
        await conn.async_stop()
    finally:
        mod.asyncio.sleep = original_ref  # type: ignore[assignment]

    assert len(delays) >= 3
    assert delays[:3] == [1, 2, 4]
