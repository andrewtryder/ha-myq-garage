"""Client for the MyQ Garage API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class MyQGarageClientError(Exception):
    """Base exception for MyQ Garage Client."""


class MyQGarageAuthError(MyQGarageClientError):
    """Exception for authentication errors."""


class MyQGarageConnectionError(MyQGarageClientError):
    """Exception for connection errors."""


class MyQGarageClient:
    """Client for interacting with the MyQ Garage API."""

    def __init__(self, url: str, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.session = session

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get the list of devices (garage doors)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with self.session.get(
                f"{self.url}/devices", headers=headers, timeout=10
            ) as resp:
                if resp.status in (401, 403):
                    raise MyQGarageAuthError("Invalid API Key")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise MyQGarageConnectionError(f"Error connecting to API: {err}") from err
