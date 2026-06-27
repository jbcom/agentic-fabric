"""Mocking helpers for tests that exercise agentic-fabric integrations."""

from __future__ import annotations

import sys

from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Any

import pytest


if TYPE_CHECKING:
    from pytest_mock import MockerFixture


CREWAI_MODULES: tuple[str, ...] = (
    "crewai",
    "crewai.knowledge",
    "crewai.knowledge.source",
    "crewai.knowledge.source.text_file_knowledge_source",
)
LANGGRAPH_MODULES: tuple[str, ...] = ("langgraph", "langgraph.prebuilt", "langchain_anthropic")
STRANDS_MODULES: tuple[str, ...] = ("strands",)
RUNTIME_MODULES: dict[str, tuple[str, ...]] = {
    "crewai": CREWAI_MODULES,
    "langgraph": LANGGRAPH_MODULES,
    "strands": STRANDS_MODULES,
}
ALL_FRAMEWORK_MODULES: tuple[str, ...] = (*CREWAI_MODULES, *LANGGRAPH_MODULES, *STRANDS_MODULES)


@dataclass
class FabricMocker:
    """Convenience wrapper around pytest-mock for optional agent runtime tests."""

    mocker: MockerFixture
    mocked_modules: dict[str, ModuleType] = field(default_factory=dict)
    _original_modules: dict[str, ModuleType] = field(default_factory=dict)
    _original_parent_attrs: dict[tuple[str, str], Any] = field(default_factory=dict)
    _missing_parent_attrs: set[tuple[str, str]] = field(default_factory=set)

    @property
    def MagicMock(self) -> Any:
        """Return ``mocker.MagicMock`` for direct test customization."""
        return self.mocker.MagicMock

    @property
    def Mock(self) -> Any:
        """Return ``mocker.Mock`` for direct test customization."""
        return self.mocker.Mock

    @property
    def patch(self) -> Any:
        """Return ``mocker.patch`` for direct test customization."""
        return self.mocker.patch

    @property
    def spy(self) -> Any:
        """Return ``mocker.spy`` for direct test customization."""
        return self.mocker.spy

    @property
    def stub(self) -> Any:
        """Return ``mocker.stub`` for direct test customization."""
        return self.mocker.stub

    def mock_module(self, module_name: str) -> ModuleType:
        """Install one fake import module and return it."""
        if module_name in self.mocked_modules:
            return self.mocked_modules[module_name]

        module = ModuleType(module_name)
        if any(name.startswith(f"{module_name}.") for name in ALL_FRAMEWORK_MODULES):
            module.__path__ = []  # type: ignore[attr-defined]

        original = sys.modules.get(module_name)
        if isinstance(original, ModuleType):
            self._original_modules[module_name] = original
        sys.modules[module_name] = module
        self.mocked_modules[module_name] = module
        self._attach_to_parent(module_name, module)
        return module

    def mock_modules(self, module_names: Iterable[str]) -> dict[str, ModuleType]:
        """Install multiple fake import modules."""
        return {name: self.mock_module(name) for name in module_names}

    def restore_modules(self) -> None:
        """Restore fake modules and parent module attributes."""
        for module_name in list(self.mocked_modules):
            if module_name in self._original_modules:
                sys.modules[module_name] = self._original_modules[module_name]
            else:
                sys.modules.pop(module_name, None)

        for parent_name, child_name in self._missing_parent_attrs:
            parent = sys.modules.get(parent_name)
            if parent is not None and hasattr(parent, child_name):
                delattr(parent, child_name)

        for (parent_name, child_name), value in self._original_parent_attrs.items():
            parent = sys.modules.get(parent_name)
            if parent is not None:
                setattr(parent, child_name, value)

        self.mocked_modules.clear()
        self._original_modules.clear()
        self._original_parent_attrs.clear()
        self._missing_parent_attrs.clear()

    def mock_crewai(self) -> dict[str, ModuleType]:
        """Install fake CrewAI modules with common entry points."""
        modules = self.mock_modules(CREWAI_MODULES)
        setattr(modules["crewai"], "Agent", self.mocker.MagicMock())
        setattr(modules["crewai"], "Crew", self.mocker.MagicMock())
        setattr(modules["crewai"], "Task", self.mocker.MagicMock())
        setattr(modules["crewai"], "Process", self.mocker.MagicMock())
        setattr(
            modules["crewai.knowledge.source.text_file_knowledge_source"],
            "TextFileKnowledgeSource",
            self.mocker.MagicMock(),
        )
        return modules

    def mock_crewai_agent(self, **kwargs: Any) -> Any:
        """Create a standalone CrewAI agent mock."""
        return self._mock_with_attrs(**kwargs)

    def mock_crewai_task(self, **kwargs: Any) -> Any:
        """Create a standalone CrewAI task mock."""
        return self._mock_with_attrs(**kwargs)

    def mock_crewai_crew(self, result: str = "Test result", **kwargs: Any) -> Any:
        """Create a CrewAI crew mock whose ``kickoff`` returns a raw result."""
        mock_crew = self._mock_with_attrs(**kwargs)
        mock_result = self.mocker.MagicMock()
        mock_result.raw = result
        mock_crew.kickoff.return_value = mock_result
        return mock_crew

    def patch_crewai_agent(self) -> Any:
        """Patch ``crewai.Agent`` and return the patch mock."""
        self._ensure_crewai()
        return self.mocker.patch("crewai.Agent", create=True)

    def patch_crewai_task(self) -> Any:
        """Patch ``crewai.Task`` and return the patch mock."""
        self._ensure_crewai()
        return self.mocker.patch("crewai.Task", create=True)

    def patch_crewai_crew(self) -> Any:
        """Patch ``crewai.Crew`` and return the patch mock."""
        self._ensure_crewai()
        return self.mocker.patch("crewai.Crew", create=True)

    def patch_crewai_process(self) -> Any:
        """Patch ``crewai.Process`` and return the patch mock."""
        self._ensure_crewai()
        return self.mocker.patch("crewai.Process", create=True)

    def patch_knowledge_source(self) -> Any:
        """Patch or return the CrewAI text-file knowledge source mock."""
        self._ensure_crewai()
        module = self.mocked_modules["crewai.knowledge.source.text_file_knowledge_source"]
        return getattr(module, "TextFileKnowledgeSource")

    def mock_langgraph(self) -> dict[str, ModuleType]:
        """Install fake LangGraph modules with common entry points."""
        modules = self.mock_modules(LANGGRAPH_MODULES)
        setattr(modules["langgraph.prebuilt"], "create_react_agent", self.mocker.MagicMock())
        setattr(modules["langchain_anthropic"], "ChatAnthropic", self.mocker.MagicMock())
        return modules

    def patch_create_react_agent(self) -> Any:
        """Patch or return ``langgraph.prebuilt.create_react_agent``."""
        self._ensure_langgraph()
        return getattr(self.mocked_modules["langgraph.prebuilt"], "create_react_agent")

    def patch_chat_anthropic(self) -> Any:
        """Patch or return ``langchain_anthropic.ChatAnthropic``."""
        self._ensure_langgraph()
        return getattr(self.mocked_modules["langchain_anthropic"], "ChatAnthropic")

    def mock_langgraph_graph(self, result: str = "Test response") -> Any:
        """Create a LangGraph graph mock whose ``invoke`` returns one message."""
        mock_graph = self.mocker.MagicMock()
        mock_message = self.mocker.MagicMock()
        mock_message.content = result
        mock_graph.invoke.return_value = {"messages": [mock_message]}
        return mock_graph

    def mock_strands(self) -> dict[str, ModuleType]:
        """Install fake Strands modules with common entry points."""
        modules = self.mock_modules(STRANDS_MODULES)
        setattr(modules["strands"], "Agent", self.mocker.MagicMock())
        return modules

    def patch_strands_agent(self) -> Any:
        """Patch or return ``strands.Agent``."""
        self._ensure_strands()
        return getattr(self.mocked_modules["strands"], "Agent")

    def mock_strands_agent(self, result: str = "Test response") -> Any:
        """Create a Strands agent mock whose call returns text."""
        mock_agent = self.mocker.MagicMock()
        mock_agent.return_value = result
        return mock_agent

    def mock_all_frameworks(self) -> dict[str, ModuleType]:
        """Install all supported optional runtime modules."""
        return {**self.mock_crewai(), **self.mock_langgraph(), **self.mock_strands()}

    def patch_get_llm(self, return_value: Any = None) -> Any:
        """Patch ``agentic_fabric.config.llm.get_llm``."""
        mock = self.mocker.patch("agentic_fabric.config.llm.get_llm")
        mock.return_value = self.mocker.MagicMock() if return_value is None else return_value
        return mock

    def patch_discover_packages(self, packages: dict[str, Any] | None = None) -> Any:
        """Patch ``agentic_fabric.core.discovery.discover_packages``."""
        mock = self.mocker.patch("agentic_fabric.core.discovery.discover_packages")
        mock.return_value = {} if packages is None else packages
        return mock

    def patch_get_fabric_agent_config(self, config: dict[str, Any] | None = None) -> Any:
        """Patch ``agentic_fabric.core.discovery.get_fabric_agent_config``."""
        mock = self.mocker.patch("agentic_fabric.core.discovery.get_fabric_agent_config")
        mock.return_value = {"name": "test", "agents": {}, "tasks": {}} if config is None else config
        return mock

    def patch_run_fabric_agent_auto(self, result: str = "Test result") -> Any:
        """Patch ``agentic_fabric.core.decomposer.run_fabric_agent_auto``."""
        mock = self.mocker.patch("agentic_fabric.core.decomposer.run_fabric_agent_auto")
        mock.return_value = result
        return mock

    def _attach_to_parent(self, module_name: str, module: ModuleType) -> None:
        """Attach a child module to an already mocked parent module."""
        parent_name, separator, child_name = module_name.rpartition(".")
        if not separator or parent_name not in sys.modules:
            return

        parent = sys.modules[parent_name]
        key = (parent_name, child_name)
        if key not in self._original_parent_attrs and key not in self._missing_parent_attrs:
            if hasattr(parent, child_name):
                self._original_parent_attrs[key] = getattr(parent, child_name)
            else:
                self._missing_parent_attrs.add(key)
        setattr(parent, child_name, module)

    def _ensure_crewai(self) -> None:
        """Ensure CrewAI modules are mocked."""
        if "crewai" not in self.mocked_modules:
            self.mock_crewai()

    def _ensure_langgraph(self) -> None:
        """Ensure LangGraph modules are mocked."""
        if "langgraph" not in self.mocked_modules:
            self.mock_langgraph()

    def _ensure_strands(self) -> None:
        """Ensure Strands modules are mocked."""
        if "strands" not in self.mocked_modules:
            self.mock_strands()

    def _mock_with_attrs(self, **kwargs: Any) -> Any:
        """Create a mock object with supplied attributes."""
        mock = self.mocker.MagicMock()
        for key, value in kwargs.items():
            setattr(mock, key, value)
        return mock


