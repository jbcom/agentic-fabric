"""Tests for A2A Protocol 1.0 interfaces."""

from __future__ import annotations

import asyncio
import builtins
import sys
import types

from typing import Any

import pytest

from agentic_fabric import a2a


class Record:
    """Keyword-recording stand-in for protobuf and server classes."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class FakeAgentExecutor:
    """Official AgentExecutor base stand-in."""


class FakeTaskState:
    TASK_STATE_WORKING = "working"
    TASK_STATE_COMPLETED = "completed"
    TASK_STATE_FAILED = "failed"
    TASK_STATE_CANCELED = "canceled"


class FakeDefaultRequestHandler(Record):
    """Request handler stand-in."""


class FakeTaskStore:
    """In-memory task store stand-in."""


class FakeStarlette:
    """Starlette stand-in that records routes."""

    def __init__(self, *, routes: list[Any]) -> None:
        self.routes = routes


class FakeQueue:
    """Collect A2A task lifecycle events."""

    def __init__(self) -> None:
        self.events: list[Any] = []

    async def enqueue_event(self, event: Any) -> None:
        self.events.append(event)


class FakeContext:
    """A2A RequestContext stand-in."""

    def __init__(
        self,
        *,
        message: Any | None = None,
        current_task: Any | None = None,
        task_id: str | None = "task-1",
        context_id: str | None = "context-1",
    ) -> None:
        self.message = message
        self.current_task = current_task
        self.task_id = task_id
        self.context_id = context_id
        self.metadata = {"trace": "abc"}

    def get_user_input(self) -> str:
        return self.message.text


def _install_fake_a2a_types() -> types.ModuleType:
    """Install the A2A protocol types fake module."""
    protocol_types = types.ModuleType("a2a.types")
    protocol_types.AgentCapabilities = Record
    protocol_types.AgentCard = Record
    protocol_types.AgentInterface = Record
    protocol_types.AgentSkill = Record
    protocol_types.TaskState = FakeTaskState
    return protocol_types


def _install_fake_a2a_helpers() -> types.ModuleType:
    """Install the A2A helpers fake module."""
    helpers = types.ModuleType("a2a.helpers")
    helpers.get_data_parts = lambda parts: [part.data for part in parts if hasattr(part, "data")]
    helpers.new_task_from_user_message = lambda message: types.SimpleNamespace(
        id=message.task_id,
        context_id=message.context_id,
        kind="task",
    )
    helpers.new_text_status_update_event = lambda **kwargs: Record(kind="status", **kwargs)
    helpers.new_text_artifact_update_event = lambda **kwargs: Record(kind="text-artifact", **kwargs)
    helpers.new_data_artifact_update_event = lambda **kwargs: Record(kind="data-artifact", **kwargs)
    return helpers


def _install_fake_a2a_server() -> dict[str, types.ModuleType]:
    """Install the A2A server fake sub-package and return its modules."""
    package = types.ModuleType("a2a")
    server = types.ModuleType("a2a.server")
    agent_execution = types.ModuleType("a2a.server.agent_execution")
    request_handlers = types.ModuleType("a2a.server.request_handlers")
    routes = types.ModuleType("a2a.server.routes")
    tasks = types.ModuleType("a2a.server.tasks")

    agent_execution.AgentExecutor = FakeAgentExecutor
    request_handlers.DefaultRequestHandler = FakeDefaultRequestHandler
    routes.create_agent_card_routes = lambda *, agent_card: [("card", agent_card)]
    routes.create_jsonrpc_routes = lambda *, request_handler, rpc_url: [("rpc", rpc_url, request_handler)]
    tasks.InMemoryTaskStore = FakeTaskStore

    return {
        "a2a": package,
        "a2a.server": server,
        "a2a.server.agent_execution": agent_execution,
        "a2a.server.request_handlers": request_handlers,
        "a2a.server.routes": routes,
        "a2a.server.tasks": tasks,
    }


def _install_fake_starlette() -> dict[str, types.ModuleType]:
    """Install the starlette fake package and return its modules."""
    starlette = types.ModuleType("starlette")
    starlette_apps = types.ModuleType("starlette.applications")
    starlette_apps.Starlette = FakeStarlette
    return {
        "starlette": starlette,
        "starlette.applications": starlette_apps,
    }


def install_fake_a2a(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install the A2A 1.x modules consumed by the lazy adapter."""
    modules: dict[str, types.ModuleType] = {
        "a2a.types": _install_fake_a2a_types(),
        "a2a.helpers": _install_fake_a2a_helpers(),
        **_install_fake_a2a_server(),
        **_install_fake_starlette(),
    }

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


