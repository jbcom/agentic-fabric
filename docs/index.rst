Agentic Fabric
==============

``agentic-fabric`` is the standalone orchestration package for
framework-agnostic agent crews. It discovers YAML crew definitions,
selects an installed runtime, and runs the same crew on CrewAI,
LangGraph, Strands, or local CLI runners.

.. code:: bash

   pip install agentic-fabric
   pip install "agentic-fabric[langgraph]"
   pip install "agentic-fabric[strands]"
   pip install "agentic-fabric[mcp]"
   pip install "agentic-fabric[scraping]"

Local CLI runners are part of the core install because they shell out to
external executables and require no third-party Python framework. LangGraph,
Strands, MCP, scraping helpers, and vendor providers are opt-in extras. CrewAI
support stays lazy but CrewAI itself is an external install while its ChromaDB
dependency path has an upstream critical advisory with no patched version.

Vendor-backed passthrough extras are deferred until ``vendor-fabric`` is
published with a stable optional-extra contract. Until then, vendor references
stay lazy and report install guidance at use time.

Core imports stay lightweight. Optional frameworks and vendor SDKs are
loaded only when a runner, tool, or adapter is resolved.

.. toctree::
   :maxdepth: 2

   getting-started
   architecture
   agentic-workflows
   vendor-fabric
   pillars
   development
   api/index
