"""Tests for the MyQ Garage config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
    MyQGarageConnectionError,
)
from custom_components.myq_garage.const import DOMAIN

MOCK_DEVICE_DATA = [
    {
        "id": "door_1",
        "name": "Main Garage Door",
        "status": "closed",
    }
]


async def test_config_flow_user_step(hass: HomeAssistant) -> None:
    """Test the user step shows the configuration form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_config_flow_success(hass: HomeAssistant) -> None:
    """Test a successful config flow creates an entry without a unique ID."""
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com/",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MyQ Garage"
    # The stored URL is the normalized form (trailing slash stripped), not
    # the raw user input.
    assert result["data"] == {
        CONF_URL: "https://myq-api.example.com",
        CONF_API_KEY: "test_api_key",
    }
    # The companion API does not (yet) support the optional /info endpoint,
    # so the URL is not used as a unique ID; duplicates are instead prevented
    # by comparing normalized URLs (see below).
    assert result["result"].unique_id is None


async def test_config_flow_uses_stable_id_when_available(hass: HomeAssistant) -> None:
    """Test a config entry adopts a stable id from the optional /info endpoint."""
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-123"},
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com/",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "installation-123"


async def test_config_flow_duplicate_stable_id_aborts(hass: HomeAssistant) -> None:
    """Test two different URLs sharing the same stable id are rejected."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="installation-123",
        data={
            CONF_URL: "https://old-myq-api.example.com",
            CONF_API_KEY: "existing_key",
        },
    )
    existing_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-123"},
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://new-myq-api.example.com",
                CONF_API_KEY: "new_api_key",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_info_endpoint_error_falls_back(hass: HomeAssistant) -> None:
    """Test the flow still succeeds if the optional /info call fails."""
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            side_effect=MyQGarageConnectionError("Connection failed"),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com/",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id is None


async def test_config_flow_duplicate_url_aborts(hass: HomeAssistant) -> None:
    """Test configuring the same API URL twice is rejected."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "existing_key",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com/",
                CONF_API_KEY: "new_api_key",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_connection_error(hass: HomeAssistant) -> None:
    """Test connection errors are surfaced to the user."""
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageConnectionError("Connection failed"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_auth_error(hass: HomeAssistant) -> None:
    """Test authentication errors are surfaced to the user."""
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "bad_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_config_flow_unknown_error(hass: HomeAssistant) -> None:
    """Test an unexpected exception is surfaced as an unknown error."""
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=RuntimeError("boom"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_config_flow_invalid_url(hass: HomeAssistant) -> None:
    """Test malformed URLs are rejected before attempting a connection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_URL: "not-a-url",
            CONF_API_KEY: "test_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_config_flow_url_with_credentials_rejected(hass: HomeAssistant) -> None:
    """Test URLs with embedded credentials are rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_URL: "https://user:pass@myq-api.example.com",
            CONF_API_KEY: "test_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_config_flow_url_with_query_rejected(hass: HomeAssistant) -> None:
    """Test a URL with a query string is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_URL: "https://myq-api.example.com/api?token=x",
            CONF_API_KEY: "test_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_config_flow_url_with_fragment_rejected(hass: HomeAssistant) -> None:
    """Test a URL with a fragment is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_URL: "https://myq-api.example.com/api#section",
            CONF_API_KEY: "test_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_config_flow_normalizes_hostname_and_default_port(
    hass: HomeAssistant,
) -> None:
    """Test the stored URL lowercases the host and drops the default port."""
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "HTTPS://MyQ-API.Example.com:443/",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_URL] == "https://myq-api.example.com"


