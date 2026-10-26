"""Testumgebung: eigene Integration laden."""

import sys

import pytest

if sys.platform == "win32":
    # asyncio braucht unter Windows intern ein Socket-Paar; die Socket-Sperre der HA-Tests nur unter Linux
    import pytest_socket

    pytest_socket.disable_socket = lambda *args, **kwargs: None
    pytest_socket.socket_allow_hosts = lambda *args, **kwargs: None


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
