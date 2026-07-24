"""Tests for MyQ Garage repair flows."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.client import MyQGarageConnectionError
from custom_components.myq_garage.const import DOMAIN, invalid_legacy_url_issue_id
from custom_components.myq_garage.repairs import async_create_fix_flow

MOCK_DEVICE_DATA = [
    {
        "id": "door_1",
        "name": "Main Garage Door",
        "status": "closed",
    }
]


async def _create_migration_error_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a config entry stuck in migration error with a repair issue."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com/?token=secret",
            CONF_API_KEY: "old_api_key",
        },
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_invalid_legacy_url_creates_repair_issue(hass: HomeAssistant) -> None:
    """Migration failure registers a fixable repair issue."""
    entry = await _create_migration_error_entry(hass)

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, invalid_legacy_url_issue_id(entry.entry_id)
    )
    assert issue is not None
    assert issue.is_fixable is True
    assert issue.translation_key == "invalid_legacy_url"


async def test_repair_flow_updates_invalid_legacy_url(hass: HomeAssistant) -> None:
    """Repair flow migrates the entry to v3 and clears the issue."""
    assert await async_setup_component(hass, "repairs", {})
    await hass.async_block_till_done()

    entry = await _create_migration_error_entry(hass)
    issue_id = invalid_legacy_url_issue_id(entry.entry_id)
    flow_manager = hass.data["repairs"]["flow_manager"]

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
        result = await flow_manager.async_init(DOMAIN, data={"issue_id": issue_id})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "confirm"

        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert hass.config_entries.async_get_entry(entry.entry_id) is None
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    new_entry = entries[0]
    assert new_entry.version == 3
    assert new_entry.data[CONF_URL] == "https://myq-api.example.com"
    assert new_entry.data[CONF_API_KEY] == "good_api_key"
    assert new_entry.unique_id == "installation-123"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_repair_flow_invalid_url(hass: HomeAssistant) -> None:
    """Repair flow rejects an invalid replacement URL."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
    result = await flow_manager.async_configure(
        result["flow_id"],
        {
            CONF_URL: "https://myq-api.example.com/?token=still-bad",
            CONF_API_KEY: "good_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


async def test_repair_flow_connection_error(hass: HomeAssistant) -> None:
    """Repair flow surfaces connection failures."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageConnectionError("offline"),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_repair_flow_wrong_account(hass: HomeAssistant) -> None:
    """Repair flow rejects a key belonging to a different installation."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
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
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "someone_elses_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wrong_account"}


async def test_repair_flow_entry_missing(hass: HomeAssistant) -> None:
    """Repair flow aborts when the config entry no longer exists."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    issue_id = invalid_legacy_url_issue_id(entry.entry_id)
    await hass.config_entries.async_remove(entry.entry_id)

    # Recreate the issue so the repairs manager will still hand us a flow.
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key="invalid_legacy_url",
        data={"entry_id": entry.entry_id},
    )

    flow_manager = hass.data["repairs"]["flow_manager"]
    result = await flow_manager.async_init(DOMAIN, data={"issue_id": issue_id})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "entry_missing"


async def test_repair_flow_recreate_failed(hass: HomeAssistant) -> None:
    """Repair flow aborts when recreating the config entry fails."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
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
            "homeassistant.config_entries.ConfigEntriesFlowManager.async_init",
            new=AsyncMock(
                return_value={
                    "type": FlowResultType.FORM,
                    "flow_id": "x",
                    "handler": DOMAIN,
                    "step_id": "user",
                }
            ),
        ),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "recreate_failed"


async def test_async_create_fix_flow_from_issue_id_prefix(
    hass: HomeAssistant,
) -> None:
    """Fall back to parsing the entry id from the issue id prefix."""
    flow = await async_create_fix_flow(hass, "invalid_legacy_url_abc123", data=None)
    assert flow._entry_id == "abc123"


async def test_async_create_fix_flow_unknown_issue() -> None:
    """Unknown issue ids raise ValueError."""
    with pytest.raises(ValueError, match="Unknown repair issue_id"):
        await async_create_fix_flow(
            None,  # type: ignore[arg-type]
            "something_else",
            data=None,
        )


async def test_repair_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Repair flow surfaces authentication failures."""
    from custom_components.myq_garage.client import MyQGarageAuthError

    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("bad key"),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "bad_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_repair_flow_cannot_verify_account(hass: HomeAssistant) -> None:
    """Repair flow requires /info for identified entries."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
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
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_verify_account"}


async def test_repair_flow_unknown_error(hass: HomeAssistant) -> None:
    """Repair flow surfaces unexpected failures."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=RuntimeError("boom"),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
