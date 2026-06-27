Agentic Workflows
=================

Crew definitions are YAML-first and runtime-neutral unless placed in a
framework-specific directory.

.. code:: yaml

   name: example
   crews:
     reviewer:
       description: Review implementation quality
       agents: config/agents.yaml
       tasks: config/tasks.yaml

``agentic-fabric`` resolves the crew, selects a runner, and delegates
execution to the installed framework. The public API is intentionally
small:

.. code:: python

   from agentic_fabric import discover_packages, get_crew_config, run_crew_auto

   packages = discover_packages()
   config = get_crew_config(packages["example"], "reviewer")
   result = run_crew_auto(config, inputs={"topic": "release readiness"})

For stateful orchestration, register the same config with
``AgenticData``:

.. code:: python

   from agentic_fabric import AgenticData

   session = AgenticData(agent_registry={"reviewer": config})
   session.use_runtime("langgraph", strict=False)
   result = session.run_reviewer({"topic": "release readiness"})

When no framework is installed, discovery and metadata inspection still
work. Execution reports the unavailable runtime instead of failing
during import.

Tool Resolution
---------------

Crew tool entries are resolved lazily. Built-in filesystem tool aliases,
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
relative to the crew config directory and cannot escape it. Filesystem
tools resolve symlinks before reading or writing and keep writes inside
their configured workspace directories.
