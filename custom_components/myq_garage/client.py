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
        except ValueError as err:
            # resp.json() raises a ValueError (e.g. json.JSONDecodeError) when
            # the response body is not valid JSON.
            raise MyQGarageConnectionError(
                f"Invalid JSON response from API: {err}"
            ) from err

    async def get_info(self) -> dict[str, Any] | None:
        """Get stable installation info from the API, if supported.

        The ``/info`` endpoint is optional. Companion APIs that do not yet
        implement it should return HTTP 404, in which case this returns
        None so callers can fall back to other duplicate-entry detection.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with self.session.get(
                f"{self.url}/info", headers=headers, timeout=10
            ) as resp:
                if resp.status in (401, 403):
                    raise MyQGarageAuthError("Invalid API Key")
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise MyQGarageConnectionError(f"Error connecting to API: {err}") from err
        except ValueError as err:
            raise MyQGarageConnectionError(
                f"Invalid JSON response from API: {err}"
            ) from err
