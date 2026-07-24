"""Typed data models for the MyQ Garage integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .client import MyQGarageClientError

_LOGGER = logging.getLogger(__name__)


class MyQGarageDataError(MyQGarageClientError):
    """Raised when the API response contains invalid or unsafe data."""


class MyQGarageDoorStatus(StrEnum):
    """Known status values for a MyQ Garage door."""

    OPEN = "open"
    CLOSED = "closed"
    OPENING = "opening"
    CLOSING = "closing"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MyQGarageDevice:
    """A validated MyQ Garage device record."""

    id: str
    name: str
    status: MyQGarageDoorStatus

    @property
    def is_closed(self) -> bool | None:
        """Return True if closed, False if open, None if unknown."""
        if self.status is MyQGarageDoorStatus.CLOSED:
            return True
        if self.status is MyQGarageDoorStatus.OPEN:
            return False
        return None


def extract_stable_id(info: Any) -> str | None:
    """Extract and validate a stable installation id from an /info payload.

    Returns None if info is missing, malformed, or lacks a usable
    ``installation_id``, so callers can fall back to other duplicate-entry
    detection instead of failing.
    """
    if not isinstance(info, dict):
        return None

    stable_id = info.get("installation_id")
    if not isinstance(stable_id, str) or not stable_id.strip():
        return None

    return stable_id


def parse_devices(raw_devices: Any) -> dict[str, MyQGarageDevice]:
    """Validate and normalize the raw ``/devices`` API payload.

    Records with a missing or empty ``id`` are deliberately skipped and
    logged, rather than being coalesced into a shared placeholder identity.
    A duplicate ``id`` indicates an inconsistent API response and rejects
    the entire update, since it cannot be resolved to a single stable
    entity. A response that is not a list of objects is rejected outright.
    """
    if not isinstance(raw_devices, list):
        raise MyQGarageDataError(
            f"Expected a list of devices from the API, got {type(raw_devices).__name__}"
        )

    devices: dict[str, MyQGarageDevice] = {}

    for raw in raw_devices:
        if not isinstance(raw, dict):
            _LOGGER.warning("Skipping device record that is not an object: %r", raw)
            continue

        device_id = raw.get("id")
        if not isinstance(device_id, str) or not device_id.strip():
            _LOGGER.warning("Skipping device with missing or invalid id: %s", raw)
            continue

        if device_id in devices:
            raise MyQGarageDataError(
                f"API response contains duplicate device id: {device_id}"
            )

        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            name = "MyQ Garage Door"

        raw_status = raw.get("status")
        try:
            status = MyQGarageDoorStatus(raw_status)
        except ValueError:
            _LOGGER.warning(
                "Device %s has unknown status %r; treating as unknown",
                device_id,
                raw_status,
            )
            status = MyQGarageDoorStatus.UNKNOWN

        devices[device_id] = MyQGarageDevice(id=device_id, name=name, status=status)

    return devices
