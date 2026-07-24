<p align="center">
  <img src="custom_components/myq_garage/brand/icon.png" alt="MyQ Garage" width="128">
</p>

# MyQ Garage Custom Component for Home Assistant

[![hacs][hacsbadge]][hacs]
[![GitHub release][releasebadge]][releases]

[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs]: https://github.com/custom-components/hacs
[releasebadge]: https://img.shields.io/github/release/andrewtryder/ha-myq-garage.svg
[releases]: https://github.com/andrewtryder/ha-myq-garage/releases

[![Open your Home Assistant instance and open a repository inside Home Assistant.](https://my.home-assistant.io/badges/open_repository.svg)](https://my.home-assistant.io/redirect/open_repository/?owner=andrewtryder&repository=ha-myq-garage&category=integration)

This integration connects Home Assistant to a custom MyQ Garage REST API. It is designed to work with a companion **Cloudflare Worker** (or any compatible service) that tracks garage door state from MyQ email notifications.

## Requirements

Before installing this integration, you need:

1. **A deployed MyQ Garage companion API** that implements the [API contract](#api-contract) below (`GET /devices` with Bearer auth; optional `GET /info`).
2. **Home Assistant 2026.7.0 or newer**, with [HACS](https://hacs.xyz/) installed.

This repository is a standalone HACS custom integration: install only `custom_components/myq_garage`. No PyPI package or extra runtime dependency is required.

## Supported devices

- The integration creates Home Assistant cover entities for garage-door records exposed by the companion API.
- Each record must include a stable, non-empty device `id`.
- Only garage cover entities are created.
- Other MyQ device types are not supported unless the companion API maps them into the documented garage-door schema.

## Supported functionality

| Functionality               | Support |
| --------------------------- | ------- |
| Open/closed state           | Yes     |
| Opening/closing state       | Yes     |
| Availability                | Yes     |
| Dynamic device addition     | Yes     |
| Manual stale-device removal | Yes     |
| Open/close commands         | No      |
| Push updates                | No      |
| Reauthentication            | Yes     |
| Reconfiguration             | Yes     |
| Diagnostics                 | Yes     |

## Use cases

- Alert when a garage door remains open longer than expected.
- Show garage state on a dashboard.
- Warn when a door is still open overnight.
- Detect when the companion API stops reporting a door (entity becomes unavailable).

## What it does

This integration provides **read-only** Cover entities that report garage door open/closed status. It polls your API every 30 seconds by default. Open/close commands are **not** supported.

## Installation

### HACS (recommended)

Once this repository is included in the default HACS catalog, search for **MyQ Garage** in HACS and install it.

Until then, add it as a custom repository:

1. In HACS, open **Integrations** → **⋮** → **Custom repositories**.
2. Add `https://github.com/andrewtryder/ha-myq-garage` with category **Integration**.
3. Install **MyQ Garage**.
4. Restart Home Assistant.
5. Add the integration: **Settings** → **Devices & Services** → **Add Integration** → **MyQ Garage**.

## Configuration

When configuring the integration, you will be prompted for:

- **API URL**: The base URL of your MyQ Garage API (for example, `https://myq-api.example.com`).
- **API Key**: The Bearer token your API expects in the `Authorization` header.

Only one config entry is allowed per API URL.

Use **HTTPS** for public hosts. Plain HTTP is allowed only for localhost, loopback, RFC1918 private addresses, link-local addresses, and `.local` development hostnames.

The integration polls your API every **30 seconds** by default. To change this, go to **Settings → Devices & Services → MyQ Garage → Configure** and set **Scan interval (seconds)** (allowed range: 10–3600).

To change the API URL or API key later, use **Settings → Devices & Services → MyQ Garage → ⋮ → Reconfigure**.

## Data updates

- All device state comes from polling your companion API's `GET /devices` endpoint on the configured scan interval; there is no push/webhook support.
- Every poll replaces the full set of known devices. If your API stops returning a device, the corresponding Home Assistant entity becomes **unavailable**. You can delete that device from **Settings → Devices & Services → MyQ Garage → Devices** (Delete). If a new device appears later, a cover entity is created automatically without reloading the integration.
- Changing the scan interval in the options flow takes effect immediately.
- If your API key is revoked or expires, Home Assistant prompts you to reauthenticate rather than repeatedly retrying with a bad key.
- Download diagnostics from the integration page when filing issues; API keys, URLs, installation IDs, device IDs, and device names are redacted.
- If an older config entry has an invalid stored URL that cannot be migrated, Home Assistant creates a repair issue with a guided fix flow that updates the existing entry in place.

## API contract

Implement a companion service with the following endpoints. HTTPS is strongly recommended for any non-local deployment because the API key is sent as a Bearer token.

### `GET /devices` (required)

```http
GET /devices HTTP/1.1
Host: myq-api.example.com
Authorization: Bearer <api_key>
```

Successful response (`200`) — JSON array:

```json
[
  {
    "id": "door_1",
    "name": "Main Garage Door",
    "status": "closed"
  }
]
```

| Field    | Type   | Required | Notes |
| -------- | ------ | -------- | ----- |
| `id`     | string | yes      | Stable non-empty device identity. Missing/empty ids are skipped; duplicate ids reject the whole update. |
| `name`   | string | no       | Defaults to `MyQ Garage Door`. |
| `status` | string | no       | One of `open`, `closed`, `opening`, `closing`. Anything else is treated as unknown. |

Expected HTTP status codes:

| Status | Meaning |
| ------ | ------- |
| `200`  | Success with a JSON array body |
| `401` / `403` | Invalid or expired API key (triggers reauthentication) |
| `429`  | Rate limited (treated as a transient connection failure) |
| `5xx`  | Server error (retry on next poll) |

### `GET /info` (optional)

```http
GET /info HTTP/1.1
Host: myq-api.example.com
Authorization: Bearer <api_key>
```

Successful response (`200`):

```json
{ "installation_id": "some-stable-identifier" }
```

`installation_id` should be a stable identifier for your account/installation (not derived from the URL, hostname, or IP). When present, the integration uses it to detect duplicate config entries and to confirm reauthentication targets the same installation.

If `/info` is not implemented, return `404`. The integration then falls back to comparing configured URLs.

### Example `curl` requests

```bash
curl -sS -H "Authorization: Bearer YOUR_API_KEY" \
  https://myq-api.example.com/devices

curl -sS -H "Authorization: Bearer YOUR_API_KEY" \
  https://myq-api.example.com/info
```

## Automation examples

Replace the placeholders with your entity ID and notification service.

### Notify when a door stays open

```yaml
automation:
  - alias: Garage door open too long
    triggers:
      - trigger: state
        entity_id: cover.YOUR_GARAGE_DOOR
        to: "open"
        for:
          minutes: 15
    actions:
      - action: notify.YOUR_NOTIFY_SERVICE
        data:
          title: Garage door open
          message: "Your garage door has been open for 15 minutes."
```

### Notify when a garage entity becomes unavailable

```yaml
automation:
  - alias: Garage door unavailable
    triggers:
      - trigger: state
        entity_id: cover.YOUR_GARAGE_DOOR
        to: unavailable
        for:
          minutes: 5
    actions:
      - action: notify.YOUR_NOTIFY_SERVICE
        data:
          title: Garage door unavailable
          message: "Home Assistant lost garage door status from the companion API."
```

### Overnight open-door warning

```yaml
automation:
  - alias: Garage door open overnight
    triggers:
      - trigger: time
        at: "23:00:00"
    conditions:
      - condition: state
        entity_id: cover.YOUR_GARAGE_DOOR
        state: "open"
    actions:
      - action: notify.YOUR_NOTIFY_SERVICE
        data:
          title: Garage door still open
          message: "A garage door is still open at 11 PM."
```

## Known limitations

- **Read-only**: this integration cannot open or close your garage door; it only reports status from your API.
- **Cloud polling**: state changes are reflected after the next poll (every 30 seconds by default), not instantly.
- **No discovery**: the integration must be added manually with your API URL and API key.
- **Single account identity**: config entries are de-duplicated by comparing configured API URLs unless your companion API implements `/info`.

## Troubleshooting

- **"Failed to connect to the MyQ API"**: verify the API URL is reachable from Home Assistant and that `/devices` responds.
- **"Invalid API Key"**: confirm the API key matches your companion API. Use the reauthentication flow to enter a new key without recreating the integration.
- **"Plain HTTP is only allowed…"**: use HTTPS for public hosts, or an allowed local address for development.
- **A garage door entity is unavailable**: your API no longer includes that device in `/devices`. Delete the device if it is gone for good.
- **Entity shows an unknown state**: your API returned a `status` outside `open` / `closed` / `opening` / `closing`.
- Enable debug logging:

  ```yaml
  logger:
    logs:
      custom_components.myq_garage: debug
  ```

## Removing the integration

1. Go to **Settings → Devices & Services**.
2. Find **MyQ Garage** and select **⋮** → **Delete**.
3. Confirm removal. This deletes the config entry and associated cover entities/devices; it does not affect your companion API.
4. Optionally remove the integration files via HACS if you no longer want the code installed.

## Local Development

This repository includes optional Docker-based tooling for testing the integration end-to-end. HACS users do not need these files.

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | Runs Home Assistant and a mock API locally |
| `ha-dev/config/configuration.yaml` | Minimal Home Assistant config for dev |
| `ha-dev/mock_api/` | Mock `/devices` endpoint used during local testing |

### Quick start

```bash
docker compose up -d
```

Open Home Assistant at http://localhost:8123, then add the **MyQ Garage** integration with:

- **API URL**: `http://mock-api:8080`
- **API Key**: `dev-api-key`

The custom component is bind-mounted from this repo, so code changes are picked up after restarting the Home Assistant container.

```bash
docker compose restart homeassistant
docker compose logs -f homeassistant
docker compose down
```

Home Assistant runtime data (`.storage/`, databases, logs) is gitignored under `ha-dev/config/` and is created locally when you run Docker.

Unit tests use `pytest` and do not require Docker. See `AGENTS.md` for linting, formatting, and test commands.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for conventional commits, squash-only merge guidance, Release Please token setup, and how to refresh the test dependency lockfile.
