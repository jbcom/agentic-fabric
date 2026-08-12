"""A2A Protocol 1.0 interfaces for fabric agents and vendor capabilities.

The module keeps the official A2A SDK optional and lazy. It owns protocol
cards, task lifecycle events, and ASGI routes while delegating agent execution
to ``AgenticData`` and provider execution to the inherited ``VendorData``
facade.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


A2A_INSTALL_MESSAGE = "A2A SDK is not installed. Install with: pip install agentic-fabric[a2a]"


@dataclass(frozen=True)
class A2ASkillSpec:
    """Protocol-neutral description of one skill advertised by an agent."""

    id: str
    name: str
    description: str
    tags: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    input_modes: tuple[str, ...] = ("text/plain", "application/json")
    output_modes: tuple[str, ...] = ("text/plain", "application/json")


@dataclass(frozen=True)
class A2ARequest:
    """Stable request view passed to application handlers."""

    text: str
    data: tuple[Any, ...]
    metadata: Mapping[str, Any]
    message: Any
    task_id: str
    context_id: str


@dataclass(frozen=True)
class A2AAgentSpec:
    """Agent card metadata and its application-level request handler."""

    name: str
    description: str
    version: str
    url: str
    handler: Callable[[A2ARequest], Any]
    skills: tuple[A2ASkillSpec, ...]
    default_input_modes: tuple[str, ...] = ("text/plain", "application/json")
    default_output_modes: tuple[str, ...] = ("text/plain", "application/json")


def _require_a2a() -> dict[str, Any]:
    """Load the official A2A 1.x server surface lazily."""
    try:
        from a2a.helpers import (
            get_data_parts,
            new_data_artifact_update_event,
            new_task_from_user_message,
            new_text_artifact_update_event,
            new_text_status_update_event,
        )
        from a2a.server.agent_execution import AgentExecutor
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
        from a2a.server.tasks import InMemoryTaskStore
        from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill, TaskState
        from starlette.applications import Starlette
    except ImportError as exc:
        raise ImportError(A2A_INSTALL_MESSAGE) from exc
    return {
        "AgentCapabilities": AgentCapabilities,
        "AgentCard": AgentCard,
        "AgentExecutor": AgentExecutor,
        "AgentInterface": AgentInterface,
        "AgentSkill": AgentSkill,
        "DefaultRequestHandler": DefaultRequestHandler,
        "InMemoryTaskStore": InMemoryTaskStore,
        "Starlette": Starlette,
        "TaskState": TaskState,
        "create_agent_card_routes": create_agent_card_routes,
        "create_jsonrpc_routes": create_jsonrpc_routes,
        "get_data_parts": get_data_parts,
        "new_data_artifact_update_event": new_data_artifact_update_event,
        "new_task_from_user_message": new_task_from_user_message,
        "new_text_artifact_update_event": new_text_artifact_update_event,
        "new_text_status_update_event": new_text_status_update_event,
    }


def _jsonable(value: Any) -> Any:
    """Lower and redact an application result for a protocol artifact."""
    from extended_data.containers import to_builtin
    from extended_data.primitives.redaction import redact_sensitive_data

    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return redact_sensitive_data(to_builtin(value))


def _error_text(error: Exception) -> str:
    """Return a non-secret-bearing A2A task failure message."""
    return f"{type(error).__name__}: request failed"


def create_agent_card(spec: A2AAgentSpec) -> Any:
    """Build an A2A 1.0 Agent Card with an explicit JSON-RPC interface."""
    sdk = _require_a2a()
    skills = [
        sdk["AgentSkill"](
            id=skill.id,
            name=skill.name,
            description=skill.description,
            tags=list(skill.tags),
            examples=list(skill.examples),
            input_modes=list(skill.input_modes),
            output_modes=list(skill.output_modes),
        )
        for skill in spec.skills
    ]
    return sdk["AgentCard"](
        name=spec.name,
        description=spec.description,
        version=spec.version,
        capabilities=sdk["AgentCapabilities"](streaming=True, push_notifications=False),
        default_input_modes=list(spec.default_input_modes),
        default_output_modes=list(spec.default_output_modes),
        skills=skills,
        supported_interfaces=[
            sdk["AgentInterface"](
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=spec.url,
            )
        ],
    )


def create_agent_executor(spec: A2AAgentSpec) -> Any:
    """Create an A2A executor that emits one valid task lifecycle stream."""
    sdk = _require_a2a()
    agent_executor_base = sdk["AgentExecutor"]

    class FabricAgentExecutor(agent_executor_base):
        """Bridge an application handler into A2A task events."""

        def __init__(self) -> None:
            self._cancelled: set[str] = set()

        async def execute(self, context: Any, event_queue: Any) -> None:
            message = context.message
            if message is None:
                msg = "A2A requests require a message"
                raise ValueError(msg)

            task = context.current_task or sdk["new_task_from_user_message"](message)
            task_id = task.id
            context_id = task.context_id
            await event_queue.enqueue_event(task)
            await event_queue.enqueue_event(
                sdk["new_text_status_update_event"](
                    task_id=task_id,
                    context_id=context_id,
                    state=sdk["TaskState"].TASK_STATE_WORKING,
                    text="Processing request.",
                )
            )

            request = A2ARequest(
                text=context.get_user_input(),
                data=tuple(sdk["get_data_parts"](message.parts)),
                metadata=dict(context.metadata),
                message=message,
                task_id=task_id,
                context_id=context_id,
            )
            try:
                if inspect.iscoroutinefunction(spec.handler):
                    result = await spec.handler(request)
                else:
                    result = await asyncio.to_thread(spec.handler, request)
                    if inspect.isawaitable(result):
                        result = await result

                if task_id in self._cancelled:
                    return
                payload = _jsonable(result)
                if isinstance(payload, str):
                    artifact = sdk["new_text_artifact_update_event"](
                        task_id=task_id,
                        context_id=context_id,
                        name="result",
                        text=payload,
                        last_chunk=True,
                    )
                else:
                    artifact = sdk["new_data_artifact_update_event"](
                        task_id=task_id,
                        context_id=context_id,
                        name="result",
                        data=payload,
                        media_type="application/json",
                        last_chunk=True,
                    )
                await event_queue.enqueue_event(artifact)
                await event_queue.enqueue_event(
                    sdk["new_text_status_update_event"](
                        task_id=task_id,
                        context_id=context_id,
                        state=sdk["TaskState"].TASK_STATE_COMPLETED,
                        text="Request completed.",
                    )
                )
            except Exception as exc:
                if task_id in self._cancelled:
                    return
                await event_queue.enqueue_event(
                    sdk["new_text_status_update_event"](
                        task_id=task_id,
                        context_id=context_id,
                        state=sdk["TaskState"].TASK_STATE_FAILED,
                        text=_error_text(exc),
                    )
                )

        async def cancel(self, context: Any, event_queue: Any) -> None:
            task_id = context.task_id or ""
            context_id = context.context_id or ""
            self._cancelled.add(task_id)
            await event_queue.enqueue_event(
                sdk["new_text_status_update_event"](
                    task_id=task_id,
                    context_id=context_id,
                    state=sdk["TaskState"].TASK_STATE_CANCELED,
                    text="Request canceled.",
                )
            )

    return FabricAgentExecutor()


def create_a2a_app(spec: A2AAgentSpec, *, task_store: Any | None = None) -> Any:
    """Create a Starlette app serving Agent Card discovery and A2A JSON-RPC."""
    sdk = _require_a2a()
    card = create_agent_card(spec)
    request_handler = sdk["DefaultRequestHandler"](
        agent_executor=create_agent_executor(spec),
        task_store=task_store or sdk["InMemoryTaskStore"](),
        agent_card=card,
    )
    rpc_path = urlparse(spec.url).path or "/a2a"
    routes = [
        *sdk["create_agent_card_routes"](agent_card=card),
        *sdk["create_jsonrpc_routes"](request_handler=request_handler, rpc_url=rpc_path),
    ]
    return sdk["Starlette"](routes=routes)


def _request_payload(request: A2ARequest) -> Mapping[str, Any]:
    """Read a structured request from an A2A data part or JSON text."""
    if request.data and isinstance(request.data[0], Mapping):
        return request.data[0]
    try:
        payload = json.loads(request.text)
    except json.JSONDecodeError as exc:
        msg = "Vendor A2A requests require a JSON data part or JSON text"
        raise ValueError(msg) from exc
    if not isinstance(payload, Mapping):
        msg = "Vendor A2A request payload must be an object"
        raise TypeError(msg)
    return payload


def create_vendor_agent_spec(
    url: str,
    *,
    data: Any | None = None,
    name: str = "Vendor Fabric Agent",
    description: str = "Invoke available vendor-fabric capabilities through the Agent2Agent protocol.",
) -> A2AAgentSpec:
    """Create an A2A agent backed only by the public ``VendorData`` facade."""
    from agentic_fabric import AgenticData, __version__

    data = data or AgenticData()

    def call_vendor(request: A2ARequest) -> Any:
        payload = _request_payload(request)
        provider = str(payload.get("provider", "")).strip()
        operation = str(payload.get("operation", "")).strip()
        arguments = payload.get("arguments", {})
        if not provider or not operation:
            msg = "Vendor A2A requests require non-empty provider and operation fields"
            raise ValueError(msg)
        if not isinstance(arguments, Mapping):
            msg = "Vendor A2A arguments must be an object"
            raise TypeError(msg)
        return data.call(operation, provider, **dict(arguments))

    capability_examples = []
    for capability in data.capabilities(include_unavailable=False):
        provider = str(capability.get("provider", ""))
        operation = str(capability.get("operation", ""))
        if provider and operation:
            capability_examples.append(
                json.dumps({"provider": provider, "operation": operation, "arguments": {}}, separators=(",", ":"))
            )

    skill = A2ASkillSpec(
        id="vendor-capability",
        name="Vendor capability",
        description=(
            "Call an available vendor-fabric capability with provider, operation, and arguments fields. "
            "Provider credentials and connector behavior remain in vendor-fabric."
        ),
        tags=("vendor-fabric", "connectors"),
        examples=tuple(capability_examples[:5]),
    )
    return A2AAgentSpec(
        name=name,
        description=description,
        version=__version__,
        url=url,
        handler=call_vendor,
        skills=(skill,),
    )


def create_vendor_a2a_app(url: str, *, data: Any | None = None) -> Any:
    """Create the vendor-capability A2A JSON-RPC application."""
    return create_a2a_app(create_vendor_agent_spec(url, data=data))


def create_fabric_agent_spec(
    fabric_agent: str | Mapping[str, Any],
    url: str,
    *,
    data: Any | None = None,
    name: str | None = None,
    description: str | None = None,
) -> A2AAgentSpec:
    """Create an A2A spec that runs one registered or inline fabric agent."""
    from agentic_fabric import AgenticData, __version__

    data = data or AgenticData()
    agent_name = name or (
        fabric_agent if isinstance(fabric_agent, str) else str(fabric_agent.get("name", "Fabric Agent"))
    )

    def run_fabric(request: A2ARequest) -> Any:
        return data.run_fabric_agent(
            fabric_agent,
            inputs={"message": request.text, "data": list(request.data), "metadata": dict(request.metadata)},
        )

    return A2AAgentSpec(
        name=agent_name,
        description=description or f"Run the {agent_name} fabric agent through the Agent2Agent protocol.",
        version=__version__,
        url=url,
        handler=run_fabric,
        skills=(
            A2ASkillSpec(
                id="run-fabric-agent",
                name=f"Run {agent_name}",
                description=description or f"Delegate a task to the {agent_name} fabric agent.",
                tags=("agentic-fabric", "delegation"),
            ),
        ),
    )


def run_a2a_app(app: Any, *, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run an A2A ASGI application with Uvicorn."""
    try:
        import uvicorn
    except ImportError as exc:
        raise ImportError(A2A_INSTALL_MESSAGE) from exc
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """Run the vendor-capability A2A console entry point."""
    parser = argparse.ArgumentParser(description="Serve vendor-fabric capabilities over A2A JSON-RPC")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--url", default=None, help="Public JSON-RPC URL advertised in the Agent Card")
    arguments = parser.parse_args()
    url = arguments.url or f"http://{arguments.host}:{arguments.port}/a2a"
    run_a2a_app(create_vendor_a2a_app(url), host=arguments.host, port=arguments.port)


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = [
    "A2AAgentSpec",
    "A2ARequest",
    "A2ASkillSpec",
    "create_a2a_app",
    "create_agent_card",
    "create_agent_executor",
    "create_fabric_agent_spec",
    "create_vendor_a2a_app",
    "create_vendor_agent_spec",
    "run_a2a_app",
]
