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
2. **Home Assistant** with [HACS](https://hacs.xyz/) installed.

If you do not already have the API running, open an [issue](https://github.com/andrewtryder/ha-myq-garage/issues) for setup guidance.

## What it does

This integration provides **read-only** Cover entities that report garage door open/closed status. It polls your API every minute. Open/close commands are **not** supported.

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
