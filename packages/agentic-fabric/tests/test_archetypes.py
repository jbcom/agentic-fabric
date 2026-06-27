"""Tests for the agent archetype resolution system."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_fabric.base import resolve_agent_archetypes, resolve_archetype


class TestResolveArchetype:
    """Tests for resolve_archetype."""

    def test_no_extends_returns_copy(self) -> None:
        config: dict[str, Any] = {"role": "Engineer", "goal": "Write code"}
        result = resolve_archetype(config)
        assert result == config
        assert result is not config

    def test_extends_inherits_role_goal_backstory(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior Engineer",
                "goal": "Write quality code",
                "backstory": "10 years of experience",
            }
        }
        config: dict[str, Any] = {"extends": "senior_engineer"}
        result = resolve_archetype(config, archetypes=archetypes)
        assert result["role"] == "Senior Engineer"
        assert result["goal"] == "Write quality code"
        assert result["backstory"] == "10 years of experience"
        assert "extends" not in result

    def test_extends_with_variables_interpolation(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior {language} Engineer",
                "goal": "Write {language} code",
                "backstory": "10 years of experience",
            }
        }
        config: dict[str, Any] = {
            "extends": "senior_engineer",
            "variables": {"language": "Python"},
        }
        result = resolve_archetype(config, archetypes=archetypes)
        assert result["role"] == "Senior Python Engineer"
        assert result["goal"] == "Write Python code"
        assert "variables" not in result

    def test_base_placeholder_replaced_with_archetype_value(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior Engineer",
                "goal": "Write quality code",
                "backstory": "You have 10 years of experience.",
            }
        }
        config: dict[str, Any] = {
            "extends": "senior_engineer",
            "backstory": "{base}\nAdditional context for my package.",
        }
        result = resolve_archetype(config, archetypes=archetypes)
        assert result["backstory"] == "You have 10 years of experience.\nAdditional context for my package."

    def test_agent_overrides_archetype_field(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior Engineer",
                "goal": "Write quality code",
                "backstory": "10 years of experience",
            }
        }
        config: dict[str, Any] = {
            "extends": "senior_engineer",
            "goal": "Custom goal override",
        }
        result = resolve_archetype(config, archetypes=archetypes)
        assert result["role"] == "Senior Engineer"
        assert result["goal"] == "Custom goal override"

    def test_unknown_archetype_warns_and_returns_copy(self) -> None:
        config: dict[str, Any] = {"extends": "nonexistent", "role": "Agent"}
        result = resolve_archetype(config, archetypes={})
        assert result["role"] == "Agent"
        assert "extends" not in result

    def test_archetype_fields_copied_when_not_in_agent(self) -> None:
        archetypes = {
            "architect": {
                "role": "Software Architect",
                "goal": "Design systems",
                "backstory": "Expert architect",
            }
        }
        config: dict[str, Any] = {"extends": "architect", "role": "My Architect"}
        result = resolve_archetype(config, archetypes=archetypes)
        assert result["role"] == "My Architect"
        assert result["goal"] == "Design systems"
        assert result["backstory"] == "Expert architect"

    def test_missing_variable_leaves_placeholder(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior {language} Engineer",
                "goal": "Write code",
                "backstory": "Experienced",
            }
        }
        config: dict[str, Any] = {"extends": "senior_engineer"}
        result = resolve_archetype(config, archetypes=archetypes)
        # Missing variable means the placeholder is left as-is
        assert "{language}" in result["role"]

    def test_variables_not_a_dict_treated_as_empty(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior {language} Engineer",
                "goal": "Write code",
                "backstory": "Experienced",
            }
        }
        config: dict[str, Any] = {"extends": "senior_engineer", "variables": "not a dict"}
        result = resolve_archetype(config, archetypes=archetypes)
        assert "{language}" in result["role"]

    def test_interpolate_returns_empty_string_for_empty_text(self) -> None:
        """_interpolate should return empty text unchanged (no formatting)."""
        from agentic_fabric.base import _interpolate

        assert _interpolate("", {"x": "y"}) == ""

    def test_archetype_extra_field_copied_into_resolved(self) -> None:
        """Fields beyond role/goal/backstory should be copied from the archetype."""
        archetypes = {
            "senior_engineer": {
                "role": "Senior Engineer",
                "goal": "Write code",
                "backstory": "Experienced",
                "max_delegation": 3,
            }
        }
        config: dict[str, Any] = {"extends": "senior_engineer"}
        result = resolve_archetype(config, archetypes=archetypes)

        assert result["max_delegation"] == 3


class TestResolveAgentArchetypes:
    """Tests for resolve_agent_archetypes (batch)."""

    def test_resolves_multiple_agents(self) -> None:
        archetypes = {
            "senior_engineer": {
                "role": "Senior {language} Engineer",
                "goal": "Write {language} code",
                "backstory": "Experienced",
            }
        }
        agents_config = {
            "engineer1": {
                "extends": "senior_engineer",
                "variables": {"language": "Python"},
            },
            "plain_agent": {
                "role": "Plain Agent",
                "goal": "Do things",
            },
        }
        result = resolve_agent_archetypes(agents_config, archetypes=archetypes)
        assert result["engineer1"]["role"] == "Senior Python Engineer"
        assert result["plain_agent"]["role"] == "Plain Agent"

    def test_empty_config(self) -> None:
        result = resolve_agent_archetypes({}, archetypes={})
        assert result == {}


def test_builtin_archetypes_load() -> None:
    """The bundled archetypes.yaml loads and contains known archetypes."""
    from agentic_fabric.base import _load_archetypes

    archetypes = _load_archetypes()
    assert "senior_engineer" in archetypes
    assert "qa_engineer" in archetypes
    assert "technical_lead" in archetypes
    assert "architect" in archetypes
    assert "designer" in archetypes


class TestLoadArchetypesEdgeCases:
    """Tests for _load_archetypes error and edge-case handling."""

    def test_returns_empty_on_oserror(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An OSError reading archetypes.yaml should log and return empty dict."""
        from pathlib import Path

        from agentic_fabric import base

        monkeypatch.setattr(base, "_ARCHETYPES_PATH", Path("/nonexistent/path/archetypes.yaml"))

        assert base._load_archetypes() == {}

    def test_returns_empty_when_data_not_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-dict YAML content should produce an empty archetypes dict."""
        from agentic_fabric import base

        monkeypatch.setattr(base.yaml, "safe_load", lambda *a: ["not", "a", "dict"])

        assert base._load_archetypes() == {}

    def test_returns_empty_when_archetypes_key_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A dict without an 'archetypes' key should yield an empty dict."""
        from agentic_fabric import base

        monkeypatch.setattr(base.yaml, "safe_load", lambda *a: {"other": "stuff"})

        assert base._load_archetypes() == {}


def test_resolve_archetype_loads_from_file_when_archetypes_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """resolve_archetype should call _load_archetypes when archetypes is None."""
    from agentic_fabric import base

    monkeypatch.setattr(
        base,
        "_load_archetypes",
        lambda: {"senior_engineer": {"role": "Senior Engineer", "goal": "Write code", "backstory": "Experienced"}},
    )

    result = base.resolve_archetype({"extends": "senior_engineer"})
    assert result["role"] == "Senior Engineer"
    assert result["goal"] == "Write code"


def test_resolve_agent_archetypes_with_empty_variables_dict() -> None:
    """An explicit empty variables dict should resolve cleanly."""
    archetypes = {
        "senior_engineer": {
            "role": "Senior Engineer",
            "goal": "Write code",
            "backstory": "Experienced",
        }
    }
    agents_config = {"engineer": {"extends": "senior_engineer", "variables": {}}}

    result = resolve_agent_archetypes(agents_config, archetypes=archetypes)

    assert result["engineer"]["role"] == "Senior Engineer"
    assert result["engineer"]["goal"] == "Write code"
    assert "variables" not in result["engineer"]
    assert "extends" not in result["engineer"]
