"""Typed data models for the MyQ Garage integration.

Re-exports the published ``myq-garage-api`` package for the integration.
"""

from myq_garage_api import (
    MyQGarageDataError,
    MyQGarageDevice,
    MyQGarageDoorStatus,
    extract_stable_id,
    parse_devices,
)

__all__ = [
    "MyQGarageDataError",
    "MyQGarageDevice",
    "MyQGarageDoorStatus",
    "extract_stable_id",
    "parse_devices",
]
