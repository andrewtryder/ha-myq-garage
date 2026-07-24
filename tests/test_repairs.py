"""Tests for MyQ Garage repair flows."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.client import MyQGarageConnectionError
from custom_components.myq_garage.const import (
    CONF_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    invalid_legacy_url_issue_id,
)
from custom_components.myq_garage.repairs import async_create_fix_flow

MOCK_DEVICE_DATA = [
    {
        "id": "door_1",
        "name": "Main Garage Door",
        "status": "closed",
    }
]


async def _create_migration_error_entry(
    hass: HomeAssistant,
    *,
    unique_id: str | None = "installation-123",
    options: dict | None = None,
    title: str = "MyQ Garage",
) -> MockConfigEntry:
    """Create a config entry stuck in migration error with a repair issue."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=unique_id,
        title=title,
        data={
            CONF_URL: "https://myq-api.example.com/?token=secret",
            CONF_API_KEY: "old_api_key",
        },
        options=options or {CONF_SCAN_INTERVAL_SECONDS: 90},
    )
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
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


async def test_repair_flow_updates_invalid_legacy_url_in_place(
    hass: HomeAssistant,
) -> None:
    """Repair flow updates the existing entry and clears the issue."""
    assert await async_setup_component(hass, "repairs", {})
    await hass.async_block_till_done()

    entry = await _create_migration_error_entry(hass, title="Custom Title")
    entry_id = entry.entry_id
    issue_id = invalid_legacy_url_issue_id(entry_id)
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
    repaired = hass.config_entries.async_get_entry(entry_id)
    assert repaired is not None
    assert repaired.entry_id == entry_id
    assert repaired.version == 3
    assert repaired.title == "Custom Title"
    assert repaired.unique_id == "installation-123"
    assert repaired.options[CONF_SCAN_INTERVAL_SECONDS] == 90
    assert repaired.data[CONF_URL] == "https://myq-api.example.com"
    assert repaired.data[CONF_API_KEY] == "good_api_key"
    assert repaired.state is ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_repair_flow_preserves_entity_registry_customization(
    hass: HomeAssistant,
) -> None:
    """Repair keeps the same entry id so customized entity ids survive."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "cover",
        DOMAIN,
        "door_1_cover",
        config_entry=entry,
        suggested_object_id="main_garage_custom",
    )
    customized = entity_registry.async_get("cover.main_garage_custom")
    assert customized is not None
    assert customized.config_entry_id == entry.entry_id

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
        result = await flow_manager.async_init(
            DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
        )
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    surviving = entity_registry.async_get("cover.main_garage_custom")
    assert surviving is not None
    assert surviving.config_entry_id == entry.entry_id
    assert surviving.unique_id == "door_1_cover"


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
    assert hass.config_entries.async_get_entry(entry.entry_id) is not None
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_repair_flow_insecure_public_http(hass: HomeAssistant) -> None:
    """Repair flow rejects plain HTTP for public hosts."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
    result = await flow_manager.async_configure(
        result["flow_id"],
        {
            CONF_URL: "http://myq-api.example.com",
            CONF_API_KEY: "good_api_key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "insecure_url"}


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
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


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


async def test_repair_flow_duplicate_url_aborts(hass: HomeAssistant) -> None:
    """Repair aborts when another entry already uses the replacement URL."""
    assert await async_setup_component(hass, "repairs", {})
    existing = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-other",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "other_key",
        },
    )
    existing.add_to_hass(hass)
    entry = await _create_migration_error_entry(hass)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(
        DOMAIN, data={"issue_id": invalid_legacy_url_issue_id(entry.entry_id)}
    )
    result = await flow_manager.async_configure(
        result["flow_id"],
        {
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "good_api_key",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert hass.config_entries.async_get_entry(entry.entry_id) is not None
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_repair_flow_duplicate_stable_id_aborts(hass: HomeAssistant) -> None:
    """Repair aborts when another entry already owns the installation id."""
    assert await async_setup_component(hass, "repairs", {})
    existing = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://other-api.example.com",
            CONF_API_KEY: "other_key",
        },
    )
    existing.add_to_hass(hass)
    entry = await _create_migration_error_entry(hass, unique_id=None)
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
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


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


async def test_repair_flow_duplicate_url_skips_unparsable_other_entry(
    hass: HomeAssistant,
) -> None:
    """Duplicate URL detection ignores other entries with unparsable URLs."""
    assert await async_setup_component(hass, "repairs", {})
    existing = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-other",
        data={
            CONF_URL: "https://broken.example.com/?bad=1",
            CONF_API_KEY: "other_key",
        },
    )
    existing.add_to_hass(hass)
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
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.state is ConfigEntryState.LOADED


async def test_repair_flow_adopts_stable_id_when_missing(
    hass: HomeAssistant,
) -> None:
    """Repair adopts a stable installation id when the entry lacked one."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass, unique_id=None)
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
            return_value={"installation_id": "installation-new"},
        ),
        patch(
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.unique_id == "installation-new"
    assert entry.state is ConfigEntryState.LOADED


async def test_repair_flow_reload_raises(hass: HomeAssistant) -> None:
    """Repair aborts when async_setup raises after the entry is updated."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    issue_id = invalid_legacy_url_issue_id(entry.entry_id)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(DOMAIN, data={"issue_id": issue_id})
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-123"},
        ),
        patch.object(
            hass.config_entries,
            "async_setup",
            side_effect=RuntimeError("setup exploded"),
        ),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reload_failed"
    assert hass.config_entries.async_get_entry(entry.entry_id) is not None
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_repair_flow_reload_failed(hass: HomeAssistant) -> None:
    """Repair aborts when setup fails after updating the entry, keeping it."""
    assert await async_setup_component(hass, "repairs", {})
    entry = await _create_migration_error_entry(hass)
    issue_id = invalid_legacy_url_issue_id(entry.entry_id)
    flow_manager = hass.data["repairs"]["flow_manager"]

    result = await flow_manager.async_init(DOMAIN, data={"issue_id": issue_id})
    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value={"installation_id": "installation-123"},
        ),
        patch.object(
            hass.config_entries,
            "async_setup",
            return_value=False,
        ),
    ):
        result = await flow_manager.async_configure(
            result["flow_id"],
            {
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "good_api_key",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reload_failed"
    repaired = hass.config_entries.async_get_entry(entry.entry_id)
    assert repaired is not None
    assert repaired.data[CONF_URL] == "https://myq-api.example.com"
    assert repaired.version == 3
    assert repaired.options[CONF_SCAN_INTERVAL_SECONDS] == 90
    # Issue remains until a successful recovery.
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


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
