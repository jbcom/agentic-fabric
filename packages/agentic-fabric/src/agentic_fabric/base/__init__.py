"""Base module - reusable agent archetypes and shared tool re-exports.

Archetypes are base templates that packages can extend in their own
``agents.yaml``. Use the ``extends`` field to inherit from an archetype:

.. code:: yaml

   my_engineer:
     extends: senior_engineer
     variables:
       language: Python
     backstory: |
       {base}
       Additional context specific to my package...

The ``{base}`` placeholder in agent config is replaced with the
archetype's value. ``{language}`` and other ``variables`` are interpolated
into the resolved role/goal/backstory strings.
"""

from __future__ import annotations

import logging

from pathlib import Path
from typing import Any

import yaml

from agentic_fabric.tools.file_tools import (
    DirectoryListTool,
    GameCodeReaderTool,
    GameCodeWriterTool,
)


logger = logging.getLogger(__name__)

_ARCHETYPES_PATH = Path(__file__).parent / "archetypes.yaml"


def _load_archetypes() -> dict[str, dict[str, Any]]:
    """Load built-in archetypes from the bundled YAML file."""
    try:
        data = yaml.safe_load(_ARCHETYPES_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.warning("Could not load archetypes.yaml: %s", exc)
        return {}
    if not isinstance(data, dict):
        return {}
    return data.get("archetypes", {})


def _interpolate(text: str, variables: dict[str, Any]) -> str:
    """Interpolate ``{key}`` placeholders in *text* using *variables*."""
    if not text:
        return text
    try:
        return text.format(**variables)
    except (KeyError, IndexError):
        return text


def resolve_archetype(
    agent_config: dict[str, Any],
    *,
    archetypes: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve ``extends`` and ``variables`` in an agent config.

    If the config has an ``extends`` key, the named archetype is loaded
    and its role/goal/backstory are merged. ``{base}`` in the agent's
    own field is replaced with the archetype's value. Other ``{variables}``
    are interpolated into the final resolved strings.

    Args:
        agent_config: Raw agent config dict that may contain ``extends``
            and ``variables``.
        archetypes: Optional pre-loaded archetypes dict. If ``None``,
            built-in archetypes are loaded from ``archetypes.yaml``.

    Returns:
        New config dict with ``extends`` and ``variables`` consumed
        and all string fields interpolated.
    """
    extends = agent_config.get("extends")
    if not extends:
        return dict(agent_config)

    if archetypes is None:
        archetypes = _load_archetypes()

    archetype = archetypes.get(extends)
    if archetype is None:
        logger.warning("Agent config extends unknown archetype '%s'", extends)
        result = dict(agent_config)
        result.pop("extends", None)
        result.pop("variables", None)
        return result

    variables = agent_config.get("variables", {})
    if not isinstance(variables, dict):
        variables = {}

    resolved: dict[str, Any] = dict(agent_config)
    del resolved["extends"]
    resolved.pop("variables", None)

    for field in ("role", "goal", "backstory"):
        agent_value = agent_config.get(field, "")
        archetype_value = archetype.get(field, "")
        # {base} in the agent's value is replaced with the archetype value
        merged = agent_value.replace("{base}", archetype_value) if agent_value else archetype_value
        resolved[field] = _interpolate(merged, variables)

    # Copy any fields from the archetype not overridden by the agent
    for key, value in archetype.items():
        if key not in resolved:
            resolved[key] = value

    return resolved


def resolve_agent_archetypes(
    agents_config: dict[str, dict[str, Any]],
    *,
    archetypes: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve archetypes for every agent in a config dict.

    Args:
        agents_config: Dict mapping agent names to agent configs.
        archetypes: Optional pre-loaded archetypes dict.

    Returns:
        New dict with archetypes resolved for each agent.
    """
    return {
        name: resolve_archetype(config, archetypes=archetypes)
        for name, config in agents_config.items()
    }


__all__ = [
    "DirectoryListTool",
    "GameCodeReaderTool",
    "GameCodeWriterTool",
    "resolve_agent_archetypes",
    "resolve_archetype",
]
