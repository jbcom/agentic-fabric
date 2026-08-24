---
title: Contributing
description: How trusted upstream agents and external contributors work safely in this public repository.
---

# Contributing

Read the repository-root [`AGENTS.md`](https://github.com/jbcom/agentic-fabric/blob/main/AGENTS.md) before changing this workspace. It defines the package boundaries, supported Python versions, validation matrix, and release rules.

## Development flow

1. Create an upstream topic branch from `main`; do not push ordinary work directly to `main`.
2. Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, and so on).
3. Run the targeted checks, then the complete tox matrix before requesting merge.
4. Open a pull request. Automated checks and review integrations report findings; address them with normal additional commits.
5. When the branch needs synchronization, merge `main` into it. Do not rebase shared history or force-push.
6. Merge only with a merge commit after every required automated gate passes. Squash and rebase merges are intentionally disabled.

External forks are welcome, but their workflow code, dependencies, artifacts, and generated output are treated as untrusted. Trusted agents work on branches in this upstream repository and still satisfy the same policy gates without routine human approval.

## Before you send a change

```bash
uv sync --all-packages --all-extras --dev
pre-commit run --all-files
tox -e lint,typecheck,audit,py311,py312,py313,py314,coverage,plugin,examples,docs,build
```

The docs check regenerates the API-reference page and builds the Sourcey site. Never hand-edit package versions or tags: release-please owns that lifecycle.
