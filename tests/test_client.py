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
    json_error: Exception | None = None,
    raise_for_status: Exception | None = None,
) -> AsyncMock:
    """Build an AsyncMock ClientSession that yields a mocked response."""
    resp = AsyncMock()
    resp.status = status
    if json_error is None:
        resp.json = AsyncMock(return_value=payload)
    else:
        resp.json = AsyncMock(side_effect=json_error)
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
async def test_get_devices_invalid_json():
    """Test a malformed JSON response is surfaced as a connection error."""
    session = _mock_session_response(json_error=ValueError("not valid json"))
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_connection_error():
    """Test connection error."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.side_effect = aiohttp.ClientError("Connection Refused")
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_get_info_success():
    """Test a companion API that supports the optional /info endpoint."""
    session = _mock_session_response(payload={"installation_id": "installation-123"})
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    info = await client.get_info()
    assert info == {"installation_id": "installation-123"}


@pytest.mark.asyncio
async def test_get_info_not_supported_returns_none():
    """Test a companion API without /info support returns None, not an error."""
    session = _mock_session_response(status=404)
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    assert await client.get_info() is None


@pytest.mark.asyncio
async def test_get_info_auth_error():
    """Test an auth error on /info is raised like any other auth failure."""
    session = _mock_session_response(status=401)
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageAuthError):
        await client.get_info()


@pytest.mark.asyncio
async def test_get_info_connection_error():
    """Test a connection error on /info surfaces as a connection error."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.get.side_effect = aiohttp.ClientError("Connection Refused")
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_info()


@pytest.mark.asyncio
async def test_get_info_invalid_json():
    """Test a malformed JSON /info response is surfaced as a connection error."""
    session = _mock_session_response(json_error=ValueError("not valid json"))
    client = MyQGarageClient("http://localhost:8080", "test_key", session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_info()
