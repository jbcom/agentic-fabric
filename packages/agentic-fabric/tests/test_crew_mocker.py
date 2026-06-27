"""Tests for local agentic-fabric test support."""

from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

from tests._crew_mocker import ALL_FRAMEWORK_MODULES, CREWAI_MODULES, LANGGRAPH_MODULES, STRANDS_MODULES


if TYPE_CHECKING:
    from tests._crew_mocker import CrewMocker


class TestCrewMockerBasics:
    """Test basic CrewMocker functionality."""

    def test_crew_mocker_has_mocker(self, crew_mocker: CrewMocker) -> None:
        assert crew_mocker.mocker is not None

    def test_magic_mock_property(self, crew_mocker: CrewMocker) -> None:
        assert crew_mocker.MagicMock() is not None

    def test_mock_module_adds_to_sys_modules(self, crew_mocker: CrewMocker) -> None:
        mock = crew_mocker.mock_module("test_fake_module_xyz")
        assert sys.modules["test_fake_module_xyz"] is mock

    def test_mock_module_returns_same_mock_on_repeat(self, crew_mocker: CrewMocker) -> None:
        assert crew_mocker.mock_module("test_fake_repeat") is crew_mocker.mock_module("test_fake_repeat")

    def test_restore_modules_cleans_up(self, crew_mocker: CrewMocker) -> None:
        crew_mocker.mock_module("test_restore_target")
        crew_mocker.restore_modules()
        assert "test_restore_target" not in sys.modules


class TestFrameworkMocking:
    """Test framework-specific mocking helpers."""

    def test_mock_crewai_mocks_all_modules(self, crew_mocker: CrewMocker) -> None:
        mocks = crew_mocker.mock_crewai()
        for module in CREWAI_MODULES:
            assert module in mocks
            assert module in sys.modules

    def test_mock_langgraph_mocks_all_modules(self, crew_mocker: CrewMocker) -> None:
        mocks = crew_mocker.mock_langgraph()
        for module in LANGGRAPH_MODULES:
            assert module in mocks

    def test_mock_strands_mocks_all_modules(self, crew_mocker: CrewMocker) -> None:
        mocks = crew_mocker.mock_strands()
        for module in STRANDS_MODULES:
            assert module in mocks

    def test_mock_all_frameworks(self, crew_mocker: CrewMocker) -> None:
        mocks = crew_mocker.mock_all_frameworks()
        for module in ALL_FRAMEWORK_MODULES:
            assert module in mocks

    def test_patch_get_llm_custom_return(self, crew_mocker: CrewMocker) -> None:
        custom_llm = crew_mocker.MagicMock(name="custom_llm")
        mock = crew_mocker.patch_get_llm(return_value=custom_llm)
        assert mock.return_value is custom_llm


class TestLocalFixtures:
    """Test reusable local fixtures."""

    def test_temp_workspace_fixture(self, temp_workspace: Path) -> None:
        assert (temp_workspace / "packages" / "sample" / ".crewai" / "manifest.yaml").exists()
