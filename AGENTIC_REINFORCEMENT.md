# Agentic Reinforcement

This repository creates the runtime- and agent-aware superclass on top of
`VendorData`.

## AgenticData Contract

- `AgenticData` extends `VendorData`, not `ExtendedData` directly.
- Preserve vendor-layer semantics while adding runtime context, fabric agent registry
  behavior, runner dispatch, and agent-facing tool exposure.
- The local `_VendorDataBase` fallback is an importability shim, not a second
  architecture. Keep it minimal and temporary in spirit.

## What This Repository Owns

- runtime discovery and selection
- runner registries and runtime adapters
- LangChain, CrewAI, LangGraph, Strands, and MCP-facing tool wrappers
- agent-facing tool catalogs built from vendor capabilities
- fabric agent, session, and agent orchestration context

## What This Repository Does Not Own

- base data primitives
- generic file/workflow/logging primitives
- provider SDK integrations
- provider availability/install guidance beyond delegating to `vendor-fabric`
- reimplementation of the `VendorData` provider dispatch layer

## Hand-Off From Vendor Fabric

- Pull provider capability metadata and typed callables from `vendor-fabric`.
- Decide here how those capabilities become framework tools and runtime-visible
  surfaces.
- If something exists only because an AI framework wants a specific wrapper
  type, keep it here.
- Do not push AI-framework shims back down into `vendor-fabric`.
- Do not bypass `vendor-fabric` to import SecretSync Go bindings or invoke the
  Go runtime directly from this layer.

## Superclass Role

- `AgenticData` is the superclass downstream domain-specific agent/session/task
  objects should extend.
- Downstream apps should build on `AgenticData` rather than recreating provider
  and runtime composition from scratch.
- Agentic behavior is additive over the vendor layer, which is additive over
  the base data layer.
