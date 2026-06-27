Pillars
=======

Declare Once
------------

Crew definitions should be portable across supported runtimes. Framework
specificity belongs in adapters and optional extras, not in the basic
crew schema.

Data And Context Move Together
------------------------------

``AgenticData`` should carry the current extended data value, active
provider context, active runtime context, logging context, and
tool/capability registry. It should extend ``VendorData``; it should not
duplicate ``ExtendedData`` or provider behavior.

Lazy by Default
---------------

Optional frameworks, vendor SDKs, and tool packages must be imported
only when their runner or tool is used.

Capabilities Over Boilerplate
-----------------------------

Agent runners and tools should declare capabilities with decorators
collected by ``__init_subclass__``. Dynamic facade methods are allowed
only when they route to declared capabilities.

Clear Boundaries
----------------

This package does not own data primitives or vendor APIs. It composes
``extended-data`` and ``vendor-fabric`` when those capabilities are
installed. Provider connectors and dispatch stay in ``vendor-fabric``;
framework-specific and agent-facing wrappers built from those capabilities
stay in this package.

Testable Adapters
-----------------

Every runner and tool adapter should have unit coverage for resolution,
availability, and failure behavior. End-to-end tests can stay optional
and marked by runtime.

Frameworks Are Optional, Contracts Are Not
------------------------------------------

CrewAI, LangGraph, Strands, and local CLI runners can be optional
installs. Their availability, missing dependency messages, fixture
behavior, and runtime selection order must still be documented and
tested.
