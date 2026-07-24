"""Minimal mock MyQ Garage API for local Home Assistant testing."""

from __future__ import annotations

from aiohttp import web

API_KEY = "dev-api-key"
INSTALLATION_ID = "dev-installation-1"
DEVICES = [
    {"id": "door_1", "name": "Main Garage Door", "status": "closed"},
    {"id": "door_2", "name": "Side Garage Door", "status": "open"},
]


async def get_devices(request: web.Request) -> web.Response:
    """Return garage door devices when the API key is valid."""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {API_KEY}":
        return web.Response(status=401, text="Unauthorized")

    return web.json_response(DEVICES)


async def get_info(request: web.Request) -> web.Response:
    """Return a stable installation id, demonstrating optional /info support.

    Real companion API deployments may omit this endpoint entirely (the
    integration falls back to comparing configured URLs); this mock
    implements it so the stable-identity code path can be exercised locally.
    """
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {API_KEY}":
        return web.Response(status=401, text="Unauthorized")

    return web.json_response({"installation_id": INSTALLATION_ID})


def main() -> None:
    """Start the mock API server."""
    app = web.Application()
    app.router.add_get("/devices", get_devices)
    app.router.add_get("/info", get_info)
    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
