<p align="center">
  <img src="custom_components/myq_garage/brand/icon.png" alt="MyQ Garage" width="128">
</p>

# MyQ Garage Custom Component for Home Assistant

This is a custom component for Home Assistant that integrates with my other component for this,
a Cloudflare Worker that works with the MyQ notifications via email.

## Description
This integration provides a Cover entity to control and monitor the MyQ Garage Door Opener status.

## Installation

### HACS (Recommended)
1. Add this repository to HACS as a custom repository: `https://github.com/andrewtryder/ha-myq-garage`
2. Install the "MyQ Garage" integration.
3. Restart Home Assistant.
4. Add the integration through the Home Assistant UI: Settings -> Devices & Services -> Add Integration -> MyQ Garage.

## Configuration
When configuring the integration, you will be prompted for:
- **API URL**: The URL of your custom MyQ API endpoint.
- **API Key**: The API key to authenticate with your custom API.
