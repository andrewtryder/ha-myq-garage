<p align="center">
  <img src="custom_components/myq_garage/brand/icon.png" alt="MyQ Garage" width="128">
</p>

# MyQ Garage for Home Assistant

[![hacs][hacsbadge]][hacs]
[![GitHub release][releasebadge]][releases]

[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs]: https://hacs.xyz/
[releasebadge]: https://img.shields.io/github/release/andrewtryder/ha-myq-garage.svg
[releases]: https://github.com/andrewtryder/ha-myq-garage/releases

[![Open your Home Assistant instance and open a repository inside the HACS store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrewtryder&repository=ha-myq-garage&category=integration)

This is the **Home Assistant / HACS integration** for [myq-garage-worker](https://github.com/andrewtryder/myq-garage-worker) — a Cloudflare Worker that watches MyQ garage door notification emails and exposes live door status.

Use this integration to show your garage doors in Home Assistant. The Worker is required separately; this repository only covers the Home Assistant side.

## What you get

- A **cover** entity for each garage door reported by your Worker
- Open, closed, opening, and closing status
- Status updates by polling (about every 30 seconds by default)

This integration is **read-only**. It does not open or close your garage door.

Handy ideas once it’s set up:

- Alert if a door stays open too long
- Show door status on a dashboard
- Warn if a door is still open late at night
- Notice when the Worker stops reporting a door (the entity becomes unavailable)

## Before you start

1. Deploy [myq-garage-worker](https://github.com/andrewtryder/myq-garage-worker) and note its **API URL** and **API key**.
2. Run **Home Assistant 2026.7.0 or newer** with [HACS](https://hacs.xyz/) installed.

## Installation

### Option A: Open in HACS

Use the badge above, or open this link from a browser that can reach your Home Assistant instance:

[Add MyQ Garage in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrewtryder&repository=ha-myq-garage&category=integration)

Then download **MyQ Garage**, restart Home Assistant, and continue with [Setup](#setup).

### Option B: Add as a custom repository

1. In HACS, open **Integrations** → **⋮** → **Custom repositories**.
2. Add `https://github.com/andrewtryder/ha-myq-garage` with category **Integration**.
3. Find **MyQ Garage** and download it.
4. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **MyQ Garage**.
3. Enter:
   - **API URL** — your Worker base URL (for example `https://myq-api.example.com`)
   - **API Key** — the Bearer token from your Worker
4. Submit.

Use **HTTPS** for public deployments. Plain HTTP is only for local/private addresses.

To change how often Home Assistant checks status, open **Settings → Devices & services → MyQ Garage → Configure** and set **Scan interval** (10–3600 seconds; default 30).

To update the URL or API key later, use **⋮ → Reconfigure**. If the key stops working, Home Assistant will ask you to reauthenticate.

## Troubleshooting

- **Failed to connect** — confirm the Worker URL is reachable from Home Assistant and that the Worker is running.
- **Invalid API key** — check the key in your Worker settings, then use the reauthentication prompt in Home Assistant.
- **Plain HTTP is only allowed…** — switch to HTTPS for public hosts.
- **Door entity unavailable** — the Worker is no longer listing that door. Delete the device in Home Assistant if it won’t return.
- **Unknown state** — the Worker returned a status Home Assistant doesn’t recognize; check the Worker logs and recent emails.

## Removing the integration

1. Go to **Settings → Devices & services**.
2. Find **MyQ Garage** → **⋮** → **Delete**.
3. Optionally remove it from HACS as well.

This only removes the Home Assistant integration. Your Worker is unchanged.

## For developers

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for development, testing, and contribution guidelines. The Worker API contract lives in the [myq-garage-worker](https://github.com/andrewtryder/myq-garage-worker) repository.
