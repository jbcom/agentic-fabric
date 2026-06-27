"""Tests for runner implementations.

These tests verify the interface contracts for all runner implementations
without requiring the actual frameworks to be installed.
"""

from __future__ import annotations

import builtins
import sys

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from pytest_agentic_fabric.mocking import FabricMocker


def reject_imports(*blocked_names: str):
    """Return an import hook that raises for selected top-level packages."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in blocked_names:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    return fake_import


class TestCrewAIRunner:
    """Tests for CrewAI runner implementation."""

    def test_init_reports_missing_crewai(self, fabric_mocker: FabricMocker) -> None:
        """CrewAI runner construction should explain how to install CrewAI."""
        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        fabric_mocker.patch("builtins.__import__", side_effect=reject_imports("crewai"))

        try:
            CrewAIRunner()
        except RuntimeError as exc:
            assert "pip install crewai" in str(exc)
        else:  # pragma: no cover - defensive if CrewAI import mocking stops working
            raise AssertionError("CrewAIRunner did not report missing CrewAI")

    def test_build_agent_creates_crewai_agent(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_agent creates a CrewAI Agent."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        MockAgent = fabric_mocker.patch_crewai_agent()
        fabric_mocker.patch_get_llm()

        runner = CrewAIRunner()

        agent_config = {
            "role": "Test Agent",
            "goal": "Test goal",
            "backstory": "Test backstory",
            "allow_delegation": True,
        }

        tools = [fabric_mocker.MagicMock()]
        runner.build_agent(agent_config, tools=tools)

        MockAgent.assert_called_once()
        call_kwargs = MockAgent.call_args[1]
        assert call_kwargs["role"] == "Test Agent"
        assert call_kwargs["goal"] == "Test goal"
        assert call_kwargs["backstory"] == "Test backstory"
        assert call_kwargs["allow_delegation"] is True
        assert call_kwargs["tools"] == tools

    def test_build_task_creates_crewai_task(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_task creates a CrewAI Task."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        MockTask = fabric_mocker.patch_crewai_task()

        runner = CrewAIRunner()

        task_config = {
            "description": "Test task description",
            "expected_output": "Test output",
        }
        mock_agent = fabric_mocker.MagicMock()

        runner.build_task(task_config, mock_agent)

        MockTask.assert_called_once()
        call_kwargs = MockTask.call_args[1]
        assert call_kwargs["description"] == "Test task description"
        assert call_kwargs["expected_output"] == "Test output"
        assert call_kwargs["agent"] == mock_agent

    def test_build_task_includes_context(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_task includes context tasks when provided."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        MockTask = fabric_mocker.patch_crewai_task()

        runner = CrewAIRunner()

        task_config = {
            "description": "Test task",
            "expected_output": "Test output",
        }
        mock_agent = fabric_mocker.MagicMock()
        context_tasks = [fabric_mocker.MagicMock(), fabric_mocker.MagicMock()]

        runner.build_task(task_config, mock_agent, context=context_tasks)

        call_kwargs = MockTask.call_args[1]
        assert call_kwargs["context"] == context_tasks

    def test_build_fabric_agent_creates_crewai_crew(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_fabric_agent creates a CrewAI Crew."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        MockCrew = fabric_mocker.patch_crewai_crew()
        MockAgent = fabric_mocker.patch_crewai_agent()
        MockTask = fabric_mocker.patch_crewai_task()
        fabric_mocker.patch_crewai_process()
        fabric_mocker.patch_get_llm()

        runner = CrewAIRunner()

        mock_agent = fabric_mocker.MagicMock()
        MockAgent.return_value = mock_agent

        mock_task = fabric_mocker.MagicMock()
        MockTask.return_value = mock_task

        fabric_agent_config = {
            "name": "test_fabric_agent",
            "agents": {
                "agent1": {
                    "role": "Agent 1",
                    "goal": "Goal 1",
                    "backstory": "Backstory 1",
                }
            },
            "tasks": {
                "task1": {
                    "description": "Task 1",
                    "expected_output": "Output 1",
                    "agent": "agent1",
                }
            },
            "knowledge_paths": [],
        }

        runner.build_fabric_agent(fabric_agent_config)

        MockCrew.assert_called_once()
        call_kwargs = MockCrew.call_args[1]
        assert len(call_kwargs["agents"]) == 1
        assert len(call_kwargs["tasks"]) == 1
        assert call_kwargs["planning"] is True
        assert call_kwargs["memory"] is True

    def test_run_executes_crewai_crew_and_returns_result(self, fabric_mocker: FabricMocker) -> None:
        """Test that run executes fabric_agent and returns string result."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        runner = CrewAIRunner()

        mock_crew = fabric_mocker.mock_crewai_crew(result="Test output")

        result = runner.run(mock_crew, {"input": "test input"})

        mock_crew.kickoff.assert_called_once_with(inputs={"input": "test input"})
        assert result == "Test output"

    def test_run_handles_result_without_raw(self, fabric_mocker: FabricMocker) -> None:
        """Test that run handles results without raw attribute."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        runner = CrewAIRunner()

        mock_crew = fabric_mocker.MagicMock()
        mock_crew.kickoff.return_value = "Direct string result"

        result = runner.run(mock_crew, {})

        assert result == "Direct string result"

    def test_handles_knowledge_sources(self, fabric_mocker: FabricMocker, tmp_path) -> None:
        """Test that knowledge sources are loaded from paths."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        MockKnowledge = fabric_mocker.patch_knowledge_source()

        runner = CrewAIRunner()

        # Create test knowledge file
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        (knowledge_dir / "test.md").write_text("# Test Knowledge\nContent here")

        sources = runner._load_knowledge([knowledge_dir])

        # Verify TextFileKnowledgeSource was called for the .md file
        assert MockKnowledge.called
        assert len(sources) > 0

    def test_handles_task_context_dependencies(self, fabric_mocker: FabricMocker) -> None:
        """Test that tasks with context dependencies are handled correctly."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        fabric_mocker.patch_crewai_crew()
        MockAgent = fabric_mocker.patch_crewai_agent()
        MockTask = fabric_mocker.patch_crewai_task()
        fabric_mocker.patch_crewai_process()
        fabric_mocker.patch_get_llm()

        runner = CrewAIRunner()

        mock_agent = fabric_mocker.MagicMock()
        MockAgent.return_value = mock_agent

        mock_task1 = fabric_mocker.MagicMock()
        mock_task2 = fabric_mocker.MagicMock()
        MockTask.side_effect = [mock_task1, mock_task2]

        fabric_agent_config = {
            "agents": {
                "agent1": {
                    "role": "Agent",
                    "goal": "Goal",
                    "backstory": "Story",
                }
            },
            "tasks": {
                "task1": {
                    "description": "Task 1",
                    "expected_output": "Output 1",
                    "agent": "agent1",
                },
                "task2": {
                    "description": "Task 2",
                    "expected_output": "Output 2",
                    "agent": "agent1",
                    "context": ["task1"],
                },
            },
            "knowledge_paths": [],
        }

        runner.build_fabric_agent(fabric_agent_config)

        # Verify second task was created with context
        assert MockTask.call_count == 2
        second_task_kwargs = MockTask.call_args_list[1][1]
        assert "context" in second_task_kwargs
        assert second_task_kwargs["context"] == [mock_task1]

    def test_build_fabric_agent_warns_for_unresolved_context_dependencies(
        self,
        fabric_mocker: FabricMocker,
        caplog,
    ) -> None:
        """Unresolved task context references should be visible to callers."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        fabric_mocker.patch_crewai_crew()
        fabric_mocker.patch_crewai_agent()
        fabric_mocker.patch_crewai_task()
        fabric_mocker.patch_crewai_process()
        fabric_mocker.patch_get_llm()

        runner = CrewAIRunner()
        fabric_agent_config = {
            "agents": {"agent1": {"role": "Agent", "goal": "Goal", "backstory": "Story"}},
            "tasks": {
                "task1": {
                    "description": "Task 1",
                    "expected_output": "Output 1",
                    "agent": "agent1",
                    "context": ["later_task"],
                }
            },
            "knowledge_paths": [],
        }

        runner.build_fabric_agent(fabric_agent_config)

        assert "references context tasks that are not yet available: later_task" in caplog.text

    def test_build_fabric_agent_resolves_declared_tools(self, fabric_mocker: FabricMocker) -> None:
        """Tool names declared in agent config should be instantiated and attached."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        fabric_mocker.patch_crewai_crew()
        MockAgent = fabric_mocker.patch_crewai_agent()
        fabric_mocker.patch_crewai_task()
        fabric_mocker.patch_crewai_process()
        fabric_mocker.patch_get_llm()

        resolved_tool = fabric_mocker.MagicMock()

        runner = CrewAIRunner()
        runner._resolve_tools = fabric_mocker.MagicMock(return_value=[resolved_tool])

        fabric_agent_config = {
            "agents": {
                "agent1": {
                    "role": "Agent 1",
                    "goal": "Goal 1",
                    "backstory": "Backstory 1",
                    "tools": ["FileWriteTool"],
                }
            },
            "tasks": {
                "task1": {
                    "description": "Task 1",
                    "expected_output": "Output 1",
                    "agent": "agent1",
                }
            },
            "knowledge_paths": [],
        }

        runner.build_fabric_agent(fabric_agent_config)

        runner._resolve_tools.assert_called_once_with(["FileWriteTool"])
        assert MockAgent.call_args[1]["tools"] == [resolved_tool]

    def test_build_fabric_agent_rejects_tasks_with_unknown_agents(self, fabric_mocker: FabricMocker) -> None:
        """CrewAI tasks must reference agents declared in the fabric_agent config."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        runner = CrewAIRunner()

        fabric_agent_config = {
            "agents": {},
            "tasks": {"task1": {"description": "Task", "agent": "missing"}},
        }

        try:
            runner.build_fabric_agent(fabric_agent_config)
        except ValueError as exc:
            assert "invalid agent: missing" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("CrewAIRunner accepted a task with an unknown agent")

    def test_load_knowledge_skips_non_directories_and_logs_read_errors(
        self,
        fabric_mocker: FabricMocker,
        tmp_path,
    ) -> None:
        """Knowledge loading should skip bad paths and tolerate unreadable files."""
        fabric_mocker.mock_crewai()

        from agentic_fabric.runners.crewai_runner import CrewAIRunner

        fabric_mocker.patch_knowledge_source()
        runner = CrewAIRunner()
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        bad_file = knowledge_dir / "bad.md"
        bad_file.write_text("content", encoding="utf-8")
        original_read_text = type(bad_file).read_text

        def fake_read_text(self, *args: Any, **kwargs: Any) -> str:
            if self == bad_file:
                raise OSError("cannot read")
            return original_read_text(self, *args, **kwargs)

        fabric_mocker.patch.object(type(bad_file), "read_text", fake_read_text)

        assert runner._load_knowledge([tmp_path / "missing", knowledge_dir]) == []


