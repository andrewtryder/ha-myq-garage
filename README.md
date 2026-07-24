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

This integration connects Home Assistant to a custom MyQ Garage REST API. It is designed to work with a companion **Cloudflare Worker** that tracks garage door state from MyQ email notifications.

## Requirements

Before installing this integration, you need:

1. **A deployed MyQ Garage API** — a Cloudflare Worker (or compatible REST service) that exposes a `/devices` endpoint and accepts Bearer token authentication. This integration does not talk to MyQ directly.
2. **Home Assistant 2026.7.0 or newer**, with [HACS](https://hacs.xyz/) installed.

If you do not already have the API running, open an [issue](https://github.com/andrewtryder/ha-myq-garage/issues) for setup guidance.

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

The integration polls your API every **30 seconds** by default. To change this, go to **Settings → Devices & Services → MyQ Garage → Configure** and set **Scan interval (seconds)** (allowed range: 10–3600).

To change the API URL or API key later, use **Settings → Devices & Services → MyQ Garage → ⋮ → Reconfigure**.

## Data updates

- All device state comes from polling your companion API's `GET /devices` endpoint on the configured scan interval; there is no push/webhook support.
- Every poll replaces the full set of known devices. If your API stops returning a device (for example, it was removed from your account), the corresponding Home Assistant entity becomes **unavailable** rather than showing a stale state. You can then delete that device from **Settings → Devices & Services → MyQ Garage → Devices** (Delete). If a new device appears in a later poll, a cover entity is created automatically without reloading the integration.
- Changing the scan interval in the options flow takes effect immediately, without needing to reload the integration or restart Home Assistant.
- If your API key is revoked or expires, Home Assistant will prompt you to reauthenticate (**Settings → Devices & Services → MyQ Garage → Reconfigure**) rather than repeatedly retrying with a bad key.
- Download diagnostics from the integration page (**Download diagnostics**) when filing issues; the API key is redacted automatically.
- If an older config entry has an invalid stored URL that cannot be migrated, Home Assistant creates a repair issue with a guided fix flow.
## API contract

This integration expects your companion API to expose:

```
GET /devices
Authorization: Bearer <api_key>
```

returning a JSON array of device objects:

```json
[
  {
    "id": "door_1",
    "name": "Main Garage Door",
    "status": "closed"
  }
]
```

- `id` (string, required): a stable, non-empty identifier for the device. Records missing an `id` are skipped and logged; a response containing two devices with the same `id` is treated as invalid and the entire update is rejected (the previous good data is kept until the next successful poll).
- `name` (string, optional): a human-readable device name. Defaults to "MyQ Garage Door" if omitted.
- `status` (string, optional): one of `open`, `closed`, `opening`, `closing`. Any other value (or a missing value) is treated as unknown, which Home Assistant reports as an unknown cover state rather than open or closed.

The endpoint must respond with `401` or `403` for an invalid or expired API key so Home Assistant can distinguish authentication failures (which trigger reauthentication) from connectivity failures (which trigger a retry).

### Optional: stable installation identity (`/info`)

```
GET /info
Authorization: Bearer <api_key>
```

If implemented, this should return:

```json
{ "installation_id": "some-stable-identifier" }
```

`installation_id` should be a stable identifier for your account/installation (not derived from the URL, hostname, or IP). When present, the integration uses it to detect duplicate config entries even if the API URL changes later, and to confirm you're reauthenticating the same account rather than switching to a different one. If your API does not implement `/info`, return `404` and the integration falls back to comparing configured URLs — no other behavior changes.

## Known limitations

- **Read-only**: this integration cannot open or close your garage door; it only reports status reported by your API.
- **Cloud polling**: state changes are only reflected after the next poll (every 30 seconds by default), not instantly.
- **No discovery**: the integration must be added manually with your API URL and API key; there is no automatic discovery of your companion API.
- **Single account identity**: config entries are de-duplicated by comparing configured API URLs unless your companion API implements the optional `/info` endpoint described above, which provides a durable identity independent of the URL.

## Troubleshooting

- **"Failed to connect to the MyQ API"**: verify the API URL is reachable from your Home Assistant instance (no typos, correct scheme/port) and that the `/devices` endpoint responds.
- **"Invalid API Key"**: confirm the API key matches what your companion API expects. If the integration later prompts you to reauthenticate, go to **Settings → Devices & Services → MyQ Garage** and follow the reauthentication flow to enter a new key without recreating the integration.
- **A garage door entity is unavailable**: this means your API no longer includes that device in its `/devices` response. Check your companion API/account configuration; the entity returns automatically once the device reappears in the API response. If the device is gone for good, open the device page and choose **Delete**.
- **Entity shows an unknown state**: your API returned a `status` value that is not one of `open`, `closed`, `opening`, or `closing`. Check the Home Assistant logs for a warning identifying the offending device and status value.
- Enable debug logging for more detail by adding the following to `configuration.yaml`:

  ```yaml
  logger:
    logs:
      custom_components.myq_garage: debug
  ```

## Removing the integration

1. Go to **Settings → Devices & Services**.
2. Find **MyQ Garage** and select **⋮** → **Delete**.
3. Confirm removal. This deletes the config entry and all associated cover entities and devices; it does not affect your companion API or its data.
4. Optionally, remove the integration files via HACS (**HACS → Integrations → MyQ Garage → ⋮ → Remove**) if you no longer want the code installed.

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
