# Agentic Fabric Workspace

This repository is the future public `jbcom/agentic-fabric` workspace.

Documentation: [jonbogaty.com/agentic-fabric](https://jonbogaty.com/agentic-fabric/)

Read `AGENTS.md` first in Codex sessions; it contains the active local
migration plan and hand-off instructions.

The active branch is `codex/agentic-fabric-bootstrap`. This repository should
be completed after `extended-data` and `vendor-fabric`, because its
`AgenticData` design depends on their final contracts.

Current implemented surface includes `AgenticData`, lazy runtime registry
metadata, capability decorators, vendor-tool references, and the sibling
`pytest-agentic-fabric` package.
