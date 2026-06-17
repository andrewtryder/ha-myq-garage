"""Fixtures for MyQ Garage integration testing."""

import threading

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]

original_enumerate = threading.enumerate


def _filtered_enumerate():
    return [
        t
        for t in original_enumerate()
        if "waitpid-" not in t.name and "_run_safe_shutdown_loop" not in t.name
    ]


threading.enumerate = _filtered_enumerate


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant tests."""
    yield
