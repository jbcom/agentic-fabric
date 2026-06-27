Getting Started
===============

Install the core package when you only need discovery, configuration loading,
lazy runner selection, and local CLI runner profiles:

.. code:: bash

   pip install agentic-fabric

Install the runtime extras you actually use:

.. code:: bash

   pip install "agentic-fabric[langgraph]"
   pip install "agentic-fabric[strands]"
   pip install "agentic-fabric[mcp]"
   pip install "agentic-fabric[scraping]"

``mcp`` exposes MCP integration dependencies. ``scraping`` installs the
first-party requests/BeautifulSoup scraping helpers. Vendor passthrough extras
are deferred until ``vendor-fabric`` is published with a stable optional-extra
contract. There is no aggregate AI or all-frameworks extra. Test, typing, docs,
and dev extras are reserved for repository validation and package maintenance.

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
install guidance. Automatic selection follows CrewAI, then LangGraph, then
Strands, but explicit runtime selection always wins unless the crew is stored
in a framework-specific directory.

Use ``AgenticData`` when runtime context should travel with data and
registered crew definitions:

.. code:: python

   from agentic_fabric import AgenticData

   session = AgenticData({"repo": "jbcom/agentic-fabric"})
   session.register_agent("reviewer", crew_config)
   result = session.run_agent("reviewer", runtime="crewai")

CrewAI Dependency Note
----------------------

The CrewAI adapter remains lazy and source-compatible, but
``agentic-fabric`` does not publish a CrewAI extra while current CrewAI
releases depend on ChromaDB releases covered by an upstream critical advisory
with no patched version. Install CrewAI separately only after reviewing that
advisory state. Core, local CLI, LangGraph, Strands, MCP, and first-party
scraping installs do not include CrewAI.
