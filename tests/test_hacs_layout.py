"""Deployment smoke tests for a standalone HACS layout."""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.const import DOMAIN

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_SRC = REPO_ROOT / "custom_components" / "myq_garage"

MOCK_DEVICE_DATA = [{"id": "door_1", "name": "Main Garage Door", "status": "closed"}]


def test_integration_sources_do_not_import_repository_packages() -> None:
    """HACS installs must not depend on packages/myq-garage-api."""
    forbidden = {"myq_garage_api"}
    for path in INTEGRATION_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = {node.module.split(".")[0]}
            else:
                continue
            overlap = names & forbidden
            assert not overlap, f"{path} imports {overlap}"


def test_hacs_layout_imports_from_isolated_copy(tmp_path: Path) -> None:
    """Only custom_components/myq_garage is required for imports."""
    isolated_root = tmp_path / "config"
    isolated_integration = isolated_root / "custom_components" / "myq_garage"
    shutil.copytree(
        INTEGRATION_SRC,
        isolated_integration,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    assert not (tmp_path / "packages").exists()

    script = textwrap.dedent(
        """
        import importlib
        import sys

        modules = [
            "custom_components.myq_garage",
            "custom_components.myq_garage.client",
            "custom_components.myq_garage.models",
            "custom_components.myq_garage.config_flow",
            "custom_components.myq_garage.coordinator",
            "custom_components.myq_garage.cover",
            "custom_components.myq_garage.diagnostics",
            "custom_components.myq_garage.entity",
            "custom_components.myq_garage.repairs",
            "custom_components.myq_garage.util",
            "custom_components.myq_garage.const",
        ]
        assert "myq_garage_api" not in sys.modules
        for name in modules:
            importlib.import_module(name)
        assert "myq_garage_api" not in sys.modules
        print("ok")
        """
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(isolated_root)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
    assert "myq_garage_api" not in sys.modules


async def test_hacs_layout_mocked_setup_succeeds(hass: HomeAssistant) -> None:
    """A mocked config entry sets up without any external package install."""
    assert "myq_garage_api" not in sys.modules

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "test-key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert "myq_garage_api" not in sys.modules
