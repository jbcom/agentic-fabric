Agentic Workflows
=================

Fabric agent definitions are YAML-first and runtime-neutral unless placed in a
framework-specific directory.

.. code:: yaml

   name: example
   fabric_agents:
     reviewer:
       description: Review implementation quality
       agents: config/agents.yaml
       tasks: config/tasks.yaml

``agentic-fabric`` resolves the fabric agent, selects a runner, and delegates
execution to the installed framework. The public API is intentionally
small:

.. code:: python

   from agentic_fabric import discover_packages, get_fabric_agent_config, run_fabric_agent_auto

   packages = discover_packages()
   config = get_fabric_agent_config(packages["example"], "reviewer")
   result = run_fabric_agent_auto(config, inputs={"topic": "release readiness"})

For stateful orchestration, register the same config with
``AgenticData``:

.. code:: python

   from agentic_fabric import AgenticData

   session = AgenticData(fabric_agents={"reviewer": config})
   session.use_runtime("langgraph", strict=False)
   result = session.run_reviewer({"topic": "release readiness"})

When no framework is installed, discovery and metadata inspection still
work. Execution reports the unavailable runtime instead of failing
during import.

Runtime Extras
--------------

The public runtime registry exposes install guidance for each optional
framework:

.. code:: python

   from agentic_fabric import get_framework_info

   for runtime in get_framework_info():
       print(runtime["name"], runtime["available"], runtime["install"])

Supported runtime extras are ``langgraph`` and ``strands``. The CrewAI adapter
is lazy and can use an externally installed CrewAI runtime, but
``agentic-fabric`` does not publish a CrewAI extra while CrewAI's ChromaDB
dependency path has an upstream critical advisory with no patched version.
Install the runtime you actually execute; the package does not publish an
aggregate AI or all-frameworks extra. ``mcp`` and ``scraping`` remain focused
optional tool surfaces. Local CLI runners are configured profiles over external
executables and do not require a Python extra:

.. code:: bash

   agentic-fabric list-runners
   agentic-fabric run --runner claude-code --input "Review this package"

Tool Resolution
---------------

Fabric agent tool entries are resolved lazily. Built-in filesystem tool aliases,
``mcp://filesystem/...`` aliases, and ``vendor://provider/operation``
references do not import optional framework or vendor packages until the
tool is used.

For Python tools, prefer registering a factory in application startup:

.. code:: python

   from agentic_fabric.tools.registry import register_tool_factory

   register_tool_factory("MyTool", lambda: MyTool(), aliases=("my-tool",))

Fully qualified ``module:attribute`` and ``package.module.ClassName``
references are allowed for ``agentic_fabric`` modules by default. External
module imports must be explicitly allowlisted:

.. code:: bash

   export AGENTIC_FABRIC_TOOL_IMPORT_ALLOWLIST="my_company.tools,shared_agents."

Manifest paths for ``agents``, ``tasks``, and ``knowledge`` are resolved
relative to the fabric agent config directory and cannot escape it. Filesystem
tools resolve symlinks before reading or writing and keep writes inside
their configured workspace directories.

MCP Adapters
------------

The ``mcp`` extra installs the MCP transport dependency. Provider
implementation still belongs to ``vendor-fabric``; this package only owns the
runtime-visible adapter layer:

.. code:: bash

   agentic-fabric-vendor-mcp
   agentic-fabric-meshy-mcp

``agentic-fabric-vendor-mcp`` exposes credential-free vendor catalog tools and
public ``vendor-fabric`` data methods. ``agentic-fabric-meshy-mcp`` adapts the
Meshy capability definitions from ``vendor_fabric.meshy.tools`` into MCP tool
metadata. Install the matching ``vendor-fabric`` package and provider extras
in the same environment before running provider-backed MCP tools.
