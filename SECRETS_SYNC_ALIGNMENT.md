# SecretSync Alignment

This file locks the intended SecretSync boundary for `agentic-fabric`.

## Canonical Stack

1. `secrets-sync` owns the Go runtime and gopy binding source.
2. `vendor-fabric` owns the Python facade, credential handoff, and
   `VendorData`-level capability surface.
3. `agentic-fabric` owns runtime selection, tool wrapping, and orchestration.

## Binding Contract

- PyPI distribution: `secrets-sync-python-binding`
- Python import/module: `secrets_sync`
- This repository should not import `secrets_sync` directly; it should consume
  SecretSync through `vendor-fabric`.

## This Repository's Role

- Turn SecretSync-related vendor capabilities into framework-visible tools for
  CrewAI, LangGraph, Strands, MCP, and related runtimes.
- Preserve the superclass chain `ExtendedData -> VendorData -> AgenticData`.
- Keep install guidance honest: vendor extras and agent runtime extras are
  separate concerns unless an explicit passthrough extra is later added.

## Required Direction

- Access SecretSync through `VendorData` and `vendor-fabric` capabilities.
- Keep agent/session abstractions additive over the vendor layer.
- Let runners and tool registries decide how SecretSync becomes usable in a
  given runtime without re-owning provider logic here.

## Forbidden Drift

- Do not import or bind directly to the SecretSync Go runtime from here.
- Do not own credential handoff, provider clients, or binding plumbing here.
- Do not document fake aggregate extras that do not actually exist.
