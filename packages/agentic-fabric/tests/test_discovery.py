"""Tests for the discovery module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestDiscovery:
    """Tests for package discovery functionality."""

    def test_discover_packages_finds_crewai_directories(self, temp_workspace: Path) -> None:
        """Test that discover_packages finds packages with .crewai directories."""
        from agentic_fabric.core.discovery import discover_packages

        packages = discover_packages(workspace_root=temp_workspace)

        assert "sample" in packages
        assert packages["sample"].exists()

    def test_discover_packages_finds_fabric_directories(self, tmp_path: Path) -> None:
        """Test that discover_packages finds framework-agnostic .fabric directories."""
        from agentic_fabric.core.discovery import discover_packages

        # Create packages with .fabric directory
        pkg_dir = tmp_path / "packages" / "strata"
        fabric_dir = pkg_dir / ".fabric"
        fabric_dir.mkdir(parents=True)
        (fabric_dir / "manifest.yaml").write_text("name: strata\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path)

        assert "strata" in packages
        assert packages["strata"].name == ".fabric"

    def test_discover_packages_prefers_fabric_over_crewai(self, tmp_path: Path) -> None:
        """Test that .fabric takes priority over .crewai when both exist."""
        from agentic_fabric.core.discovery import discover_packages

        # Create package with both .fabric and .crewai
        pkg_dir = tmp_path / "packages" / "hybrid"
        (pkg_dir / ".fabric").mkdir(parents=True)
        (pkg_dir / ".fabric" / "manifest.yaml").write_text("name: hybrid\nfabric_agents: {}")
        (pkg_dir / ".crewai").mkdir(parents=True)
        (pkg_dir / ".crewai" / "manifest.yaml").write_text("name: hybrid\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path)

        assert "hybrid" in packages
        # .fabric should be preferred (framework-agnostic first)
        assert packages["hybrid"].name == ".fabric"

    def test_discover_packages_returns_empty_when_no_packages(self, tmp_path: Path) -> None:
        """Test that discover_packages returns empty dict when no config dirs exist."""
        from agentic_fabric.core.discovery import discover_packages

        # Create empty packages directory
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()
        (packages_dir / "some_package").mkdir()

        packages = discover_packages(workspace_root=tmp_path)

        assert packages == {}

    def test_discover_packages_rejects_unknown_framework(self, tmp_path: Path) -> None:
        """Unknown framework filters should not widen discovery to all directories."""
        from agentic_fabric.core.discovery import discover_packages

        with pytest.raises(ValueError, match="Unknown framework: crewaii"):
            discover_packages(workspace_root=tmp_path, framework="crewaii")

    def test_discover_all_framework_configs(self, tmp_path: Path) -> None:
        """Test discovering all framework configs for a package."""
        from agentic_fabric.core.discovery import discover_all_framework_configs

        # Create package with multiple framework configs
        pkg_dir = tmp_path / "packages" / "multi"
        (pkg_dir / ".fabric").mkdir(parents=True)
        (pkg_dir / ".fabric" / "manifest.yaml").write_text("name: multi\nfabric_agents: {}")
        (pkg_dir / ".crewai").mkdir(parents=True)
        (pkg_dir / ".crewai" / "manifest.yaml").write_text("name: multi\nfabric_agents: {}")

        configs = discover_all_framework_configs(workspace_root=tmp_path)

        assert "multi" in configs
        assert None in configs["multi"]  # .fabric -> None (agnostic)
        assert "crewai" in configs["multi"]

    def test_discover_all_framework_configs_uses_default_root_and_skips_files(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All-framework discovery should use the default root and skip non-package files."""
        from agentic_fabric.core.discovery import discover_all_framework_configs

        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()
        (packages_dir / "README.md").write_text("not a package", encoding="utf-8")

        pkg_dir = packages_dir / "multi"
        (pkg_dir / ".fabric").mkdir(parents=True)
        (pkg_dir / ".fabric" / "manifest.yaml").write_text("name: multi\nfabric_agents: {}\n", encoding="utf-8")
        (pkg_dir / ".strands").mkdir()
        (pkg_dir / ".strands" / "manifest.yaml").write_text("name: multi\nfabric_agents: {}\n", encoding="utf-8")

        (tmp_path / ".langgraph").mkdir()
        (tmp_path / ".langgraph" / "manifest.yaml").write_text("name: root\nfabric_agents: {}\n", encoding="utf-8")
        monkeypatch.setattr("agentic_fabric.core.discovery.get_workspace_root", lambda: tmp_path)

        configs = discover_all_framework_configs()

        assert configs["multi"][None] == pkg_dir / ".fabric"
        assert configs["multi"]["strands"] == pkg_dir / ".strands"
        assert configs[tmp_path.name]["langgraph"] == tmp_path / ".langgraph"

    def test_list_fabric_agents_returns_entries_from_manifest(self, temp_workspace: Path) -> None:
        """Test that list_fabric_agents returns fabric agent definitions from manifest."""
        from agentic_fabric.core.discovery import list_fabric_agents

        with patch(
            "agentic_fabric.core.discovery.discover_packages",
            return_value={"sample": temp_workspace / "packages" / "sample" / ".crewai"},
        ):
            fabric_agents_by_package = list_fabric_agents()

        assert "sample" in fabric_agents_by_package
        fabric_agents = fabric_agents_by_package["sample"]
        assert len(fabric_agents) == 1
        assert fabric_agents[0]["name"] == "test_fabric_agent"

    def test_list_fabric_agents_filters_by_package_name(self, temp_workspace: Path) -> None:
        """Test that list_fabric_agents can filter to a specific package."""
        from agentic_fabric.core.discovery import list_fabric_agents

        with patch(
            "agentic_fabric.core.discovery.discover_packages",
            return_value={"sample": temp_workspace / "packages" / "sample" / ".crewai"},
        ):
            fabric_agents_by_package = list_fabric_agents(package_name="sample")

        assert "sample" in fabric_agents_by_package
        assert len(fabric_agents_by_package) == 1

    def test_list_fabric_agents_returns_empty_for_nonexistent_package(self, temp_workspace: Path) -> None:
        """Test that list_fabric_agents returns empty for non-existent package."""
        from agentic_fabric.core.discovery import list_fabric_agents

        with patch(
            "agentic_fabric.core.discovery.discover_packages",
            return_value={"sample": temp_workspace / "packages" / "sample" / ".crewai"},
        ):
            fabric_agents_by_package = list_fabric_agents(package_name="nonexistent")

        assert fabric_agents_by_package == {}

    def test_load_manifest_parses_yaml(self, temp_workspace: Path) -> None:
        """Test that load_manifest parses YAML correctly."""
        from agentic_fabric.core.discovery import load_manifest

        crewai_dir = temp_workspace / "packages" / "sample" / ".crewai"
        manifest = load_manifest(crewai_dir)

        assert manifest is not None
        assert manifest.get("name") == "sample"
        assert "fabric_agents" in manifest

    def test_get_workspace_root_finds_root(self) -> None:
        """Test that get_workspace_root finds the workspace root."""
        from agentic_fabric.core.discovery import get_workspace_root

        # This should find the actual workspace root
        root = get_workspace_root()

        # Verify it looks like a workspace root
        assert (root / "packages").exists() or root == Path.cwd()

    def test_get_workspace_root_falls_back_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Workspace root discovery should fall back when no markers are found."""
        from agentic_fabric.core import discovery

        module_path = tmp_path / "installed" / "module.py"
        module_path.parent.mkdir()
        module_path.write_text("# module\n", encoding="utf-8")
        monkeypatch.setattr(discovery, "__file__", str(module_path))
        monkeypatch.chdir(tmp_path)

        assert discovery.get_workspace_root() == tmp_path

    def test_get_framework_from_config_dir(self) -> None:
        """Test framework detection from directory name."""
        from agentic_fabric.core.discovery import get_framework_from_config_dir

        assert get_framework_from_config_dir(Path("/some/path/.fabric")) is None
        assert get_framework_from_config_dir(Path("/some/path/.crewai")) == "crewai"
        assert get_framework_from_config_dir(Path("/some/path/.langgraph")) == "langgraph"
        assert get_framework_from_config_dir(Path("/some/path/.strands")) == "strands"

    def test_get_fabric_agent_config_includes_required_framework(self, temp_workspace: Path) -> None:
        """Test that get_fabric_agent_config includes required_framework field."""
        from agentic_fabric.core.discovery import get_fabric_agent_config

        crewai_dir = temp_workspace / "packages" / "sample" / ".crewai"
        config = get_fabric_agent_config(crewai_dir, "test_fabric_agent")

        assert config["required_framework"] == "crewai"

    def test_get_fabric_agent_config_requires_agents_and_tasks_keys(self, tmp_path: Path) -> None:
        """Fabric agent configs should fail before resolving missing YAML paths."""
        from agentic_fabric.core.discovery import get_fabric_agent_config

        fabric_dir = tmp_path / ".fabric"
        fabric_dir.mkdir()
        (fabric_dir / "manifest.yaml").write_text(
            """
