Vendor Fabric Integration
=========================

``agentic-fabric`` does not declare passthrough ``vendor-fabric`` extras
until ``vendor-fabric`` is published and resolvable from PyPI. The core
package still imports without vendor SDKs installed.

The integration rule is simple: vendor IO, provider capability metadata,
and SecretSync behavior belong in ``vendor-fabric``; crew orchestration,
runtime selection, and agent-facing framework wrappers belong here.

``AgenticData`` subclasses ``VendorData`` when ``vendor-fabric`` is
installed. Until then, it keeps runtime context importable and raises
clear guidance for vendor-backed operations.

Vendor-backed tools use lazy references:

.. code:: python

   from agentic_fabric.tools.registry import resolve_tool

   tool = resolve_tool("vendor://github/get_file")
   result = tool(path="README.md")

Those wrappers route through ``AgenticData.call`` and ``VendorData``
capabilities. Agent code should not import cloud SDKs or provider
clients directly.

When ``vendor-fabric`` is installed, downstream agent/session classes can
also expose a provider catalog from the superclass:

.. code:: python

   from agentic_fabric import AgenticData


   session = AgenticData()
   github_tools = session.vendor_tools("github", include_unavailable=False)

``vendor_tools()`` reads ``VendorData.capabilities()`` and converts each
capability route into a lazy ``VendorCapabilityTool``. The provider
connectors, install availability, and dispatch behavior still come from
``vendor-fabric``.