def reject_imports(monkeypatch: pytest.MonkeyPatch, prefix: str) -> None:
    """Reject imports for a module prefix."""
    real_import = builtins.__import__

    def reject(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == prefix or name.startswith(f"{prefix}."):
            raise ImportError(f"blocked {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject)


def make_spec(handler: Any) -> a2a.A2AAgentSpec:
    """Build a representative application spec."""
    return a2a.A2AAgentSpec(
        name="Demo Agent",
        description="Demonstrate A2A.",
        version="1.2.3",
        url="https://agents.example/a2a/jsonrpc",
        handler=handler,
        skills=(
            a2a.A2ASkillSpec(
                id="demo",
                name="Demo",
                description="Run demo work.",
                tags=("demo",),
                examples=("hello",),
            ),
        ),
    )


def make_message(*, text: str = "hello", data: list[Any] | None = None) -> Any:
    """Build a fake A2A message."""
    parts = [types.SimpleNamespace(data=item) for item in (data or [])]
    return types.SimpleNamespace(
        text=text,
        parts=parts,
        task_id="task-1",
        context_id="context-1",
    )


def test_a2a_card_and_jsonrpc_app(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)
    spec = make_spec(lambda request: request.text)

    card = a2a.create_agent_card(spec)
    custom_store = object()
    app = a2a.create_a2a_app(spec, task_store=custom_store)

    assert card.name == "Demo Agent"
    assert card.capabilities.streaming is True
    assert card.capabilities.push_notifications is False
    assert card.supported_interfaces[0].protocol_binding == "JSONRPC"
    assert card.supported_interfaces[0].protocol_version == "1.0"
    assert card.skills[0].input_modes == ["text/plain", "application/json"]
    assert app.routes[0][0] == "card"
    assert app.routes[1][0:2] == ("rpc", "/a2a/jsonrpc")
    assert app.routes[1][2].task_store is custom_store
    assert isinstance(app.routes[1][2].agent_executor, FakeAgentExecutor)


def test_a2a_app_uses_default_task_store_and_path(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)
    spec = make_spec(lambda request: request.text)
    spec = a2a.A2AAgentSpec(**{**spec.__dict__, "url": "https://agents.example"})
    app = a2a.create_a2a_app(spec)
    assert app.routes[1][1] == "/a2a"
    assert isinstance(app.routes[1][2].task_store, FakeTaskStore)


def test_a2a_executor_emits_text_task_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)
    seen: list[a2a.A2ARequest] = []

    def handler(request: a2a.A2ARequest) -> str:
        seen.append(request)
        return "finished"

    executor = a2a.create_agent_executor(make_spec(handler))
    queue = FakeQueue()
    context = FakeContext(message=make_message(data=[{"value": 1}]))
    asyncio.run(executor.execute(context, queue))

    assert [event.kind for event in queue.events] == ["task", "status", "text-artifact", "status"]
    assert queue.events[1].state == "working"
    assert queue.events[2].text == "finished"
    assert queue.events[2].last_chunk is True
    assert queue.events[3].state == "completed"
    assert seen[0].text == "hello"
    assert seen[0].data == ({"value": 1},)
    assert seen[0].metadata == {"trace": "abc"}


def test_a2a_executor_emits_structured_and_async_results(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)

    async def handler(request: a2a.A2ARequest) -> dict[str, str]:
        return {"echo": request.text}

    task = types.SimpleNamespace(id="existing-task", context_id="existing-context", kind="task")
    queue = FakeQueue()
    executor = a2a.create_agent_executor(make_spec(handler))
    asyncio.run(executor.execute(FakeContext(message=make_message(), current_task=task), queue))

    assert queue.events[0] is task
    assert queue.events[2].kind == "data-artifact"
    assert queue.events[2].data == {"echo": "hello"}
    assert queue.events[2].media_type == "application/json"


def test_a2a_executor_awaits_sync_handler_awaitable(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)

    async def response() -> str:
        return "awaited"

    executor = a2a.create_agent_executor(make_spec(lambda request: response()))
    queue = FakeQueue()
    asyncio.run(executor.execute(FakeContext(message=make_message()), queue))
    assert queue.events[2].text == "awaited"


def test_a2a_executor_emits_redacted_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)

    def handler(request: a2a.A2ARequest) -> None:
        raise RuntimeError("failed with sk-secret-value")

    executor = a2a.create_agent_executor(make_spec(handler))
    queue = FakeQueue()
    asyncio.run(executor.execute(FakeContext(message=make_message()), queue))

    assert [event.kind for event in queue.events] == ["task", "status", "status"]
    assert queue.events[-1].state == "failed"
    assert "sk-secret-value" not in queue.events[-1].text


