"""Tests for the ManagerAgent class."""

from __future__ import annotations

import asyncio

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_fabric.core.manager import ManagerAgent


class TestManagerAgent:
    """Tests for ManagerAgent base class."""

    def test_init_with_fabric_agents(self):
        """Test manager initialization with fabric agent mappings."""
        fabric_agents = {"design": "game_design", "qa": "quality_assurance"}
        manager = ManagerAgent(fabric_agents=fabric_agents)

        assert manager.fabric_agents == fabric_agents
        assert manager.package_name is None
        assert manager.workspace_root is None

    def test_init_with_package_name(self):
        """Test manager initialization with package name."""
        fabric_agents = {"design": "game_design"}
        manager = ManagerAgent(fabric_agents=fabric_agents, package_name="my_package")

        assert manager.package_name == "my_package"

    def test_get_packages_caches_result(self):
        """Test that package discovery is cached."""
        manager = ManagerAgent(fabric_agents={"test": "test_fabric_agent"})

        with patch("agentic_fabric.core.manager.discover_packages") as mock_discover:
            mock_packages = {"pkg1": Path("/path/pkg1")}
            mock_discover.return_value = mock_packages

            # First call
            result1 = manager._get_packages()
            assert result1 == mock_packages
            assert mock_discover.call_count == 1

            # Second call should use cache
            result2 = manager._get_packages()
            assert result2 == mock_packages
            assert mock_discover.call_count == 1  # Not called again

    def test_delegate_with_string_input(self):
        """Test delegation with string input."""
        manager = ManagerAgent(
            fabric_agents={"design": "game_design"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}
        mock_config = {
            "name": "game_design",
            "agents": {},
            "tasks": {},
        }

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.return_value = mock_config
            mock_run.return_value = "Design complete"

            result = manager.delegate("design", "Create a game design")

            assert result == "Design complete"
            # Verify string was converted to dict
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["inputs"] == {"task": "Create a game design"}

    def test_delegate_with_dict_input(self):
        """Test delegation with dict input."""
        manager = ManagerAgent(
            fabric_agents={"design": "game_design"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}
        mock_config = {"name": "game_design", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.return_value = mock_config
            mock_run.return_value = "Design complete"

            inputs = {"task": "Create design", "theme": "fantasy"}
            result = manager.delegate("design", inputs)

            assert result == "Design complete"
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[1]["inputs"] == inputs

    def test_delegate_unknown_role_raises_error(self):
        """Test that delegating to unknown role raises ValueError."""
        manager = ManagerAgent(fabric_agents={"design": "game_design"})

        with pytest.raises(ValueError, match="Unknown fabric agent role 'unknown'"):
            manager.delegate("unknown", "test task")

    def test_delegate_package_not_found_raises_error(self):
        """Test that missing package raises ValueError."""
        manager = ManagerAgent(
            fabric_agents={"design": "game_design"},
            package_name="nonexistent",
        )

        with patch("agentic_fabric.core.manager.discover_packages") as mock_discover:
            mock_discover.return_value = {"other_pkg": Path("/other")}

            with pytest.raises(ValueError, match="Package 'nonexistent' not found"):
                manager.delegate("design", "test task")

    def test_delegate_auto_discovers_fabric_agent(self):
        """Test auto-discovery of a fabric agent when package_name is not specified."""
        manager = ManagerAgent(fabric_agents={"design": "game_design"})

        mock_packages = {
            "pkg1": Path("/pkg1/.fabric"),
            "pkg2": Path("/pkg2/.fabric"),
        }
        mock_config = {"name": "game_design", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages

            # First package doesn't have the fabric agent.
            def get_config_side_effect(pkg_dir, fabric_agent_name):
                if pkg_dir == Path("/pkg1/.fabric"):
                    raise ValueError("Fabric agent not found")
                return mock_config

            mock_get_config.side_effect = get_config_side_effect
            mock_run.return_value = "Success"

            result = manager.delegate("design", "test task")

            assert result == "Success"
            # Should have tried pkg1 (failed), then found in pkg2 (config is cached)
            assert mock_get_config.call_count == 2

    def test_delegate_uses_cached_fabric_agent_config(self):
        """Repeated delegation to the same fabric agent should reuse the cached config."""
        manager = ManagerAgent(fabric_agents={"design": "game_design"}, package_name="test_pkg")
        mock_config = {"name": "game_design", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages", return_value={"test_pkg": Path("/test/.fabric")}),
            patch("agentic_fabric.core.manager.get_fabric_agent_config", return_value=mock_config) as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto", side_effect=["first", "second"]) as mock_run,
        ):
            assert manager.delegate("design", "first task", framework="crewai") == "first"
            assert manager.delegate("design", {"task": "second task"}, framework="langgraph") == "second"

        mock_get_config.assert_called_once_with(Path("/test/.fabric"), "game_design")
        assert mock_run.call_args_list[1].kwargs == {"inputs": {"task": "second task"}, "framework": "langgraph"}

    def test_delegate_fabric_agent_not_found_raises_error(self):
        """Test that fabric agent not found in any package raises ValueError."""
        manager = ManagerAgent(fabric_agents={"design": "missing_fabric_agent"})

        mock_packages = {"pkg1": Path("/pkg1/.fabric")}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.side_effect = ValueError("Fabric agent not found")

            with pytest.raises(ValueError, match="Fabric agent 'missing_fabric_agent' not found"):
                manager.delegate("design", "test task")

    @pytest.mark.asyncio
    async def test_delegate_async(self):
        """Test async delegation."""
        manager = ManagerAgent(
            fabric_agents={"design": "game_design"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}
        mock_config = {"name": "game_design", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.return_value = mock_config
            mock_run.return_value = "Async result"

            result = await manager.delegate_async("design", "test task")

            assert result == "Async result"

    @pytest.mark.asyncio
    async def test_delegate_parallel(self):
        """Test parallel delegation to multiple fabric agents."""
        manager = ManagerAgent(
            fabric_agents={"design": "game_design", "assets": "asset_gen"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages

            # Return different configs for different fabric agents to distinguish them.
            def get_config_side_effect(pkg_dir, fabric_agent_name):
                return {"name": fabric_agent_name, "agents": {}, "tasks": {}}

            mock_get_config.side_effect = get_config_side_effect

            # Mock different results based on fabric agent name in config.
            def run_side_effect(config, inputs, framework=None):
                fabric_agent_name = config["name"]
                if fabric_agent_name == "game_design":
                    return "Design done"
                elif fabric_agent_name == "asset_gen":
                    return "Assets done"
                return f"Unknown fabric agent: {fabric_agent_name}"

            mock_run.side_effect = run_side_effect

            results = await manager.delegate_parallel(
                [
                    ("design", "Create design"),
                    ("assets", "Generate assets"),
                ]
            )

            # Verify correct results returned (order matches input order)
            assert results == ["Design done", "Assets done"]
            # Both should have been executed
            assert mock_run.call_count == 2

    def test_delegate_sequential(self):
        """Test sequential delegation to multiple fabric agents."""
        manager = ManagerAgent(
            fabric_agents={"design": "game_design", "impl": "implementation"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}
        mock_config = {"name": "test", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.return_value = mock_config
            mock_run.side_effect = ["Design result", "Implementation result"]

            results = manager.delegate_sequential(
                [
                    ("design", "Create design"),
                    ("impl", "Implement design"),
                ]
            )

            assert results == ["Design result", "Implementation result"]
            assert mock_run.call_count == 2
            # Verify they were called in order
            calls = mock_run.call_args_list
            assert calls[0][1]["inputs"]["task"] == "Create design"
            assert calls[1][1]["inputs"]["task"] == "Implement design"

    def test_checkpoint_auto_approve(self):
        """Test checkpoint with auto_approve=True."""
        manager = ManagerAgent(fabric_agents={"test": "test_fabric_agent"})

        approved, result = manager.checkpoint(
            "Review design",
            "Design output",
            auto_approve=True,
        )

        assert approved is True
        assert result == "Design output"

    def test_checkpoint_base_implementation_auto_approves(self):
        """Test that base checkpoint implementation auto-approves."""
        manager = ManagerAgent(fabric_agents={"test": "test_fabric_agent"})

        approved, result = manager.checkpoint(
            "Review design",
            "Design output",
            auto_approve=False,  # Even with False, base impl approves
        )

        assert approved is True
        assert result == "Design output"

    def test_execute_workflow_not_implemented(self):
        """Test that execute_workflow raises NotImplementedError in base class."""
        manager = ManagerAgent(fabric_agents={"test": "test_fabric_agent"})

        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            asyncio.run(manager.execute_workflow("test task"))


class TestManagerAgentSubclass:
    """Tests for ManagerAgent subclass implementation."""

    @pytest.mark.asyncio
    async def test_custom_workflow_implementation(self):
        """Test a custom manager implementation."""

        class TestManager(ManagerAgent):
            async def execute_workflow(self, task: str, **kwargs):
                # Simple sequential workflow
                design = await self.delegate_async("design", task)
                return await self.delegate_async("impl", design)

        manager = TestManager(
            fabric_agents={"design": "game_design", "impl": "implementation"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}
        mock_config = {"name": "test", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.return_value = mock_config
            mock_run.side_effect = ["Design done", "Implementation done"]

            result = await manager.execute_workflow("Build a game")

            assert result == "Implementation done"
            assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_workflow_with_parallel_execution(self):
        """Test a custom manager with parallel execution."""

        class ParallelManager(ManagerAgent):
            async def execute_workflow(self, task: str, **kwargs):
                # Parallel execution
                results = await self.delegate_parallel(
                    [
                        ("design", task),
                        ("assets", task),
                    ]
                )
                # Then sequential QA
                return await self.delegate_async(
                    "qa",
                    {
                        "design": results[0],
                        "assets": results[1],
                    },
                )

        manager = ParallelManager(
            fabric_agents={"design": "design", "assets": "assets", "qa": "qa"},
            package_name="test_pkg",
        )

        mock_packages = {"test_pkg": Path("/test/.fabric")}
        mock_config = {"name": "test", "agents": {}, "tasks": {}}

        with (
            patch("agentic_fabric.core.manager.discover_packages") as mock_discover,
            patch("agentic_fabric.core.manager.get_fabric_agent_config") as mock_get_config,
            patch("agentic_fabric.core.manager.run_fabric_agent_auto") as mock_run,
        ):
            mock_discover.return_value = mock_packages
            mock_get_config.return_value = mock_config
            mock_run.side_effect = ["Design done", "Assets done", "QA passed"]

            result = await manager.execute_workflow("Build game")

            assert result == "QA passed"
            assert mock_run.call_count == 3
