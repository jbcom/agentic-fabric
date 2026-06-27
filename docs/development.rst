Development
===========

Use tox for local validation:

.. code:: bash

   tox -e lint
   tox -e typecheck
   tox -e audit
   tox -e py311
   tox -e py312
   tox -e py313
   tox -e py314
   tox -e coverage
   tox -e plugin
   tox -e examples
   tox -e docs
   tox -e build

Optional framework and vendor tests should be marked and should skip
cleanly when the relevant extra is not installed.

Use ``pytest-agentic-fabric`` fixtures for reusable runtime test setup:

.. code:: python

   def test_runtime(agentic_fabric_mocker, agentic_fabric_agent_config):
       agentic_fabric_mocker.mock_langgraph()
       assert agentic_fabric_agent_config["name"] == "test_fabric_agent"

Override ``agentic_fabric_agent_config`` when a test needs a custom
discoverable workspace. The ``agentic_workspace`` fixture writes that config
into a temporary ``packages/sample/.fabric`` tree with matching manifest,
agents, and tasks YAML files.

Published helper fixtures include ``fabric_mocker``/``agentic_fabric_mocker``,
``mock_agentic_frameworks``, ``mock_crewai``, ``mock_langgraph``,
``mock_strands``, ``simple_agent_config``, ``simple_task_config``,
``simple_fabric_agent_config``, ``multi_agent_fabric_agent_config``,
``fabric_agent_with_knowledge``, and ``temp_fabric_dir``. Use those fixtures
instead of private test modules so downstream packages exercise the same
pytest plugin surface that is published with the workspace.

Before deleting old monorepo code, first prove this repository owns the
moved surface with docs, tests, package metadata, and release workflows.
