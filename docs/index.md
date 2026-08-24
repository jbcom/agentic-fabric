---
title: Agentic Fabric
description: Framework-agnostic orchestration for YAML-defined agent fabrics.
---

![Woven configuration, runtime, and tool boundaries flowing through Agentic Fabric.](assets/agentic-fabric-hero.jpg)

`agentic-fabric` is the standalone orchestration package for framework-agnostic agent fabrics. It discovers YAML fabric agent definitions, selects an installed runtime, and runs the same fabric agent on CrewAI, LangGraph, Strands, or local CLI runners.

``` bash
pip install agentic-fabric
pip install "agentic-fabric[langgraph]"
pip install "agentic-fabric[strands]"
pip install "agentic-fabric[a2a]"
pip install "agentic-fabric[mcp]"
pip install "agentic-fabric[scraping]"
```

Local CLI runners are part of the core install because they shell out to external executables and require no third-party Python framework. LangGraph, Strands, A2A, MCP, scraping helpers, and vendor providers are opt-in extras. CrewAI support stays lazy but CrewAI itself is an external install while its ChromaDB dependency path has an upstream critical advisory with no patched version.

`vendor-fabric` is the required provider layer. Provider SDKs remain opt-in through matching `anthropic`, `aws`, `cursor`, `github`, `google`, `meshy`, `secrets-sync`, `slack`, `vault`, and `zoom` passthrough extras.

Core imports stay lightweight. Optional frameworks and vendor SDKs are loaded only when a runner, tool, or adapter is resolved.
