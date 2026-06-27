"""Tests for YAML configuration parsing error handling."""

from __future__ import annotations

import logging

from pathlib import Path

import pytest
import yaml

from agentic_fabric.core.discovery import (
    get_fabric_agent_config,
    get_framework_from_config_dir,
    load_manifest,
)


def write_empty_agent_task_files(config_dir: Path) -> None:
    """Write minimal valid agents/tasks YAML files for config-loading tests."""
    (config_dir / "agents.yaml").write_text("{}\n", encoding="utf-8")
    (config_dir / "tasks.yaml").write_text("{}\n", encoding="utf-8")


class TestLoadManifestErrors:
    """Test error handling in load_manifest."""

    def test_missing_manifest_file_raises(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing manifest."""
        with pytest.raises(FileNotFoundError):
            load_manifest(tmp_path / "nonexistent")

    def test_empty_manifest_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty YAML file should return empty dict, not None."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text("")
        result = load_manifest(tmp_path)
        assert result == {}

    def test_manifest_with_only_comments_returns_empty_dict(self, tmp_path: Path) -> None:
        """YAML with only comments should return empty dict."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text("# just a comment\n# another comment\n")
        result = load_manifest(tmp_path)
        assert result == {}

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Badly formed YAML should raise a yaml error."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(":\n  bad:\n    - ][invalid yaml")
        with pytest.raises(yaml.YAMLError):
            load_manifest(tmp_path)

    def test_non_mapping_manifest_raises_type_error(self, tmp_path: Path) -> None:
        """Manifest root must be a mapping."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text("- not\n- a mapping\n", encoding="utf-8")

        with pytest.raises(TypeError, match="must contain a mapping"):
            load_manifest(tmp_path)

    def test_manifest_with_no_fabric_agents_key(self, tmp_path: Path) -> None:
        """Manifest without 'fabric_agents' key should parse without error."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text("name: test_package\ndescription: A test\n")
        result = load_manifest(tmp_path)
        assert result.get("name") == "test_package"
        assert result.get("fabric_agents") is None


class TestGetFabricAgentConfigErrors:
    """Test error handling in get_fabric_agent_config."""

    def test_fabric_agent_not_in_manifest_raises_value_error(self, tmp_path: Path) -> None:
        """Requesting a non-existent fabric_agent should raise ValueError."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  existing_fabric_agent:\n"
            "    description: An existing fabric_agent\n"
            "    agents: fabric_agents/existing/agents.yaml\n"
            "    tasks: fabric_agents/existing/tasks.yaml\n"
        )
        with pytest.raises(ValueError, match="Fabric agent 'nonexistent' not found"):
            get_fabric_agent_config(tmp_path, "nonexistent")

    def test_error_lists_available_fabric_agents(self, tmp_path: Path) -> None:
        """ValueError message should list available fabric_agent names."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  alpha_fabric_agent:\n"
            "    agents: a.yaml\n"
            "    tasks: t.yaml\n"
            "  beta_fabric_agent:\n"
            "    agents: a.yaml\n"
            "    tasks: t.yaml\n"
        )
        with pytest.raises(ValueError, match="alpha_fabric_agent") as exc_info:
            get_fabric_agent_config(tmp_path, "missing")
        assert "beta_fabric_agent" in str(exc_info.value)

    def test_missing_agents_yaml_raises_file_not_found(self, tmp_path: Path) -> None:
        """Missing agents YAML should fail as a manifest contract error."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    description: Test\n"
            "    agents: nonexistent_agents.yaml\n"
            "    tasks: tasks.yaml\n"
        )
        (tmp_path / "tasks.yaml").write_text("{}\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Agents file not found"):
            get_fabric_agent_config(tmp_path, "test_fabric_agent")

    def test_missing_tasks_yaml_raises_file_not_found(self, tmp_path: Path) -> None:
        """Missing tasks YAML should fail as a manifest contract error."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    description: Test\n"
            "    agents: agents.yaml\n"
            "    tasks: nonexistent_tasks.yaml\n"
        )
        (tmp_path / "agents.yaml").write_text("{}\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Tasks file not found"):
            get_fabric_agent_config(tmp_path, "test_fabric_agent")

    def test_non_mapping_agents_or_tasks_yaml_raises_type_error(self, tmp_path: Path) -> None:
        """Agents and tasks YAML roots must be mappings."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n",
            encoding="utf-8",
        )
        (tmp_path / "agents.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")
        (tmp_path / "tasks.yaml").write_text("{}\n", encoding="utf-8")

        with pytest.raises(TypeError, match="mapping of agents"):
            get_fabric_agent_config(tmp_path, "test_fabric_agent")

        (tmp_path / "agents.yaml").write_text("{}\n", encoding="utf-8")
        (tmp_path / "tasks.yaml").write_text("- not\n- a mapping\n", encoding="utf-8")

        with pytest.raises(TypeError, match="mapping of tasks"):
            get_fabric_agent_config(tmp_path, "test_fabric_agent")

    def test_empty_agents_and_tasks_yaml_return_empty_mappings(self, tmp_path: Path) -> None:
        """Empty but present agents/tasks files should load as empty mappings."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n",
            encoding="utf-8",
        )
        (tmp_path / "agents.yaml").write_text("", encoding="utf-8")
        (tmp_path / "tasks.yaml").write_text("", encoding="utf-8")

        config = get_fabric_agent_config(tmp_path, "test_fabric_agent")

        assert config["agents"] == {}
        assert config["tasks"] == {}

    def test_agents_and_tasks_yaml_are_read_as_utf8(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Agents and tasks YAML should use explicit UTF-8 decoding."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n",
            encoding="utf-8",
        )
        (tmp_path / "agents.yaml").write_text("agent:\n  role: Café reviewer\n", encoding="utf-8")
        (tmp_path / "tasks.yaml").write_text("task:\n  description: Résumé review\n", encoding="utf-8")
        original_read_text = Path.read_text
        encodings: list[str | None] = []

        def tracking_read_text(self: Path, *args, **kwargs) -> str:
            if self.name in {"agents.yaml", "tasks.yaml"}:
                encodings.append(kwargs.get("encoding"))
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", tracking_read_text)

        config = get_fabric_agent_config(tmp_path, "test_fabric_agent")

        assert config["agents"]["agent"]["role"] == "Café reviewer"
        assert config["tasks"]["task"]["description"] == "Résumé review"
        assert encodings == ["utf-8", "utf-8"]

    def test_empty_fabric_agents_section_raises_for_any_fabric_agent(self, tmp_path: Path) -> None:
        """Empty fabric_agents section should raise ValueError."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text("fabric_agents: {}\n")
        with pytest.raises(ValueError, match="not found"):
            get_fabric_agent_config(tmp_path, "anything")

    def test_knowledge_paths_resolves_relative(self, tmp_path: Path) -> None:
        """Knowledge paths should resolve relative to config dir."""
        # Create the knowledge directory
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        (knowledge_dir / "docs.md").write_text("# Docs")

        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n  test_fabric_agent:\n    agents: agents.yaml\n    tasks: tasks.yaml\n    knowledge:\n      - knowledge\n"
        )
        write_empty_agent_task_files(tmp_path)
        config = get_fabric_agent_config(tmp_path, "test_fabric_agent")
        assert len(config["knowledge_paths"]) == 1
        assert config["knowledge_paths"][0] == knowledge_dir

    def test_nonexistent_knowledge_paths_excluded(self, tmp_path: Path) -> None:
        """Non-existent knowledge paths should be silently excluded."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n"
            "    knowledge:\n"
            "      - missing_dir\n"
        )
        write_empty_agent_task_files(tmp_path)
        config = get_fabric_agent_config(tmp_path, "test_fabric_agent")
        assert config["knowledge_paths"] == []

    def test_knowledge_file_paths_excluded(self, tmp_path: Path) -> None:
        """Knowledge paths must be directories, not plain files."""
        (tmp_path / "knowledge.md").write_text("# Not a directory")
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n"
            "    knowledge:\n"
            "      - knowledge.md\n"
        )
        write_empty_agent_task_files(tmp_path)

        config = get_fabric_agent_config(tmp_path, "test_fabric_agent")

        assert config["knowledge_paths"] == []

    def test_agents_path_cannot_escape_config_dir(self, tmp_path: Path) -> None:
        """Manifest agents paths must stay inside the config directory."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: ../outside_agents.yaml\n"
            "    tasks: tasks.yaml\n"
        )

        with pytest.raises(ValueError, match="Manifest path must be relative"):
            get_fabric_agent_config(tmp_path, "test_fabric_agent")

    def test_agents_symlink_path_cannot_escape_config_dir(self, tmp_path: Path) -> None:
        """Resolved symlinks must not escape the config directory."""
        config_dir = tmp_path / ".fabric"
        config_dir.mkdir()
        outside = tmp_path / "outside_agents.yaml"
        outside.write_text("agent: {}\n", encoding="utf-8")
        link_path = config_dir / "agents-link.yaml"
        try:
            link_path.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"symlinks unavailable: {exc}")

        manifest_file = config_dir / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents-link.yaml\n"
            "    tasks: tasks.yaml\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Manifest path escapes config directory"):
            get_fabric_agent_config(config_dir, "test_fabric_agent")

    def test_knowledge_path_cannot_escape_config_dir(self, tmp_path: Path) -> None:
        """Manifest knowledge paths must stay inside the config directory."""
        manifest_file = tmp_path / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n"
            "    knowledge:\n"
            "      - ../knowledge\n"
        )
        write_empty_agent_task_files(tmp_path)

        with pytest.raises(ValueError, match="Manifest path must be relative"):
            get_fabric_agent_config(tmp_path, "test_fabric_agent")


class TestGetFrameworkFromConfigDir:
    """Test edge cases for get_framework_from_config_dir."""

    def test_unknown_directory_name_returns_none(self) -> None:
        """Unknown directory name should return None."""
        result = get_framework_from_config_dir(Path("/path/.unknown"))
        assert result is None

    def test_non_hidden_directory_returns_none(self) -> None:
        """Non-hidden directory name should return None."""
        result = get_framework_from_config_dir(Path("/path/crewai"))
        assert result is None

    def test_all_known_dirs_return_expected_framework(self) -> None:
        """All known framework directories should map correctly."""
        expected = {
            ".fabric": None,
            ".crewai": "crewai",
            ".langgraph": "langgraph",
            ".strands": "strands",
        }
        for dir_name, framework in expected.items():
            result = get_framework_from_config_dir(Path(f"/any/path/{dir_name}"))
            assert result == framework, f"Expected {framework} for {dir_name}, got {result}"


class TestCrewConfigFrameworkConflict:
    """Test framework conflict warnings in get_fabric_agent_config."""

    def test_framework_mismatch_logs_warning(self, tmp_path: Path, caplog) -> None:
        """When manifest preferred_framework differs from directory, warn."""
        crewai_dir = tmp_path / ".crewai"
        crewai_dir.mkdir()

        manifest_file = crewai_dir / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    description: Test\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n"
            "    preferred_framework: strands\n"
        )
        write_empty_agent_task_files(crewai_dir)
        with caplog.at_level(logging.WARNING):
            config = get_fabric_agent_config(crewai_dir, "test_fabric_agent")
        assert "preferred_framework=strands" in caplog.text
        assert "requires crewai" in caplog.text
        # required_framework should still be crewai (directory wins)
        assert config["required_framework"] == "crewai"

    def test_matching_preferred_framework_no_warning(self, tmp_path: Path, caplog) -> None:
        """When preferred_framework matches directory, no warning."""
        crewai_dir = tmp_path / ".crewai"
        crewai_dir.mkdir()

        manifest_file = crewai_dir / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    description: Test\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n"
            "    preferred_framework: crewai\n"
        )
        write_empty_agent_task_files(crewai_dir)
        with caplog.at_level(logging.WARNING):
            get_fabric_agent_config(crewai_dir, "test_fabric_agent")
        assert "preferred_framework" not in caplog.text

    def test_preferred_auto_no_warning(self, tmp_path: Path, caplog) -> None:
        """preferred_framework='auto' should not trigger warning."""
        crewai_dir = tmp_path / ".crewai"
        crewai_dir.mkdir()

        manifest_file = crewai_dir / "manifest.yaml"
        manifest_file.write_text(
            "fabric_agents:\n"
            "  test_fabric_agent:\n"
            "    description: Test\n"
            "    agents: agents.yaml\n"
            "    tasks: tasks.yaml\n"
            "    preferred_framework: auto\n"
        )
        write_empty_agent_task_files(crewai_dir)
        with caplog.at_level(logging.WARNING):
            get_fabric_agent_config(crewai_dir, "test_fabric_agent")
        assert "preferred_framework" not in caplog.text
