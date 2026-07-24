# myq-garage-api

Async HTTP client for the [MyQ Garage](https://github.com/andrewtryder/ha-myq-garage) companion REST API.

This package is the OSI-licensed, tagged PyPI dependency used by the Home Assistant custom integration for dependency transparency.

## Install

```bash
pip install myq-garage-api
```

## Usage

```python
import aiohttp
from myq_garage_api import MyQGarageClient, parse_devices

async with aiohttp.ClientSession() as session:
    client = MyQGarageClient("https://myq-api.example.com", "api-key", session)
    raw = await client.get_devices()
    devices = parse_devices(raw)
```

## License

MIT
