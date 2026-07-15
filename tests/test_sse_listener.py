"""Tests for the Mediabox SSE listener."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from custom_components.mediabox.sse_listener import (
    BACKOFF_INITIAL,
    BACKOFF_MAX,
    MediaboxSseListener,
)


class _FakeContent:
    """Async iterable that yields SSE lines, then blocks until cancelled.

    A real aiohttp SSE stream stays open until the connection drops or the
    task is cancelled.  Blocking on an Event when exhausted lets the task be
    cancelled cleanly via async_stop().
    """

    def __init__(self, lines: list[str]) -> None:
        self._lines = [l.encode("utf-8") for l in lines]
        self._idx = 0
        self._closed = asyncio.Event()

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self._idx < len(self._lines):
            line = self._lines[self._idx]
            self._idx += 1
            return line
        await self._closed.wait()
        raise StopAsyncIteration

    def close(self) -> None:
        self._closed.set()


class _FakeSseResponse:
    def __init__(self, lines: list[str]) -> None:
        self.content = _FakeContent(lines)
        self.raise_for_status = MagicMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.content.close()
        return False


def _make_session(responses):
    """Create a mock session whose get() returns responses in order.

    Each call to session.get() pops the next item from *responses*.
    Returns a _FakeSseResponse (supports ``async with``).
    """
    iter_resps = iter(responses)

    def _get(url, headers=None):
        return next(iter_resps)

    session = MagicMock()
    session.get = MagicMock(side_effect=_get)
    return session


async def test_first_event_sets_current_app_immediately() -> None:
    session = _make_session([_FakeSseResponse(["data: Plex\n"])])

    listener = MediaboxSseListener(session, "192.168.1.50:3000", "key")
    await listener.async_start()
    await asyncio.sleep(0.05)

    assert listener.current_app == "Plex"
    await listener.async_stop()


async def test_subsequent_events_update_current_app() -> None:
    session = _make_session(
        [_FakeSseResponse(["data: Plex\n", "\n", "data: Netflix\n"])]
    )

    listener = MediaboxSseListener(session, "192.168.1.50:3000", "key")
    await listener.async_start()
    await asyncio.sleep(0.05)

    assert listener.current_app == "Netflix"
    await listener.async_stop()


async def test_listener_callback_invoked_on_update() -> None:
    session = _make_session([_FakeSseResponse(["data: Plex\n"])])

    listener = MediaboxSseListener(session, "192.168.1.50:3000", "key")
    calls = []
    listener.async_add_listener(lambda: calls.append(1))

    await listener.async_start()
    await asyncio.sleep(0.05)

    assert len(calls) >= 1
    await listener.async_stop()


async def test_unsubscribe_stops_callback_invocation() -> None:
    session = _make_session([_FakeSseResponse(["data: Plex\n"])])

    listener = MediaboxSseListener(session, "192.168.1.50:3000", "key")
    calls = []
    unsub = listener.async_add_listener(lambda: calls.append(1))

    await listener.async_start()
    await asyncio.sleep(0.05)
    unsub()
    assert len(listener._listeners) == 0
    await listener.async_stop()


async def test_connection_failure_triggers_reconnect_with_backoff() -> None:
    delays: list[float] = []

    async def _tracking_sleep(delay: float) -> None:
        delays.append(delay)

    call_count = 0

    def _get(url, headers=None):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            raise Exception("connection lost")
        return _FakeSseResponse(["data: Plex\n"])

    session = MagicMock()
    session.get = MagicMock(side_effect=_get)

    import custom_components.mediabox.sse_listener as mod

    real_sleep_fn = asyncio.sleep
    original_ref = mod.asyncio.sleep
    try:
        mod.asyncio.sleep = _tracking_sleep  # type: ignore[assignment]
        listener = MediaboxSseListener(session, "192.168.1.50:3000", "key")
        await listener.async_start()
        await real_sleep_fn(0.1)
        await listener.async_stop()
    finally:
        mod.asyncio.sleep = original_ref  # type: ignore[assignment]

    assert len(delays) >= 3
    assert delays[:3] == [1, 2, 4]


async def test_deliberate_stop_does_not_log_as_error() -> None:
    session = _make_session([_FakeSseResponse([])])

    listener = MediaboxSseListener(session, "192.168.1.50:3000", "key")
    await listener.async_start()
    await asyncio.sleep(0.01)

    with patch("custom_components.mediabox.sse_listener._LOGGER") as mock_log:
        await listener.async_stop()
        mock_log.error.assert_not_called()
        mock_log.warning.assert_not_called()
