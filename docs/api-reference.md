---
title: API reference
description: Generated reference for the stable public import surfaces.
---

# API reference

This page is generated from the literal `__all__` surfaces of the two published packages. It intentionally documents only supported imports, and CI fails when this file is stale.

## `agentic_fabric`

### `A2AAgentSpec`

Declared by `agentic_fabric.a2a` as a class.

```python
class A2AAgentSpec
```

Agent card metadata and its application-level request handler.
### `A2ARequest`

Declared by `agentic_fabric.a2a` as a class.

```python
class A2ARequest
```

Stable request view passed to application handlers.
### `A2ASkillSpec`

Declared by `agentic_fabric.a2a` as a class.

```python
class A2ASkillSpec
```

Protocol-neutral description of one skill advertised by an agent.
### `AgentCapabilityProviderMixin`

Declared by `agentic_fabric.capabilities` as a class.

```python
class AgentCapabilityProviderMixin
```

Collect decorated capability declarations through inheritance.
### `AgentCapabilitySpec`

Declared by `agentic_fabric.capabilities` as a class.

```python
class AgentCapabilitySpec
```

A declared agent/runtime/tool capability.
### `AgenticData`

Declared by `agentic_fabric.agentic_data` as a class.

```python
class AgenticData
```

VendorData extension with active runtime and fabric agent registry context.
### `ManagerAgent`

Declared by `agentic_fabric.core.manager` as a class.

```python
class ManagerAgent
```

Base class for hierarchical manager agents.
### `__version__`

Declared by `agentic_fabric` as a value.

```python
__version__: str
```

Installed distribution version.
### `agent_capability`

Declared by `agentic_fabric.capabilities` as a function.

```python
def agent_capability(name: str, *, kind: str='runtime', aliases: tuple[str, ...]=(), description: str='')
```

Declare an agent-facing capability on a method.
### `compose_fabric_agent`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def compose_fabric_agent(fabric_agent_config: dict[str, Any], framework: str | None=None)
```

Compose a fabric agent configuration into a runtime-specific object.
### `create_a2a_app`

Declared by `agentic_fabric.a2a` as a function.

```python
def create_a2a_app(spec: A2AAgentSpec, *, task_store: Any | None=None)
```

Create a Starlette app serving Agent Card discovery and A2A JSON-RPC.
### `create_fabric_agent_spec`

Declared by `agentic_fabric.a2a` as a function.

```python
def create_fabric_agent_spec(fabric_agent: str | Mapping[str, Any], url: str, *, data: Any | None=None, name: str | None=None, description: str | None=None)
```

Create an A2A spec that runs one registered or inline fabric agent.
### `create_vendor_a2a_app`

Declared by `agentic_fabric.a2a` as a function.

```python
def create_vendor_a2a_app(url: str, *, data: Any | None=None)
```

Create the vendor-capability A2A JSON-RPC application.
### `create_vendor_agent_spec`

Declared by `agentic_fabric.a2a` as a function.

```python
def create_vendor_agent_spec(url: str, *, data: Any | None=None, name: str='Vendor Fabric Agent', description: str='Invoke available vendor-fabric capabilities through the Agent2Agent protocol.')
```

Create an A2A agent backed only by the public ``VendorData`` facade.
### `detect_framework`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def detect_framework(preferred: str | None=None)
```

Detect the best available AI framework.
### `discover_all_framework_configs`

Declared by `agentic_fabric.core.discovery` as a function.

```python
def discover_all_framework_configs(workspace_root: Path | None=None)
```

Discover all framework-specific config directories for all packages.
### `discover_packages`

Declared by `agentic_fabric.core.discovery` as a function.

```python
def discover_packages(workspace_root: Path | None=None, framework: str | None=None)
```

Discover all packages with fabric agent configuration directories.
### `get_available_frameworks`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def get_available_frameworks()
```

Get list of all available frameworks.
### `get_fabric_agent_config`

Declared by `agentic_fabric.core.discovery` as a function.

```python
def get_fabric_agent_config(config_dir: Path, fabric_agent_name: str)
```

Load a specific fabric agent's configuration.
### `get_framework_info`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def get_framework_info(framework: str | None=None)
```

Return lazy runtime registry metadata with current availability.
### `get_runner`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def get_runner(framework: str | None=None)
```

Get a runner for the specified or auto-detected framework.
### `is_framework_available`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def is_framework_available(framework: str)
```

Check if a framework is installed and importable.
### `list_fabric_agents`

Declared by `agentic_fabric.core.discovery` as a function.

```python
def list_fabric_agents(package_name: str | None=None, framework: str | None=None)
```

List all available fabric agents, optionally filtered by package or framework.
### `run_fabric_agent_auto`

Declared by `agentic_fabric.core.decomposer` as a function.

```python
def run_fabric_agent_auto(fabric_agent_config: dict[str, Any], inputs: dict[str, Any] | None=None, framework: str | None=None)
```

Run a fabric agent using the best available framework.
### `runtime_capability`

Declared by `agentic_fabric.capabilities` as a function.

```python
def runtime_capability(name: str, *, aliases: tuple[str, ...]=(), description: str='')
```

Declare a runner/runtime capability.
### `tool_capability`

Declared by `agentic_fabric.capabilities` as a function.

```python
def tool_capability(name: str, *, aliases: tuple[str, ...]=(), description: str='')
```

Declare a tool capability.

## `pytest_agentic_fabric`

### `ALL_FRAMEWORK_MODULES`

Declared by `pytest_agentic_fabric.mocking` as a value.

```python
ALL_FRAMEWORK_MODULES
```

Public package value.
### `CREWAI_MODULES`

Declared by `pytest_agentic_fabric.mocking` as a value.

```python
CREWAI_MODULES
```

Public package value.
### `LANGGRAPH_MODULES`

Declared by `pytest_agentic_fabric.mocking` as a value.

```python
LANGGRAPH_MODULES
```

Public package value.
### `RUNTIME_MODULES`

Declared by `pytest_agentic_fabric.mocking` as a value.

```python
RUNTIME_MODULES
```

Public package value.
### `STRANDS_MODULES`

Declared by `pytest_agentic_fabric.mocking` as a value.

```python
STRANDS_MODULES
```

Public package value.
### `FabricMocker`

Declared by `pytest_agentic_fabric.mocking` as a class.

```python
class FabricMocker
```

Convenience wrapper around pytest-mock for optional agent runtime tests.
### `__version__`

Declared by `pytest_agentic_fabric` as a value.

```python
__version__: str
```

Installed distribution version.
