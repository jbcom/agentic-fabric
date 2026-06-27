# Examples

These examples are intentionally executable in CI. They avoid live LLM calls
and optional framework imports unless explicitly noted, so they also serve as
integration checks for the public API.

```bash
python examples/discovery_workflow.py
python examples/tool_registry.py
python examples/runtime_context.py
python examples/mcp_adapters.py
```

The bundled `sample_workspace/` directory demonstrates a framework-agnostic
`.fabric/` layout.

`mcp_adapters.py` shows the agentic-fabric-owned MCP entry points and a
client configuration shape without importing the MCP SDK or provider packages.
