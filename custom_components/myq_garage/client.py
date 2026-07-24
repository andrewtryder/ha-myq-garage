"""Client for the MyQ Garage API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

import aiohttp

_LOGGER = logging.getLogger(__name__)

JsonDict = dict[str, Any]
JsonList = list[Any]


class MyQGarageClientError(Exception):
    """Base exception for MyQ Garage Client."""


class MyQGarageAuthError(MyQGarageClientError):
    """Exception for authentication errors."""


class MyQGarageConnectionError(MyQGarageClientError):
    """Exception for connection errors."""


class MyQGarageAccountVerificationError(MyQGarageClientError):
    """Exception when installation identity cannot be verified via /info."""


class MyQGarageClient:
    """Client for interacting with the MyQ Garage API."""

    def __init__(self, url: str, api_key: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.session = session

    def _headers(self) -> dict[str, str]:
        """Return the standard request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _request_json(self, path: str) -> Any:
        """Perform a GET and return decoded JSON, mapping transport errors."""
        try:
            async with self.session.get(
                f"{self.url}{path}",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (401, 403):
                    raise MyQGarageAuthError("Invalid API Key")
                if path == "/info" and resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except MyQGarageAuthError:
            raise
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise MyQGarageConnectionError(f"Timeout connecting to API: {err}") from err
        except aiohttp.ClientError as err:
            raise MyQGarageConnectionError(f"Error connecting to API: {err}") from err
        except ValueError as err:
            # resp.json() raises a ValueError (e.g. json.JSONDecodeError) when
            # the response body is not valid JSON.
            raise MyQGarageConnectionError(
                f"Invalid JSON response from API: {err}"
            ) from err

    async def get_devices(self) -> JsonList:
        """Get the list of devices (garage doors)."""
        payload = await self._request_json("/devices")
        if not isinstance(payload, list):
            raise MyQGarageConnectionError(
                f"Expected a JSON list from /devices, got {type(payload).__name__}"
            )
        return cast(JsonList, payload)

    async def get_info(self) -> JsonDict | None:
        """Get stable installation info from the API, if supported.

        The ``/info`` endpoint is optional. Companion APIs that do not yet
        implement it should return HTTP 404, in which case this returns
        None so callers can fall back to other duplicate-entry detection.
        """
        payload = await self._request_json("/info")
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise MyQGarageConnectionError(
                f"Expected a JSON object from /info, got {type(payload).__name__}"
            )
        return cast(JsonDict, payload)