async def test_config_flow_url_with_invalid_port_rejected(hass: HomeAssistant) -> None:
    """Test a URL with a non-numeric/out-of-range port is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_URL: "https://myq-api.example.com:99999",
            CONF_API_KEY: "test_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_config_flow_preserves_non_default_port(hass: HomeAssistant) -> None:
    """Test a non-default port is preserved in the normalized/stored URL."""
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com:8443",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_URL] == "https://myq-api.example.com:8443"


async def test_config_flow_normalizes_ipv6_hostname(hass: HomeAssistant) -> None:
    """Test an IPv6 literal host normalizes with brackets preserved."""
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "http://[::1]:8080",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_URL] == "http://[::1]:8080"


async def test_config_flow_url_missing_hostname_rejected(hass: HomeAssistant) -> None:
    """Test a URL with a scheme but no hostname is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={
            CONF_URL: "https://",
            CONF_API_KEY: "test_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_config_flow_ignores_malformed_existing_entry_url(
    hass: HomeAssistant,
) -> None:
    """Test duplicate detection skips an existing entry with an unparsable URL."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "not-a-url",
            CONF_API_KEY: "existing_key",
        },
    )
    existing_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "new_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_config_flow_recovers_after_error(hass: HomeAssistant) -> None:
    """Test the user can correct an error and successfully create an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "bad_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == "good_api_key"


async def test_reauth_flow_shows_form(hass: HomeAssistant) -> None:
    """Test starting a reauth flow shows the confirmation form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


async def test_reauth_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test a reauth attempt with a still-invalid API key shows an error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "still_bad_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_connection_error(hass: HomeAssistant) -> None:
    """Test a connection error during reauth shows a cannot_connect error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageConnectionError("Connection failed"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "some_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reauth_flow_recovers_after_error(hass: HomeAssistant) -> None:
    """Test the same reauth flow succeeds after correcting the API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "still_bad_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
        patch(
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "good_api_key"


async def test_reauth_flow_unknown_error(hass: HomeAssistant) -> None:
    """Test an unexpected exception during reauth is surfaced as unknown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=RuntimeError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "some_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_reauth_flow_success(hass: HomeAssistant) -> None:
    """Test a successful reauth updates and reloads the existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
        patch(
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "good_api_key"
    assert entry.data[CONF_URL] == "https://myq-api.example.com"


async def test_reauth_flow_adopts_stable_id(hass: HomeAssistant) -> None:
    """Test reauth adopts a stable id once the API starts providing one."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)
    assert entry.unique_id is None

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-123"},
        ),
        patch(
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.unique_id == "installation-123"


async def test_reauth_flow_wrong_account_aborts(hass: HomeAssistant) -> None:
    """Test reauth with a key for a different account is rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-999"},
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "someone_elses_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert entry.data[CONF_API_KEY] == "bad_api_key"
    assert entry.unique_id == "installation-123"


async def test_reauth_flow_aborts_when_adopting_duplicate_stable_id(
    hass: HomeAssistant,
) -> None:
    """Test reauth refuses to adopt a stable id already owned by another entry."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://other-api.example.com",
            CONF_API_KEY: "other_api_key",
        },
    )
    existing.add_to_hass(hass)

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)
    assert entry.unique_id is None

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-123"},
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.unique_id is None
    assert entry.data[CONF_API_KEY] == "bad_api_key"
    assert existing.unique_id == "installation-123"


async def test_reauth_identified_entry_info_404_rejects(hass: HomeAssistant) -> None:
    """Identified reauth must fail when /info is unsupported (404 → None)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_verify_account"}
    assert entry.data[CONF_API_KEY] == "bad_api_key"
    assert entry.unique_id == "installation-123"


async def test_reauth_identified_entry_info_connection_failure_rejects(
    hass: HomeAssistant,
) -> None:
    """Identified reauth must fail when /info cannot be reached."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            side_effect=MyQGarageConnectionError("offline"),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data[CONF_API_KEY] == "bad_api_key"
    assert entry.unique_id == "installation-123"


async def test_reauth_identified_entry_malformed_info_rejects(
    hass: HomeAssistant,
) -> None:
    """Identified reauth must fail when /info lacks a usable installation id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": ""},
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_verify_account"}
    assert entry.data[CONF_API_KEY] == "bad_api_key"
    assert entry.unique_id == "installation-123"


async def test_reauth_unidentified_entry_unsupported_info_succeeds(
    hass: HomeAssistant,
) -> None:
    """Legacy unidentified reauth still succeeds when /info is unsupported."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "bad_api_key",
        },
    )
    entry.add_to_hass(hass)
    assert entry.unique_id is None

    result = await entry.start_reauth_flow(hass)

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
        patch(
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "good_api_key"
    assert entry.unique_id is None
