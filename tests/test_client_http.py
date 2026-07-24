"""HTTP integration tests for MyQGarageClient against a real aiohttp server."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import aiohttp
import pytest
from aiohttp import web

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
    MyQGarageClient,
    MyQGarageConnectionError,
)

pytestmark = pytest.mark.usefixtures("socket_enabled")

API_KEY = "test-api-key"


@pytest.fixture
async def api_app_state() -> dict[str, object]:
    """Shared mutable state for the local companion API handlers."""
    return {
        "devices": [{"id": "door_1", "name": "Main", "status": "closed"}],
        "info": {"installation_id": "installation-123"},
        "devices_status": 200,
        "info_status": 200,
        "devices_body": None,
        "info_body": None,
        "devices_content_type": "application/json",
        "info_content_type": "application/json",
        "last_devices_auth": None,
        "last_info_auth": None,
        "last_devices_path": None,
        "last_info_path": None,
        "redirect_devices": False,
        "sleep_devices": 0.0,
    }


@pytest.fixture
async def api_server(
    aiohttp_client, api_app_state: dict[str, object]
) -> AsyncIterator[tuple[aiohttp.ClientSession, str, dict[str, object]]]:
    """Start a local companion API and yield session, base URL, and state."""
    state = api_app_state

    async def devices_handler(request: web.Request) -> web.StreamResponse:
        state["last_devices_auth"] = request.headers.get("Authorization")
        state["last_devices_path"] = request.rel_url.path
        if state["redirect_devices"]:
            raise web.HTTPFound("/devices-final")
        if float(state["sleep_devices"]) > 0:
            await asyncio.sleep(float(state["sleep_devices"]))
        status = int(state["devices_status"])
        if state["devices_body"] is not None:
            return web.Response(
                status=status,
                text=str(state["devices_body"]),
                content_type=str(state["devices_content_type"]),
            )
        return web.json_response(state["devices"], status=status)

    async def devices_final_handler(request: web.Request) -> web.Response:
        state["last_devices_auth"] = request.headers.get("Authorization")
        state["last_devices_path"] = request.rel_url.path
        return web.json_response(state["devices"])

    async def info_handler(request: web.Request) -> web.StreamResponse:
        state["last_info_auth"] = request.headers.get("Authorization")
        state["last_info_path"] = request.rel_url.path
        status = int(state["info_status"])
        if state["info_body"] is not None:
            return web.Response(
                status=status,
                text=str(state["info_body"]),
                content_type=str(state["info_content_type"]),
            )
        if status == 404:
            raise web.HTTPNotFound()
        return web.json_response(state["info"], status=status)

    app = web.Application()
    app.router.add_get("/devices", devices_handler)
    app.router.add_get("/devices-final", devices_final_handler)
    app.router.add_get("/info", info_handler)
    app.router.add_get("/api/v1/devices", devices_handler)
    app.router.add_get("/api/v1/info", info_handler)

    client = await aiohttp_client(app)
    base_url = str(client.make_url("/")).rstrip("/")
    yield client.session, base_url, state


@pytest.mark.asyncio
async def test_get_devices_path_and_bearer_auth(api_server) -> None:
    """Client requests /devices with a Bearer token."""
    session, base_url, state = api_server
    client = MyQGarageClient(base_url, API_KEY, session)

    devices = await client.get_devices()

    assert devices == state["devices"]
    assert state["last_devices_path"] == "/devices"
    assert state["last_devices_auth"] == f"Bearer {API_KEY}"


@pytest.mark.asyncio
async def test_get_info_path_and_bearer_auth(api_server) -> None:
    """Client requests /info with a Bearer token."""
    session, base_url, state = api_server
    client = MyQGarageClient(base_url, API_KEY, session)

    info = await client.get_info()

    assert info == state["info"]
    assert state["last_info_path"] == "/info"
    assert state["last_info_auth"] == f"Bearer {API_KEY}"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_get_devices_auth_failures(api_server, status: int) -> None:
    """401/403 on /devices raise auth errors."""
    session, base_url, state = api_server
    state["devices_status"] = status
    client = MyQGarageClient(base_url, API_KEY, session)

    with pytest.raises(MyQGarageAuthError):
        await client.get_devices()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_get_info_auth_failures(api_server, status: int) -> None:
    """401/403 on /info raise auth errors."""
    session, base_url, state = api_server
    state["info_status"] = status
    client = MyQGarageClient(base_url, API_KEY, session)

    with pytest.raises(MyQGarageAuthError):
        await client.get_info()


@pytest.mark.asyncio
async def test_get_info_404_returns_none(api_server) -> None:
    """Missing /info support returns None."""
    session, base_url, state = api_server
    state["info_status"] = 404
    client = MyQGarageClient(base_url, API_KEY, session)

    assert await client.get_info() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 500, 502, 503])
async def test_get_devices_http_errors(api_server, status: int) -> None:
    """Rate-limit and server errors become connection errors."""
    session, base_url, state = api_server
    state["devices_status"] = status
    client = MyQGarageClient(base_url, API_KEY, session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_invalid_json(api_server) -> None:
    """Non-JSON bodies raise connection errors."""
    session, base_url, state = api_server
    state["devices_body"] = "not-json"
    state["devices_content_type"] = "text/plain"
    client = MyQGarageClient(base_url, API_KEY, session)

    with pytest.raises(MyQGarageConnectionError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_get_devices_incorrect_json_type(api_server) -> None:
    """A JSON object where a list is required raises a connection error."""
    session, base_url, state = api_server
    state["devices_body"] = '{"not":"a-list"}'
    client = MyQGarageClient(base_url, API_KEY, session)

    with pytest.raises(MyQGarageConnectionError, match="JSON list"):
        await client.get_devices()


@pytest.mark.asyncio
async def test_get_info_incorrect_json_type(api_server) -> None:
    """A JSON list where an object is required raises a connection error."""
    session, base_url, state = api_server
    state["info_body"] = "[]"
    client = MyQGarageClient(base_url, API_KEY, session)

    with pytest.raises(MyQGarageConnectionError, match="JSON object"):
        await client.get_info()


@pytest.mark.asyncio
async def test_base_url_with_path_prefix(api_server) -> None:
    """Client appends endpoints under a base path."""
    session, base_url, state = api_server
    client = MyQGarageClient(f"{base_url}/api/v1", API_KEY, session)

    devices = await client.get_devices()
    info = await client.get_info()

    assert devices == state["devices"]
    assert info == state["info"]
    assert state["last_devices_path"] == "/api/v1/devices"
    assert state["last_info_path"] == "/api/v1/info"


@pytest.mark.asyncio
async def test_redirect_is_followed(api_server) -> None:
    """Client follows redirects to the final devices payload."""
    session, base_url, state = api_server
    state["redirect_devices"] = True
    client = MyQGarageClient(base_url, API_KEY, session)

    devices = await client.get_devices()

    assert devices == state["devices"]
    assert state["last_devices_path"] == "/devices-final"


@pytest.mark.asyncio
async def test_timeout(api_server) -> None:
    """Slow responses surface as connection errors."""
    session, base_url, state = api_server
    state["sleep_devices"] = 0.2
    timeout_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=0.01),
        connector=session.connector,
        connector_owner=False,
    )
    try:
        client = MyQGarageClient(base_url, API_KEY, timeout_session)
        original_get = timeout_session.get

        def get_with_tiny_timeout(url, **kwargs):
            kwargs["timeout"] = aiohttp.ClientTimeout(total=0.01)
            return original_get(url, **kwargs)

        timeout_session.get = get_with_tiny_timeout  # type: ignore[method-assign]
        with pytest.raises(MyQGarageConnectionError):
            await client.get_devices()
    finally:
        await timeout_session.close()


@pytest.mark.asyncio
async def test_connection_error_to_closed_port() -> None:
    """Unreachable hosts raise connection errors."""
    session = aiohttp.ClientSession()
    try:
        client = MyQGarageClient("http://127.0.0.1:1", API_KEY, session)
        with pytest.raises(MyQGarageConnectionError):
            await client.get_devices()
    finally:
        await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "localhost",
    ],
)
async def test_loopback_hosts_and_custom_ports(aiohttp_server, host: str) -> None:
    """Client works against loopback hosts with custom ports."""

    async def devices(_request: web.Request) -> web.Response:
        return web.json_response([{"id": "door_1", "status": "closed"}])

    app = web.Application()
    app.router.add_get("/devices", devices)
    server = await aiohttp_server(app)
    base_url = f"http://{host}:{server.port}"
    session = aiohttp.ClientSession()
    try:
        client = MyQGarageClient(base_url, API_KEY, session)
        devices_payload = await client.get_devices()
        assert devices_payload[0]["id"] == "door_1"
    finally:
        await session.close()
