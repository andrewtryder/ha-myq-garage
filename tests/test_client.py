"""Tests for the MyQ Garage client."""

import aiohttp
import pytest
from aioresponses import aioresponses

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
    MyQGarageClient,
    MyQGarageConnectionError,
)


@pytest.mark.asyncio
async def test_get_devices_success():
    """Test successful device retrieval."""
    url = "http://localhost:8080"
    api_key = "test_key"

    async with aiohttp.ClientSession() as session:
        client = MyQGarageClient(url, api_key, session)

        with aioresponses() as m:
            m.get(
                f"{url}/devices",
                payload=[{"id": "1", "name": "Garage Door", "status": "closed"}],
                status=200,
            )

            devices = await client.get_devices()
            assert len(devices) == 1
            assert devices[0]["id"] == "1"


@pytest.mark.asyncio
async def test_get_devices_auth_error():
    """Test auth error."""
    url = "http://localhost:8080"
    api_key = "test_key"

    async with aiohttp.ClientSession() as session:
        client = MyQGarageClient(url, api_key, session)

        with aioresponses() as m:
            m.get(f"{url}/devices", status=401)

            with pytest.raises(MyQGarageAuthError):
                await client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_connection_error():
    """Test connection error."""
    url = "http://localhost:8080"
    api_key = "test_key"

    async with aiohttp.ClientSession() as session:
        client = MyQGarageClient(url, api_key, session)

        with aioresponses() as m:
            m.get(f"{url}/devices", exception=aiohttp.ClientError("Connection Refused"))

            with pytest.raises(MyQGarageConnectionError):
                await client.get_devices()
