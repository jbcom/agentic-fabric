Getting Started
===============

Install the core package when you only need discovery, configuration
loading, and lazy runner selection:

.. code:: bash

   pip install agentic-fabric

Install the runtime extras you actually use:

.. code:: bash

   pip install "agentic-fabric[crewai]"
   pip install "agentic-fabric[langgraph]"
   pip install "agentic-fabric[strands]"

.. code:: python

   from agentic_fabric import detect_framework, get_framework_info, get_runner

   runtimes = get_framework_info()
   framework = detect_framework()
   runner = get_runner(framework)

Crew definitions can live in ``.crew/``, ``.crewai/``, ``.langgraph/``,
or ``.strands/`` directories. A ``.crew/`` directory is
framework-agnostic. A framework-specific directory requires that
runtime.

Use ``AgenticData`` when runtime context should travel with data and
registered crew definitions:

.. code:: python

   from agentic_fabric import AgenticData

   session = AgenticData({"repo": "jbcom/agentic-fabric"})
   session.register_agent("reviewer", crew_config)
   result = session.run_agent("reviewer", runtime="crewai")
