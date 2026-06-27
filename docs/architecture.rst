Architecture Plan
=================

This page records the local plan for ``agentic-fabric``. It is the
source of truth for agent runtime architecture in this repository.

Boundary
--------

``agentic-fabric`` owns agent and crew orchestration:

- discovery and manifest loading
- universal crew decomposition
- runner adapters for optional agent frameworks
- tool resolution for built-in, MCP-style, fully qualified, and
  vendor-backed tools
- agent-facing tool catalogs built from ``vendor-fabric`` capability
  metadata
- agent capability dispatch over the data and vendor layers
- pytest support for agent runtime tests

``extended-data`` owns base data primitives, logging, input handling,
files, redaction, and generic workflows. ``vendor-fabric`` owns vendor
API connectors, provider-backed sync, SecretSync Python facade/capability
surfaces, provider capability metadata, and provider dispatch.

AgenticData
-----------

``AgenticData`` extends the vendor layer in the same way ``VendorData``
extends ``ExtendedData``. The full-stack inheritance line is:

.. code:: text

   ExtendedData -> VendorData -> AgenticData

``AgenticData`` owns agent runtime context. It does not reimplement data
containers or provider sync. Those behaviors come from inherited layers
when ``vendor-fabric`` is installed, and from an import-safe fallback
otherwise.

.. code:: python

   from agentic_fabric import AgenticData


   session = AgenticData({"task": "summarize"})
   session.use_runtime("langgraph", strict=False)

That shape lets the agent layer carry data, provider, and runtime context
together:

.. code:: python

   session.register_agent("repo_summarizer", crew_config)
   result = session.run_agent("repo_summarizer", repo="jbcom/extended-data")

Agent Capability Registry
-------------------------

Agent and runtime capabilities should use normal Python mechanisms:

- ``typing.Protocol`` for runner and tool contracts
- abstract base classes for shared runner behavior
- ``@agent_capability(...)`` or ``@tool_capability(...)`` decorators on
  concrete runtime/tool methods
- ``__init_subclass__`` to collect capability metadata through
  inheritance
- read-only capability mappings for inspection and deterministic
  dispatch
- ``__getattr__`` only as a convenience over declared capabilities
- ``__dir__`` for autocomplete and developer inspection

The implementation lives in ``agentic_fabric.capabilities``:

- ``@agent_capability(...)``
- ``@runtime_capability(...)``
- ``@tool_capability(...)``
- ``AgentCapabilityProviderMixin``

Do not use custom dunder capability names. The capability registry is
plain Python metadata collected at class creation.

Runtime Selection
-----------------

Runtime frameworks are optional and should be discovered lazily. The
core package should import without CrewAI, LangGraph, Strands, or vendor
SDKs being imported eagerly.

Runtime metadata lives in ``agentic_fabric.runners.registry``. The public
compatibility API remains in ``agentic_fabric.core.decomposer``:
``detect_framework()``, ``get_runner()``, ``get_available_frameworks()``,
and ``get_framework_info()``.

Runtime selection should follow explicit precedence when the caller does
not choose a runtime:

1. a runtime already active on ``AgenticData``
2. a runtime requested in the crew manifest
3. the first installed runtime in documented priority order
4. a clear unavailable-runtime error with install guidance

Vendor Tooling
--------------

Vendor-backed tools should go through ``AgenticData``, ``VendorData``,
and ``vendor-fabric`` capabilities. Agent code should not call cloud SDKs
directly. Agent tools that need repository files, Slack messages, Vault
secrets, or S3 objects should route through provider capabilities
declared by ``vendor-fabric``.

Lazy vendor tool references are supported with
``vendor://provider/operation`` and ``vendor:provider:operation`` names.
When ``vendor-fabric`` is installed, ``AgenticData.vendor_tools()`` reads
``VendorData.capabilities()`` and returns lazy agent-facing wrappers for
those provider operations.

Testing Package
---------------

``pytest-agentic-fabric`` is a sibling package in this repository. It
provides runtime availability fixtures, runtime module mocking, minimal
crew/workspace fixtures, and opt-in E2E controls.

Provider fixtures belong in ``pytest-vendor-fabric``. Base data fixtures
belong in ``pytest-extended-data``.

Validation Contract
-------------------

Every public behavior needs tests and docs in the same change. Python
3.11, 3.12, 3.13, and 3.14 must pass without skipped missing
interpreters.
