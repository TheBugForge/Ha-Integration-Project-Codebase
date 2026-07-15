"""Pytest configuration for Mediabox tests.

On Windows, the proactor event loop uses AF_INET socket.socketpair() for its
internal self-pipe.  pytest-homeassistant-custom-component calls
disable_socket(allow_unix_socket=True) in its pytest_runtest_setup hook, but
AF_UNIX doesn't exist on Windows so every socket creation is blocked,
including the event loop's own self-pipe.

Fix: monkey-patch disable_socket at import time so that on Windows it allows
AF_INET / AF_INET6 creation (the event loop needs these) while the connect()
guard set by socket_allow_hosts(["127.0.0.1"]) still blocks real network I/O.
"""

from __future__ import annotations

import socket
import sys

import pytest
import pytest_socket as _ps


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield


if sys.platform == "win32":
    _original_disable = _ps.disable_socket

    def _patched_disable(allow_unix_socket: bool = False) -> None:  # noqa: ARG001
        """Allow socket creation on Windows while keeping connect() guarded."""
        socket.socket = _ps._true_socket

    _ps.disable_socket = _patched_disable  # type: ignore[assignment]