def test_a2a_executor_requires_message(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)
    executor = a2a.create_agent_executor(make_spec(lambda request: "unused"))
    with pytest.raises(ValueError, match="require a message"):
        asyncio.run(executor.execute(FakeContext(message=None), FakeQueue()))


def test_a2a_executor_cancellation_is_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)
    executor = a2a.create_agent_executor(make_spec(lambda request: "ignored"))
    queue = FakeQueue()
    context = FakeContext(message=make_message())

    asyncio.run(executor.cancel(context, queue))
    asyncio.run(executor.execute(context, queue))

    assert queue.events[0].state == "canceled"
    assert [event.kind for event in queue.events[1:]] == ["task", "status"]

    empty_ids = FakeContext(message=make_message(), task_id=None, context_id=None)
    empty_queue = FakeQueue()
    asyncio.run(executor.cancel(empty_ids, empty_queue))
    assert empty_queue.events[0].task_id == ""
    assert empty_queue.events[0].context_id == ""


def test_a2a_executor_ignores_late_failure_after_cancellation(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_a2a(monkeypatch)

    def fail(_request: a2a.A2ARequest) -> None:
        raise RuntimeError("late failure")

    executor = a2a.create_agent_executor(make_spec(fail))
    executor._cancelled.add("task-1")
    queue = FakeQueue()
    asyncio.run(executor.execute(FakeContext(message=make_message()), queue))
    assert [event.state for event in queue.events if event.kind == "status"] == ["working"]


def test_vendor_a2a_spec_routes_structured_and_text_requests() -> None:
    class Data:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def capabilities(self, *, include_unavailable: bool) -> list[dict[str, str]]:
            assert include_unavailable is False
            return [{"provider": "demo", "operation": "search"}]

        def call(self, operation: str, provider: str, **arguments: Any) -> dict[str, Any]:
            self.calls.append((operation, provider, arguments))
            return {"ok": True}

    data = Data()
    spec = a2a.create_vendor_agent_spec("https://agents.example/a2a", data=data)
    structured = a2a.A2ARequest(
        text="",
        data=({"provider": "demo", "operation": "search", "arguments": {"q": "duck"}},),
        metadata={},
        message=None,
        task_id="task",
        context_id="context",
    )
    text = a2a.A2ARequest(
        text='{"provider":"demo","operation":"search","arguments":{}}',
        data=(),
        metadata={},
        message=None,
        task_id="task",
        context_id="context",
    )

    assert spec.handler(structured) == {"ok": True}
    assert spec.handler(text) == {"ok": True}
    assert data.calls == [("search", "demo", {"q": "duck"}), ("search", "demo", {})]
    assert spec.skills[0].examples == ('{"provider":"demo","operation":"search","arguments":{}}',)


@pytest.mark.parametrize(
    ("input_request", "error", "match"),
    [
        (
            a2a.A2ARequest("not-json", (), {}, None, "task", "context"),
            ValueError,
            "require a JSON",
        ),
        (
            a2a.A2ARequest("[]", (), {}, None, "task", "context"),
            TypeError,
            "must be an object",
        ),
        (
            a2a.A2ARequest('{"provider":"","operation":""}', (), {}, None, "task", "context"),
            ValueError,
            "non-empty provider",
        ),
        (
            a2a.A2ARequest(
                '{"provider":"demo","operation":"search","arguments":[]}',
                (),
                {},
                None,
                "task",
                "context",
            ),
            TypeError,
            "arguments must be an object",
        ),
    ],
)
def test_vendor_a2a_rejects_invalid_requests(
    input_request: a2a.A2ARequest,
    error: type[Exception],
    match: str,
) -> None:
    class Data:
        def capabilities(self, *, include_unavailable: bool) -> list[Any]:
            return []

        def call(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError("invalid input should not dispatch")

    spec = a2a.create_vendor_agent_spec("https://agents.example/a2a", data=Data())
    with pytest.raises(error, match=match):
        spec.handler(input_request)


def test_vendor_and_fabric_app_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(a2a, "create_vendor_agent_spec", lambda url, data=None: (url, data))
    monkeypatch.setattr(a2a, "create_a2a_app", lambda spec: calls.append(spec) or "app")
    assert a2a.create_vendor_a2a_app("https://agents.example/a2a", data="data") == "app"
    assert calls == [("https://agents.example/a2a", "data")]


def test_fabric_agent_spec_routes_agentic_data() -> None:
    class Data:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def run_fabric_agent(self, agent: Any, *, inputs: dict[str, Any]) -> str:
            self.calls.append((agent, inputs))
            return "done"

    data = Data()
    inline = {"name": "Reviewer"}
    spec = a2a.create_fabric_agent_spec(inline, "https://agents.example/reviewer", data=data)
    request = a2a.A2ARequest("review", ({"code": "x"},), {"trace": "1"}, None, "task", "context")

    assert spec.name == "Reviewer"
    assert spec.handler(request) == "done"
    assert data.calls == [
        (
            inline,
            {"message": "review", "data": [{"code": "x"}], "metadata": {"trace": "1"}},
        )
    ]

    named = a2a.create_fabric_agent_spec(
        "writer",
        "https://agents.example/writer",
        data=data,
        name="Writer Agent",
        description="Write things.",
    )
    assert named.name == "Writer Agent"
    assert named.description == "Write things."
    assert named.skills[0].description == "Write things."


def test_a2a_run_app_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    uvicorn = types.ModuleType("uvicorn")
    calls: list[Any] = []
    uvicorn.run = lambda app, *, host, port: calls.append((app, host, port))
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn)
    a2a.run_a2a_app("app", host="localhost", port=9000)
    assert calls == [("app", "localhost", 9000)]

    monkeypatch.setattr(sys, "argv", ["agentic-fabric-vendor-a2a", "--host", "0.0.0.0", "--port", "8123"])
    monkeypatch.setattr(a2a, "create_vendor_a2a_app", lambda url: f"app:{url}")
    monkeypatch.setattr(a2a, "run_a2a_app", lambda app, *, host, port: calls.append((app, host, port)))
    a2a.main()
    assert calls[-1] == ("app:http://0.0.0.0:8123/a2a", "0.0.0.0", 8123)

    monkeypatch.setattr(
        sys,
        "argv",
        ["agentic-fabric-vendor-a2a", "--url", "https://public.example/rpc"],
    )
    a2a.main()
    assert calls[-1][0] == "app:https://public.example/rpc"


def test_a2a_reports_missing_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "a2a")
    with pytest.raises(ImportError, match=r"agentic-fabric\[a2a\]"):
        a2a.create_agent_card(make_spec(lambda request: "unused"))

    monkeypatch.undo()
    reject_imports(monkeypatch, "uvicorn")
    with pytest.raises(ImportError, match=r"agentic-fabric\[a2a\]"):
        a2a.run_a2a_app("app")


def test_a2a_result_helpers() -> None:
    class Dumpable:
        def model_dump(self) -> dict[str, bool]:
            return {"dumped": True}

    assert a2a._jsonable(Dumpable()) == {"dumped": True}
    assert a2a._error_text(RuntimeError("bad")) == "RuntimeError: request failed"