name: missing-files
fabric_agents:
  no_agents:
    tasks: tasks.yaml
  no_tasks:
    agents: agents.yaml
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="missing required key: agents"):
            get_fabric_agent_config(fabric_dir, "no_agents")

        with pytest.raises(ValueError, match="missing required key: tasks"):
            get_fabric_agent_config(fabric_dir, "no_tasks")


class TestDecomposer:
    """Tests for the decomposer module."""

    def test_is_framework_available_caches_results(self) -> None:
        """Test that framework availability is cached."""
        from agentic_fabric.core.decomposer import _framework_cache, is_framework_available

        # Clear cache first
        _framework_cache.clear()

        # Check availability (will cache result)
        result1 = is_framework_available("nonexistent_framework")
        result2 = is_framework_available("nonexistent_framework")

        assert result1 is False
        assert result2 is False
        assert "nonexistent_framework" in _framework_cache

    def test_detect_framework_raises_when_none_available(self) -> None:
        """Test that detect_framework raises when no frameworks are available."""
        from agentic_fabric.core.decomposer import detect_framework

        with (
            patch("agentic_fabric.core.decomposer.is_framework_available", return_value=False),
            pytest.raises(RuntimeError, match="No AI frameworks installed"),
        ):
            detect_framework()

    def test_detect_framework_respects_priority(self) -> None:
        """Test that frameworks are detected in priority order."""
        from agentic_fabric.core.decomposer import detect_framework

        def mock_available(framework):
            return framework in ["langgraph", "strands"]

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = detect_framework()

        # langgraph should be preferred over strands
        assert result == "langgraph"

    def test_detect_framework_with_preferred_returns_preferred(self) -> None:
        """Test that detect_framework returns preferred if available."""
        from agentic_fabric.core.decomposer import detect_framework

        def mock_available(framework):
            return framework in ["crewai", "langgraph", "strands"]

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = detect_framework(preferred="strands")

        assert result == "strands"

    def test_detect_framework_falls_back_when_preferred_unavailable(self) -> None:
        """Test that detect_framework falls back when preferred not available."""
        from agentic_fabric.core.decomposer import detect_framework

        def mock_available(framework):
            return framework == "langgraph"

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = detect_framework(preferred="crewai")

        assert result == "langgraph"

    def test_get_available_frameworks_returns_list(self) -> None:
        """Test that get_available_frameworks returns installed frameworks."""
        from agentic_fabric.core.decomposer import get_available_frameworks

        def mock_available(framework):
            return framework in ["crewai", "strands"]

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            side_effect=mock_available,
        ):
            result = get_available_frameworks()

        assert isinstance(result, list)
        assert "crewai" in result
        assert "strands" in result
        assert "langgraph" not in result

    def test_get_available_frameworks_returns_empty_when_none_installed(self) -> None:
        """Test get_available_frameworks returns empty list when none installed."""
        from agentic_fabric.core.decomposer import get_available_frameworks

        with patch(
            "agentic_fabric.core.decomposer.is_framework_available",
            return_value=False,
        ):
            result = get_available_frameworks()

        assert result == []

    def test_get_runner_returns_crewai_runner(self) -> None:
        """Test that get_runner returns CrewAIRunner for crewai."""
        from unittest.mock import MagicMock

        from agentic_fabric.core.decomposer import get_runner

        mock_runner = MagicMock()
        mock_runner.framework_name = "crewai"

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                return_value=True,
            ),
            patch(
                "agentic_fabric.runners.crewai_runner.CrewAIRunner",
                return_value=mock_runner,
            ),
        ):
            runner = get_runner("crewai")

        assert runner is not None
        assert runner.framework_name == "crewai"

    def test_get_runner_returns_langgraph_runner(self) -> None:
        """Test that get_runner returns LangGraphRunner for langgraph."""
        from unittest.mock import MagicMock

        from agentic_fabric.core.decomposer import get_runner

        mock_runner = MagicMock()
        mock_runner.framework_name = "langgraph"

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                return_value=True,
            ),
            patch(
                "agentic_fabric.runners.langgraph_runner.LangGraphRunner",
                return_value=mock_runner,
            ),
        ):
            runner = get_runner("langgraph")

        assert runner is not None
        assert runner.framework_name == "langgraph"

    def test_get_runner_returns_strands_runner(self) -> None:
        """Test that get_runner returns StrandsRunner for strands."""
        from unittest.mock import MagicMock

        from agentic_fabric.core.decomposer import get_runner

        mock_runner = MagicMock()
        mock_runner.framework_name = "strands"

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                return_value=True,
            ),
            patch(
                "agentic_fabric.runners.strands_runner.StrandsRunner",
                return_value=mock_runner,
            ),
        ):
            runner = get_runner("strands")

        assert runner is not None
        assert runner.framework_name == "strands"

    def test_get_runner_auto_detects_framework(self) -> None:
        """Test that get_runner with no args auto-detects framework."""
        from unittest.mock import MagicMock

        from agentic_fabric.core.decomposer import get_runner

        mock_runner = MagicMock()
        mock_runner.framework_name = "strands"

        def mock_available(framework):
            return framework == "strands"

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                side_effect=mock_available,
            ),
            patch(
                "agentic_fabric.runners.strands_runner.StrandsRunner",
                return_value=mock_runner,
            ),
        ):
            runner = get_runner()

        assert runner.framework_name == "strands"

    def test_get_runner_raises_for_unknown_framework(self) -> None:
        """Test that get_runner raises for unknown framework."""
        from agentic_fabric.core.decomposer import get_runner

        with pytest.raises(ValueError, match="Unknown framework"):
            get_runner("unknown_framework")

    def test_compose_fabric_agent_uses_required_framework(self, tmp_path: Path) -> None:
        """Test that compose_fabric_agent respects required_framework from config."""
        from unittest.mock import MagicMock

        from agentic_fabric.core.decomposer import compose_fabric_agent

        fabric_agent_config = {
            "name": "test_fabric_agent",
            "required_framework": "strands",
            "agents": {},
            "tasks": {},
        }

        mock_runner = MagicMock()
        mock_runner.framework_name = "strands"
        mock_runner.build_fabric_agent.return_value = MagicMock()

        def mock_available(framework):
            return framework in ["crewai", "strands"]

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                side_effect=mock_available,
            ),
            patch(
                "agentic_fabric.runners.strands_runner.StrandsRunner",
                return_value=mock_runner,
            ),
        ):
            # compose_fabric_agent returns the result of runner.build_fabric_agent()
            compose_fabric_agent(fabric_agent_config)

        # Verify the runner's build_fabric_agent was called
        mock_runner.build_fabric_agent.assert_called_once_with(fabric_agent_config)

    def test_compose_fabric_agent_raises_when_required_unavailable(self) -> None:
        """Test compose_fabric_agent raises when required framework not available."""
        from agentic_fabric.core.decomposer import compose_fabric_agent

        fabric_agent_config = {
            "name": "test_fabric_agent",
            "required_framework": "langgraph",
            "agents": {},
            "tasks": {},
        }

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                return_value=False,
            ),
            pytest.raises(RuntimeError, match=r"requires langgraph.*not installed"),
        ):
            compose_fabric_agent(fabric_agent_config)

    def test_compose_fabric_agent_validates_framework_conflict(self) -> None:
        """Test compose_fabric_agent validates requested vs required conflict."""
        from agentic_fabric.core.decomposer import compose_fabric_agent

        fabric_agent_config = {
            "name": "test_fabric_agent",
            "required_framework": "crewai",
            "agents": {},
            "tasks": {},
        }

        with (
            patch(
                "agentic_fabric.core.decomposer.is_framework_available",
                return_value=True,
            ),
            pytest.raises(ValueError, match=r"requires crewai.*langgraph was requested"),
        ):
            compose_fabric_agent(fabric_agent_config, framework="langgraph")

    def test_get_install_command_returns_pip_install(self) -> None:
        """Test that _get_install_command returns correct pip command."""
        from agentic_fabric.core.decomposer import _get_install_command

        result = _get_install_command("crewai")
        assert "crewai" in result

    def test_get_install_command_maps_langgraph(self) -> None:
        """Test that _get_install_command maps langgraph correctly."""
        from agentic_fabric.core.decomposer import _get_install_command

        result = _get_install_command("langgraph")
        assert "langgraph" in result
