"""Tests for the MyQ Garage client."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
    MyQGarageClient,
    MyQGarageConnectionError,
)


def _mock_session_response(
    *,
    status: int = 200,
    payload: object | None = None,
    raise_for_status: Exception | None = None,
) -> AsyncMock:
    """Build an AsyncMock ClientSession that yields a mocked response."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=payload)
    if raise_for_status is None:
        resp.raise_for_status = MagicMock()
    else:
        resp.raise_for_status = MagicMock(side_effect=raise_for_status)

    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.return_value.__aenter__.return_value = resp
    session.get.return_value.__aexit__.return_value = None
    return session


@pytest.mark.asyncio
async def test_get_devices_success():
    """Test successful device retrieval."""
    session = _mock_session_response(
        payload=[{"id": "1", "name": "Garage Door", "status": "closed"}]
    )
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    devices = await client.get_devices()
    assert len(devices) == 1
    assert devices[0]["id"] == "1"
    session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_devices_auth_error():
    """Test auth error."""
    session = _mock_session_response(status=401)
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageAuthError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_connection_error():
    """Test connection error."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.side_effect = aiohttp.ClientError("Connection Refused")
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_devices()
