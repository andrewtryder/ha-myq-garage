# MyQ Garage Custom Component for Home Assistant

This is a custom component for Home Assistant that integrates with a custom MyQ Garage API.

## Description
This integration provides a Cover entity to control and monitor a garage door via a custom MyQ API endpoint.

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
