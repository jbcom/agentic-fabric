"""E2E test configuration.

Fixtures and CLI options are provided by pytest-agentic-fabric plugin.
This file is kept for any project-specific customizations.

E2E tests use the published pytest-agentic-fabric markers:
- ``@pytest.mark.agentic_e2e`` — skip unless ``--agentic-e2e`` is passed
- ``@pytest.mark.agentic_runtime("crewai")`` — skip unless framework is installed

For backward compatibility, the local ``--e2e`` flag and ``e2e``/``crewai``/
``langgraph``/``strands`` markers from ``tests/conftest.py`` are also supported.
"""

from __future__ import annotations
