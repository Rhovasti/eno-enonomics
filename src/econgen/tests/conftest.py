"""Shared pytest fixtures for dynamics tests."""

import pytest

from ..dynamics.client import MinskyClient, MinskyUnavailable


@pytest.fixture(scope="module")
def minsky_client():
    """A connected MinskyClient, or skip the test if pyminsky is unavailable."""
    client = MinskyClient()
    try:
        client.connect()
    except MinskyUnavailable:
        pytest.skip("pyminsky extension not available in this environment")
    return client
