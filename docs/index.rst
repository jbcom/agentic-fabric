Agentic Fabric
==============

``agentic-fabric`` is the standalone orchestration package for
framework-agnostic agent crews. It discovers YAML crew definitions,
selects an installed runtime, and runs the same crew on CrewAI,
LangGraph, Strands, or local CLI runners.

.. code:: bash

   pip install agentic-fabric
   pip install "agentic-fabric[crewai]"
   pip install "agentic-fabric[langgraph]"
   pip install "agentic-fabric[strands]"
   pip install "agentic-fabric[ai]"

Vendor-backed tools will be exposed as passthrough extras after
``vendor-fabric`` is available on PyPI. Until then, agent runtime work
stays separate from provider dependency declarations.

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
