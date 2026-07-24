"""MyQ Garage companion API client library."""

from .client import (
    MyQGarageAccountVerificationError,
    MyQGarageAuthError,
    MyQGarageClient,
    MyQGarageClientError,
    MyQGarageConnectionError,
)
from .models import (
    MyQGarageDataError,
    MyQGarageDevice,
    MyQGarageDoorStatus,
    extract_stable_id,
    parse_devices,
)

__all__ = [
    "MyQGarageAccountVerificationError",
    "MyQGarageAuthError",
    "MyQGarageClient",
    "MyQGarageClientError",
    "MyQGarageConnectionError",
    "MyQGarageDataError",
    "MyQGarageDevice",
    "MyQGarageDoorStatus",
    "extract_stable_id",
    "parse_devices",
]

__version__ = "0.1.0"