@pytest.fixture
def agentic_fabric_mocker(mocker: MockerFixture) -> Generator[FabricMocker, None, None]:
    """Provide ``FabricMocker`` for agentic-fabric tests."""
    fabric_mocker = FabricMocker(mocker=mocker)
    yield fabric_mocker
    fabric_mocker.restore_modules()


@pytest.fixture
def fabric_mocker(mocker: MockerFixture) -> Generator[FabricMocker, None, None]:
    """Provide the concise ``FabricMocker`` fixture name."""
    fabric_mocker = FabricMocker(mocker=mocker)
    yield fabric_mocker
    fabric_mocker.restore_modules()


@pytest.fixture
def mock_agentic_frameworks(mocker: MockerFixture) -> Generator[dict[str, ModuleType], None, None]:
    """Mock every optional agent runtime framework."""
    fabric_mocker = FabricMocker(mocker=mocker)
    modules = fabric_mocker.mock_all_frameworks()
    yield modules
    fabric_mocker.restore_modules()


@pytest.fixture
def mock_crewai(mocker: MockerFixture) -> Generator[dict[str, ModuleType], None, None]:
    """Mock CrewAI modules only."""
    fabric_mocker = FabricMocker(mocker=mocker)
    modules = fabric_mocker.mock_crewai()
    yield modules
    fabric_mocker.restore_modules()


@pytest.fixture
def mock_langgraph(mocker: MockerFixture) -> Generator[dict[str, ModuleType], None, None]:
    """Mock LangGraph modules only."""
    fabric_mocker = FabricMocker(mocker=mocker)
    modules = fabric_mocker.mock_langgraph()
    yield modules
    fabric_mocker.restore_modules()


@pytest.fixture
def mock_strands(mocker: MockerFixture) -> Generator[dict[str, ModuleType], None, None]:
    """Mock Strands modules only."""
    fabric_mocker = FabricMocker(mocker=mocker)
    modules = fabric_mocker.mock_strands()
    yield modules
    fabric_mocker.restore_modules()


__all__ = [
    "ALL_FRAMEWORK_MODULES",
    "CREWAI_MODULES",
    "LANGGRAPH_MODULES",
    "RUNTIME_MODULES",
    "STRANDS_MODULES",
    "FabricMocker",
    "agentic_fabric_mocker",
    "fabric_mocker",
    "mock_agentic_frameworks",
    "mock_crewai",
    "mock_langgraph",
    "mock_strands",
]
