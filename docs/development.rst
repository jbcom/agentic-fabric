Development
===========

Use tox for local validation:

.. code:: bash

   tox -e lint
   tox -e typecheck
   tox -e py311
   tox -e py312
   tox -e py313
   tox -e py314
   tox -e coverage
   tox -e docs
   tox -e build

Optional framework and vendor tests should be marked and should skip
cleanly when the relevant extra is not installed.

Use ``pytest-agentic-fabric`` fixtures for reusable runtime test setup:

.. code:: python

   def test_runtime(agentic_mock_runtime, agentic_crew_config):
       agentic_mock_runtime("langgraph")
       assert agentic_crew_config["name"] == "test_crew"

Before deleting old monorepo code, first prove this repository owns the
moved surface with docs, tests, package metadata, and release workflows.
