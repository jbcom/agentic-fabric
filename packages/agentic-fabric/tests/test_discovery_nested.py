"""Tests for fabric_agent discovery in nested directories and edge cases."""

from __future__ import annotations

from pathlib import Path

from agentic_fabric.core.discovery import (
    DIR_TO_FRAMEWORK,
    FRAMEWORK_DIRS,
    FRAMEWORK_TO_DIR,
    discover_all_framework_configs,
    discover_packages,
)


class TestDiscoverPackagesNested:
    """Test discovery across nested directory structures."""

    def test_skips_non_directory_entries(self, tmp_path: Path) -> None:
        """Files in the packages/ directory should be ignored."""
        packages_dir = tmp_path / "packages"
        packages_dir.mkdir()

        # Create a file (not a directory) in packages/
        (packages_dir / "README.md").write_text("# Packages")

        # Create a real package too
        pkg_dir = packages_dir / "real_pkg"
        fabric_dir = pkg_dir / ".fabric"
        fabric_dir.mkdir(parents=True)
        (fabric_dir / "manifest.yaml").write_text("name: real\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path)
        assert "real_pkg" in packages
        assert "README.md" not in packages

    def test_standalone_project_at_root(self, tmp_path: Path) -> None:
        """A .fabric directory at workspace root should be discovered."""
        fabric_dir = tmp_path / ".fabric"
        fabric_dir.mkdir()
        (fabric_dir / "manifest.yaml").write_text("name: root_project\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path)
        assert tmp_path.name in packages

    def test_standalone_and_packages_coexist(self, tmp_path: Path) -> None:
        """Root .fabric and packages/.fabric should both be discovered."""
        # Root level .fabric
        root_fabric = tmp_path / ".fabric"
        root_fabric.mkdir()
        (root_fabric / "manifest.yaml").write_text("name: root\nfabric_agents: {}")

        # Package level .fabric
        pkg_dir = tmp_path / "packages" / "sub_pkg"
        pkg_fabric = pkg_dir / ".fabric"
        pkg_fabric.mkdir(parents=True)
        (pkg_fabric / "manifest.yaml").write_text("name: sub\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path)
        assert "sub_pkg" in packages
        assert tmp_path.name in packages

    def test_packages_dir_not_present(self, tmp_path: Path) -> None:
        """When there is no packages/ directory, only root is checked."""
        packages = discover_packages(workspace_root=tmp_path)
        assert packages == {}

    def test_packages_path_as_file_is_ignored(self, tmp_path: Path) -> None:
        """A file named packages should not crash package discovery."""
        (tmp_path / "packages").write_text("not a directory")

        packages = discover_packages(workspace_root=tmp_path)

        assert packages == {}

    def test_framework_filter_crewai(self, tmp_path: Path) -> None:
        """Filtering by framework='crewai' should only find .crewai dirs."""
        pkg_dir = tmp_path / "packages" / "test_pkg"

        # Create .fabric (agnostic) and .crewai (specific)
        fabric_dir = pkg_dir / ".fabric"
        fabric_dir.mkdir(parents=True)
        (fabric_dir / "manifest.yaml").write_text("name: test\nfabric_agents: {}")

        crewai_dir = pkg_dir / ".crewai"
        crewai_dir.mkdir()
        (crewai_dir / "manifest.yaml").write_text("name: test\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path, framework="crewai")
        assert "test_pkg" in packages
        assert packages["test_pkg"].name == ".crewai"

    def test_framework_filter_no_match(self, tmp_path: Path) -> None:
        """Filtering by framework with no matching dirs returns empty."""
        pkg_dir = tmp_path / "packages" / "test_pkg"
        crewai_dir = pkg_dir / ".crewai"
        crewai_dir.mkdir(parents=True)
        (crewai_dir / "manifest.yaml").write_text("name: test\nfabric_agents: {}")

        packages = discover_packages(workspace_root=tmp_path, framework="strands")
        assert packages == {}

    def test_missing_manifest_skips_directory(self, tmp_path: Path) -> None:
        """A .crewai directory without manifest.yaml should be skipped."""
        pkg_dir = tmp_path / "packages" / "test_pkg"
        crewai_dir = pkg_dir / ".crewai"
        crewai_dir.mkdir(parents=True)
        # No manifest.yaml created

        packages = discover_packages(workspace_root=tmp_path)
        assert packages == {}

    def test_file_shaped_config_path_is_skipped(self, tmp_path: Path) -> None:
        """A file named like a config directory should not be discovered."""
        pkg_dir = tmp_path / "packages" / "test_pkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / ".fabric").write_text("not a directory", encoding="utf-8")
        (tmp_path / ".langgraph").write_text("not a directory", encoding="utf-8")

        packages = discover_packages(workspace_root=tmp_path)

        assert packages == {}

    def test_multiple_packages_discovered(self, tmp_path: Path) -> None:
        """Multiple packages should all be discovered."""
        packages_dir = tmp_path / "packages"
        for name in ["alpha", "beta", "gamma"]:
            fabric_dir = packages_dir / name / ".fabric"
            fabric_dir.mkdir(parents=True)
            (fabric_dir / "manifest.yaml").write_text(f"name: {name}\nfabric_agents: {{}}")

        packages = discover_packages(workspace_root=tmp_path)
        assert set(packages.keys()) == {"alpha", "beta", "gamma"}


class TestDiscoverAllFrameworkConfigs:
    """Test discover_all_framework_configs."""

    def test_multiple_frameworks_per_package(self, tmp_path: Path) -> None:
        """A package with .fabric, .crewai, and .strands should return all."""
        pkg_dir = tmp_path / "packages" / "multi"

        for dir_name in [".fabric", ".crewai", ".strands"]:
            fw_dir = pkg_dir / dir_name
            fw_dir.mkdir(parents=True)
            (fw_dir / "manifest.yaml").write_text(f"name: multi\nframework_dir: {dir_name}\nfabric_agents: {{}}")

        configs = discover_all_framework_configs(workspace_root=tmp_path)

        assert "multi" in configs
        assert None in configs["multi"]  # .fabric -> agnostic
        assert "crewai" in configs["multi"]
        assert "strands" in configs["multi"]

    def test_root_configs_discovered(self, tmp_path: Path) -> None:
        """Root-level framework configs should be discovered."""
        fabric_dir = tmp_path / ".langgraph"
        fabric_dir.mkdir()
        (fabric_dir / "manifest.yaml").write_text("name: root\nfabric_agents: {}")

        configs = discover_all_framework_configs(workspace_root=tmp_path)
        assert tmp_path.name in configs
        assert "langgraph" in configs[tmp_path.name]

    def test_empty_workspace(self, tmp_path: Path) -> None:
        """An empty workspace should return empty dict."""
        configs = discover_all_framework_configs(workspace_root=tmp_path)
        assert configs == {}

    def test_packages_path_as_file_is_ignored(self, tmp_path: Path) -> None:
        """A file named packages should not crash all-framework discovery."""
        (tmp_path / "packages").write_text("not a directory")

        configs = discover_all_framework_configs(workspace_root=tmp_path)

        assert configs == {}


class TestFrameworkConstants:
    """Test the framework constant mappings."""

    def test_dir_to_framework_completeness(self) -> None:
        """Every entry in FRAMEWORK_DIRS should have a DIR_TO_FRAMEWORK entry."""
        for dir_name in FRAMEWORK_DIRS:
            assert dir_name in DIR_TO_FRAMEWORK

    def test_framework_to_dir_completeness(self) -> None:
        """Every framework in DIR_TO_FRAMEWORK should have a FRAMEWORK_TO_DIR entry."""
        for framework in DIR_TO_FRAMEWORK.values():
            assert framework in FRAMEWORK_TO_DIR

    def test_round_trip_mapping(self) -> None:
        """DIR_TO_FRAMEWORK -> FRAMEWORK_TO_DIR should be a round trip."""
        for dir_name, framework in DIR_TO_FRAMEWORK.items():
            assert FRAMEWORK_TO_DIR[framework] == dir_name
