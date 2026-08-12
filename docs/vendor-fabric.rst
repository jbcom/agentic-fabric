Vendor Fabric Integration
=========================

``vendor-fabric`` is a required ``agentic-fabric`` dependency. Provider SDKs
remain optional: this package declares matching ``anthropic``, ``aws``,
``cursor``, ``github``, ``google``, ``meshy``, ``secrets-sync``, ``slack``,
``vault``, and ``zoom`` passthrough extras.

The integration rule is simple: vendor IO, provider capability metadata,
and the SecretSync Python facade/capability surface belong in
``vendor-fabric``. The SecretSync Go runtime and gopy binding source
belong in ``secrets-sync``. Fabric agent orchestration, runtime selection, and
agent-facing framework wrappers belong here.

``AgenticData`` always subclasses ``VendorData``. This makes the layer contract
explicit and prevents a fallback class from silently creating a second,
incomplete provider-dispatch path.

Vendor-backed tools use lazy references:

.. code:: python

   from agentic_fabric.tools.registry import resolve_tool

   tool = resolve_tool("vendor://github/get_file")
   result = tool(path="README.md")

.. note:: A provider-backed operation still requires its matching optional
   extra and credentials. Base ``vendor-fabric`` does not eagerly import those
   provider SDKs.

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

A2A and MCP ownership follows the same boundary. ``agentic-fabric`` owns Agent
Cards, task events, tool schemas, typed results, and transport entry points.
The underlying connector classes, capability metadata, credentials, and
network calls remain in ``vendor-fabric``. The generic vendor interfaces call
only public package catalog functions, ``VendorData.capabilities()``, and
``AgenticData.call()``; no private registry traversal or connector logic is
duplicated here.
