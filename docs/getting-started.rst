Getting Started
===============

Install the core package when you only need discovery, configuration loading,
lazy runner selection, and local CLI runner profiles:

.. code:: bash

   pip install agentic-fabric

Install the runtime extras you actually use:

.. code:: bash

   pip install "agentic-fabric[crewai]"
   pip install "agentic-fabric[langgraph]"
   pip install "agentic-fabric[strands]"
   pip install "agentic-fabric[mcp]"
   pip install "agentic-fabric[scraping]"

``mcp`` exposes MCP integration dependencies. ``scraping`` installs the CrewAI
tools surface plus ``requests`` and ``beautifulsoup4``. Vendor passthrough
extras are deferred until ``vendor-fabric`` is published with a stable
optional-extra contract. There is no aggregate AI or all-frameworks extra.
Test, typing, docs, and dev extras are reserved for repository validation and
package maintenance.

Local CLI runners do not require a Python extra. They shell out to external
executables that you install separately:

.. code:: bash

   agentic-fabric list-runners --json
   agentic-fabric run --runner aider --input "Add validation to auth.py"

.. code:: python

   from agentic_fabric import detect_framework, get_framework_info, get_runner

   runtimes = get_framework_info()
   framework = detect_framework()
   runner = get_runner(framework)

Crew definitions can live in ``.crew/``, ``.crewai/``, ``.langgraph/``,
or ``.strands/`` directories. A ``.crew/`` directory is
framework-agnostic. A framework-specific directory requires that
runtime.

If a required runtime is unavailable, runtime errors include the matching
``agentic-fabric[...]`` install command. Automatic selection follows CrewAI,
then LangGraph, then Strands, but explicit runtime selection always wins unless
the crew is stored in a framework-specific directory.

Use ``AgenticData`` when runtime context should travel with data and
registered crew definitions:

.. code:: python

   from agentic_fabric import AgenticData

   session = AgenticData({"repo": "jbcom/agentic-fabric"})
   session.register_agent("reviewer", crew_config)
   result = session.run_agent("reviewer", runtime="crewai")

CrewAI Dependency Note
----------------------

The ``crewai`` and ``scraping`` extras include dependencies chosen by CrewAI.
If a transitive CrewAI dependency has an upstream advisory with no patched
release, upgrading ``agentic-fabric`` or relaxing its CrewAI range cannot clear
that advisory by itself. Core and local CLI installs do not include CrewAI.
Track the upstream CrewAI and dependency advisory state before enabling those
optional extras in sensitive environments.
