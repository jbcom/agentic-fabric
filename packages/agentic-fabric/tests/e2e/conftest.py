"""E2E test configuration.

Fixtures and CLI options are provided by pytest-agentic-fabric plugin.
This file is kept for any project-specific customizations.
"""

from __future__ import annotations

# All fixtures come from tests/conftest.py:
# - check_api_key
# - check_aws_credentials
# - simple_agent_config
# - simple_task_config
# - simple_fabric_agent_config
# - multi_agent_fabric_agent_config
# - fabric_agent_with_knowledge
# - temp_fabric_dir
#
# CLI options:
# - --e2e: Enable E2E tests
# - --framework=<name>: Filter by framework