class TestLangGraphRunner:
    """Tests for LangGraph runner implementation."""

    def test_init_reports_missing_langgraph(self, fabric_mocker: FabricMocker) -> None:
        """LangGraph runner construction should explain how to install LangGraph."""
        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        fabric_mocker.patch("builtins.__import__", side_effect=reject_imports("langgraph"))

        try:
            LangGraphRunner()
        except RuntimeError as exc:
            assert 'pip install "agentic-fabric[langgraph]"' in str(exc)
        else:  # pragma: no cover - defensive if LangGraph import mocking stops working
            raise AssertionError("LangGraphRunner did not report missing LangGraph")

    def test_build_agent_creates_react_agent(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_agent creates a LangGraph ReAct agent."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        mock_create = fabric_mocker.patch_create_react_agent()
        MockLLM = fabric_mocker.patch_chat_anthropic()
        mock_llm = fabric_mocker.MagicMock()
        MockLLM.return_value = mock_llm

        runner = LangGraphRunner()

        agent_config = {
            "role": "Test Agent",
            "goal": "Test goal",
            "llm": "claude-sonnet-4-20250514",
        }
        tools = [fabric_mocker.MagicMock()]

        runner.build_agent(agent_config, tools=tools)

        mock_create.assert_called_once()
        args = mock_create.call_args[0]
        assert args[0] == mock_llm
        assert args[1] == tools

    def test_build_fabric_agent_creates_graph(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_fabric_agent creates a LangGraph workflow."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        mock_create = fabric_mocker.patch_create_react_agent()
        fabric_mocker.patch_chat_anthropic()

        runner = LangGraphRunner()

        fabric_agent_config = {
            "llm": {"model": "claude-sonnet-4-20250514"},
            "agents": {},
            "tasks": {},
        }

        runner.build_fabric_agent(fabric_agent_config)

        mock_create.assert_called_once()

    def test_run_invokes_graph(self, fabric_mocker: FabricMocker) -> None:
        """Test that run invokes the LangGraph workflow."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        runner = LangGraphRunner()

        mock_graph = fabric_mocker.mock_langgraph_graph(result="Test response")

        result = runner.run(mock_graph, {"input": "test prompt"})

        mock_graph.invoke.assert_called_once()
        invoke_args = mock_graph.invoke.call_args[0][0]
        assert "messages" in invoke_args
        assert result == "Test response"

    def test_run_handles_dict_messages(self, fabric_mocker: FabricMocker) -> None:
        """Test that run handles dictionary message format."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        runner = LangGraphRunner()

        mock_graph = fabric_mocker.MagicMock()
        mock_graph.invoke.return_value = {"messages": [("assistant", "Test response")]}

        runner.run(mock_graph, {"task": "test task"})

        mock_graph.invoke.assert_called_once()
        invoke_args = mock_graph.invoke.call_args[0][0]
        assert "messages" in invoke_args
        assert any("test task" in str(msg) for msg in invoke_args["messages"])

    def test_run_returns_raw_result_when_no_messages(self, fabric_mocker: FabricMocker) -> None:
        """LangGraph runner should stringify results that do not contain messages."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        runner = LangGraphRunner()
        mock_graph = fabric_mocker.MagicMock()
        mock_graph.invoke.return_value = {"state": "done"}

        assert runner.run(mock_graph, {"other": "value"}) == "{'state': 'done'}"

    def test_get_llm_returns_chat_anthropic(self, fabric_mocker: FabricMocker) -> None:
        """Test that get_llm returns ChatAnthropic instance."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        MockLLM = fabric_mocker.patch_chat_anthropic()

        runner = LangGraphRunner()
        runner.get_llm("claude-sonnet-4-20250514")

        MockLLM.assert_called_once_with(model="claude-sonnet-4-20250514")

    def test_get_llm_uses_default_model(self, fabric_mocker: FabricMocker) -> None:
        """Test that get_llm uses default model when none specified."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        MockLLM = fabric_mocker.patch_chat_anthropic()

        runner = LangGraphRunner()
        runner.get_llm()

        MockLLM.assert_called_once()
        assert MockLLM.call_args[1]["model"] == "claude-haiku-4-5-20251001"

    def test_build_task_returns_dict(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_task returns task configuration dict."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        runner = LangGraphRunner()

        task_config = {
            "description": "Test task",
            "expected_output": "Test output",
        }
        mock_agent = fabric_mocker.MagicMock()

        result = runner.build_task(task_config, mock_agent)

        assert isinstance(result, dict)
        assert result["description"] == "Test task"
        assert result["expected_output"] == "Test output"
        assert result["agent"] == mock_agent

    def test_handles_multi_agent_flows(self, fabric_mocker: FabricMocker) -> None:
        """Test that multiple agents can be created for complex flows."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        mock_create = fabric_mocker.patch_create_react_agent()
        fabric_mocker.patch_chat_anthropic()

        runner = LangGraphRunner()

        # Create multiple agents
        agent1_config = {"role": "Agent 1", "goal": "Goal 1"}
        agent2_config = {"role": "Agent 2", "goal": "Goal 2"}

        runner.build_agent(agent1_config)
        runner.build_agent(agent2_config)

        # Verify create_react_agent was called twice
        assert mock_create.call_count == 2

    def test_build_fabric_agent_resolves_declared_tools(self, fabric_mocker: FabricMocker) -> None:
        """Configured agent tools should be adapted for LangGraph fabric_agents."""
        fabric_mocker.mock_langgraph()

        from agentic_fabric.runners.langgraph_runner import LangGraphRunner

        mock_create = fabric_mocker.patch_create_react_agent()
        fabric_mocker.patch_chat_anthropic()
        resolved_tool = fabric_mocker.MagicMock()
        fabric_mocker.patch("agentic_fabric.runners.langgraph_runner.resolve_langgraph_tools", return_value=[resolved_tool])

        runner = LangGraphRunner()
        fabric_agent_config = {
            "llm": {"model": "claude-sonnet-4-20250514"},
            "agents": {
                "researcher": {
                    "tools": ["ScrapeWebsiteTool"],
                }
            },
            "tasks": {},
        }

        runner.build_fabric_agent(fabric_agent_config)

        mock_create.assert_called_once()
        assert mock_create.call_args[0][1] == [resolved_tool]


class TestStrandsRunner:
    """Tests for Strands runner implementation."""

    def test_init_reports_missing_strands(self, fabric_mocker: FabricMocker) -> None:
        """Strands runner construction should explain how to install Strands."""
        from agentic_fabric.runners.strands_runner import StrandsRunner

        fabric_mocker.patch("builtins.__import__", side_effect=reject_imports("strands"))

        try:
            StrandsRunner()
        except RuntimeError as exc:
            assert 'pip install "agentic-fabric[strands]"' in str(exc)
        else:  # pragma: no cover - defensive if Strands import mocking stops working
            raise AssertionError("StrandsRunner did not report missing Strands")

    def test_build_agent_creates_strands_agent(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_agent creates a Strands Agent."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        MockAgent = fabric_mocker.patch_strands_agent()

        runner = StrandsRunner()

        agent_config = {
            "role": "Test Agent",
            "goal": "Test goal",
            "backstory": "Test backstory",
        }
        tools = [fabric_mocker.MagicMock()]

        runner.build_agent(agent_config, tools=tools)

        MockAgent.assert_called_once()
        call_kwargs = MockAgent.call_args[1]
        assert "Test Agent" in call_kwargs["system_prompt"]
        assert "Test goal" in call_kwargs["system_prompt"]
        assert "Test backstory" in call_kwargs["system_prompt"]
        assert call_kwargs["tools"] == tools

    def test_build_system_prompt_combines_agent_prompts(self, fabric_mocker: FabricMocker) -> None:
        """Test that _build_system_prompt combines multiple agent roles."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        fabric_agent_config = {
            "description": "Test fabric_agent description",
            "agents": {
                "agent1": {
                    "role": "Agent One",
                    "goal": "Goal one",
                },
                "agent2": {
                    "role": "Agent Two",
                    "goal": "Goal two",
                },
            },
            "tasks": {
                "task1": {
                    "description": "Task one description",
                }
            },
        }

        prompt = runner._build_system_prompt(fabric_agent_config)

        assert "Test fabric_agent description" in prompt
        assert "Agent One" in prompt
        assert "Agent Two" in prompt
        assert "Goal one" in prompt
        assert "Goal two" in prompt
        assert "task1" in prompt

    def test_build_system_prompt_truncates_long_descriptions(self, fabric_mocker: FabricMocker) -> None:
        """Test that long task descriptions are truncated."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        long_desc = "A" * 250
        fabric_agent_config = {
            "tasks": {
                "task1": {
                    "description": long_desc,
                }
            },
        }

        prompt = runner._build_system_prompt(fabric_agent_config)

        # Should be truncated to 200 chars + ellipsis
        assert "..." in prompt
        assert prompt.count("A") == 200

    def test_build_system_prompt_keeps_short_descriptions(self, fabric_mocker: FabricMocker) -> None:
        """Test that short task descriptions are not truncated."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        short_desc = "Short description"
        fabric_agent_config = {
            "tasks": {
                "task1": {
                    "description": short_desc,
                }
            },
        }

        prompt = runner._build_system_prompt(fabric_agent_config)

        # Should not have ellipsis for short descriptions
        assert "..." not in prompt
        assert short_desc in prompt

    def test_run_returns_string_result(self, fabric_mocker: FabricMocker) -> None:
        """Test that run executes agent and returns string result."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        mock_agent = fabric_mocker.mock_strands_agent(result="Test agent response")

        result = runner.run(mock_agent, {"input": "test prompt"})

        mock_agent.assert_called_once_with("test prompt")
        assert result == "Test agent response"

    def test_run_handles_task_input(self, fabric_mocker: FabricMocker) -> None:
        """Test that run handles 'task' key in inputs."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        mock_agent = fabric_mocker.mock_strands_agent(result="Response")

        runner.run(mock_agent, {"task": "do something"})

        mock_agent.assert_called_once_with("do something")

    def test_get_model_provider_from_string(self, fabric_mocker: FabricMocker) -> None:
        """Test extracting model provider from string config."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        result = runner._get_model_provider("claude-3-5-sonnet")

        assert result == "claude-3-5-sonnet"

    def test_get_model_provider_from_dict(self, fabric_mocker: FabricMocker) -> None:
        """Test extracting model provider from dict config."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        result = runner._get_model_provider({"model": "claude-3-5-sonnet", "provider": "anthropic"})

        assert result == "claude-3-5-sonnet"

    def test_get_model_provider_returns_none_for_empty(self, fabric_mocker: FabricMocker) -> None:
        """Test that None is returned when no config provided."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        result = runner._get_model_provider(None)

        assert result is None

    def test_build_fabric_agent_creates_strands_agent(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_fabric_agent creates a Strands agent."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        MockAgent = fabric_mocker.patch_strands_agent()

        runner = StrandsRunner()

        fabric_agent_config = {
            "description": "Test fabric_agent",
            "llm": {"model": "claude-3-5-sonnet"},
            "agents": {},
            "tasks": {},
        }

        runner.build_fabric_agent(fabric_agent_config)

        MockAgent.assert_called_once()
        call_kwargs = MockAgent.call_args[1]
        assert "system_prompt" in call_kwargs
        assert call_kwargs["model_id"] == "claude-3-5-sonnet"

    def test_build_task_returns_dict(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_task returns task configuration dict."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        runner = StrandsRunner()

        task_config = {
            "description": "Test task",
            "expected_output": "Test output",
        }
        mock_agent = fabric_mocker.MagicMock()

        result = runner.build_task(task_config, mock_agent)

        assert isinstance(result, dict)
        assert result["description"] == "Test task"
        assert result["expected_output"] == "Test output"
        assert result["agent"] == mock_agent

    def test_combines_agent_prompts(self, fabric_mocker: FabricMocker) -> None:
        """Test that multiple agent capabilities are combined into system prompt."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        MockAgent = fabric_mocker.patch_strands_agent()

        runner = StrandsRunner()

        fabric_agent_config = {
            "description": "Multi-capability fabric_agent",
            "agents": {
                "researcher": {"role": "Researcher", "goal": "Research topics"},
                "writer": {"role": "Writer", "goal": "Write content"},
            },
            "tasks": {},
        }

        runner.build_fabric_agent(fabric_agent_config)

        call_kwargs = MockAgent.call_args[1]
        system_prompt = call_kwargs["system_prompt"]

        # Verify both agent capabilities are in the prompt
        assert "Researcher" in system_prompt
        assert "Writer" in system_prompt
        assert "Research topics" in system_prompt
        assert "Write content" in system_prompt

    def test_build_fabric_agent_resolves_declared_tools(self, fabric_mocker: FabricMocker) -> None:
        """Configured agent tools should be adapted for Strands fabric_agents."""
        fabric_mocker.mock_strands()

        from agentic_fabric.runners.strands_runner import StrandsRunner

        MockAgent = fabric_mocker.patch_strands_agent()
        resolved_tool = fabric_mocker.MagicMock()
        fabric_mocker.patch("agentic_fabric.runners.strands_runner.resolve_strands_tools", return_value=[resolved_tool])

        runner = StrandsRunner()
        fabric_agent_config = {
            "description": "Test fabric_agent",
            "agents": {
                "writer": {
                    "tools": ["FileWriteTool"],
                }
            },
            "tasks": {},
        }

        runner.build_fabric_agent(fabric_agent_config)

        assert MockAgent.call_args[1]["tools"] == [resolved_tool]


class TestBaseRunner:
    """Tests for base runner interface."""

    def test_build_and_run_convenience_method(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_and_run calls build_fabric_agent and run with correct args."""
        from agentic_fabric.runners.base import BaseRunner

        class TestRunner(BaseRunner):
            # Define abstract methods so the class can be instantiated
            def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
                pass

            def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
                pass

            def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
                return fabric_mocker.MagicMock()

            def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
                return fabric_mocker.MagicMock()

        runner = TestRunner()

        # Mock the methods to verify they're called correctly
        mock_fabric_agent_obj = fabric_mocker.MagicMock()
        runner.build_fabric_agent = fabric_mocker.MagicMock(return_value=mock_fabric_agent_obj)
        runner.run = fabric_mocker.MagicMock(return_value="test result")

        fabric_agent_config = {"test": "config"}
        inputs = {"test": "input"}

        result = runner.build_and_run(fabric_agent_config, inputs)

        assert result == "test result"
        runner.build_fabric_agent.assert_called_once_with(fabric_agent_config)
        runner.run.assert_called_once_with(mock_fabric_agent_obj, inputs)

    def test_build_and_run_uses_empty_inputs_when_none(self, fabric_mocker: FabricMocker) -> None:
        """Test that build_and_run uses empty dict when inputs is None."""
        from agentic_fabric.runners.base import BaseRunner

        class TestRunner(BaseRunner):
            def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
                return fabric_mocker.MagicMock()

            def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
                assert inputs == {}
                return "result"

            def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
                return fabric_mocker.MagicMock()

            def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
                return fabric_mocker.MagicMock()

        runner = TestRunner()
        result = runner.build_and_run({}, None)

        assert result == "result"

    def test_get_llm_default_implementation(self, fabric_mocker: FabricMocker) -> None:
        """Test that get_llm has a default implementation."""
        mock_get_llm = fabric_mocker.patch_get_llm()
        fabric_mocker.patch("agentic_fabric.config.llm.DEFAULT_MODEL", "claude-sonnet-4-20250514")

        from agentic_fabric.runners.base import BaseRunner

        class TestRunner(BaseRunner):
            def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
                return fabric_mocker.MagicMock()

            def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
                return "result"

            def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
                return fabric_mocker.MagicMock()

            def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
                return fabric_mocker.MagicMock()

        runner = TestRunner()
        llm = runner.get_llm()

        assert llm == mock_get_llm.return_value

    def test_get_llm_returns_none_when_module_unavailable(self, fabric_mocker: FabricMocker) -> None:
        """Test that get_llm returns None when llm module not available."""
        from agentic_fabric.runners.base import BaseRunner

        class TestRunner(BaseRunner):
            def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
                return fabric_mocker.MagicMock()

            def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
                return "result"

            def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
                return fabric_mocker.MagicMock()

            def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
                return fabric_mocker.MagicMock()

        runner = TestRunner()

        # Simulate that the agentic_fabric.config.llm module is not available
        fabric_mocker.patch.dict(sys.modules, {"agentic_fabric.config.llm": None})
        llm = runner.get_llm()

        assert llm is None
