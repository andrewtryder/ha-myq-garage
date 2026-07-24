"""Client for the MyQ Garage API.

Re-exports the published ``myq-garage-api`` package for the integration.
"""

from myq_garage_api import (
    MyQGarageAccountVerificationError,
    MyQGarageAuthError,
    MyQGarageClient,
    MyQGarageClientError,
    MyQGarageConnectionError,
)

__all__ = [
    "MyQGarageAccountVerificationError",
    "MyQGarageAuthError",
    "MyQGarageClient",
    "MyQGarageClientError",
    "MyQGarageConnectionError",
]
