"""Tests for local agentic-fabric test support."""

from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

from pytest_agentic_fabric.mocking import ALL_FRAMEWORK_MODULES, CREWAI_MODULES, LANGGRAPH_MODULES, STRANDS_MODULES


if TYPE_CHECKING:
    from pytest_agentic_fabric.mocking import FabricMocker


class TestFabricMockerBasics:
    """Test basic FabricMocker functionality."""

    def test_fabric_mocker_has_mocker(self, fabric_mocker: FabricMocker) -> None:
        assert fabric_mocker.mocker is not None

    def test_magic_mock_property(self, fabric_mocker: FabricMocker) -> None:
        assert fabric_mocker.MagicMock() is not None

    def test_mock_module_adds_to_sys_modules(self, fabric_mocker: FabricMocker) -> None:
        mock = fabric_mocker.mock_module("test_fake_module_xyz")
        assert sys.modules["test_fake_module_xyz"] is mock

    def test_mock_module_returns_same_mock_on_repeat(self, fabric_mocker: FabricMocker) -> None:
        assert fabric_mocker.mock_module("test_fake_repeat") is fabric_mocker.mock_module("test_fake_repeat")

    def test_restore_modules_cleans_up(self, fabric_mocker: FabricMocker) -> None:
        fabric_mocker.mock_module("test_restore_target")
        fabric_mocker.restore_modules()
        assert "test_restore_target" not in sys.modules


class TestFrameworkMocking:
    """Test framework-specific mocking helpers."""

    def test_mock_crewai_mocks_all_modules(self, fabric_mocker: FabricMocker) -> None:
        mocks = fabric_mocker.mock_crewai()
        for module in CREWAI_MODULES:
            assert module in mocks
            assert module in sys.modules

    def test_mock_langgraph_mocks_all_modules(self, fabric_mocker: FabricMocker) -> None:
        mocks = fabric_mocker.mock_langgraph()
        for module in LANGGRAPH_MODULES:
            assert module in mocks

    def test_mock_strands_mocks_all_modules(self, fabric_mocker: FabricMocker) -> None:
        mocks = fabric_mocker.mock_strands()
        for module in STRANDS_MODULES:
            assert module in mocks

    def test_mock_all_frameworks(self, fabric_mocker: FabricMocker) -> None:
        mocks = fabric_mocker.mock_all_frameworks()
        for module in ALL_FRAMEWORK_MODULES:
            assert module in mocks

    def test_patch_get_llm_custom_return(self, fabric_mocker: FabricMocker) -> None:
        custom_llm = fabric_mocker.MagicMock(name="custom_llm")
        mock = fabric_mocker.patch_get_llm(return_value=custom_llm)
        assert mock.return_value is custom_llm


class TestLocalFixtures:
    """Test reusable local fixtures."""

    def test_temp_workspace_fixture(self, temp_workspace: Path) -> None:
        assert (temp_workspace / "packages" / "sample" / ".fabric" / "manifest.yaml").exists()
