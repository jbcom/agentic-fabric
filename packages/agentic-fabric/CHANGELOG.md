# CHANGELOG

<!-- version list -->

## [1.3.0](https://github.com/jbcom/agentic-fabric/compare/agentic-fabric-v1.2.3...agentic-fabric-v1.3.0) (2026-08-24)


### Features

* **repo:** establish sourcey agentic release controls ([340d16d](https://github.com/jbcom/agentic-fabric/commit/340d16da24f354470ff603e3991ebdb13c39d68b))
* **repo:** establish sourcey agentic release controls ([268d298](https://github.com/jbcom/agentic-fabric/commit/268d2983a5df51d2514f0ad725158f5abc46168b))

## [1.2.3](https://github.com/jbcom/agentic-fabric/compare/agentic-fabric-v1.2.2...agentic-fabric-v1.2.3) (2026-08-22)


### Bug Fixes

* align MCP adapter dependencies ([66a1a72](https://github.com/jbcom/agentic-fabric/commit/66a1a72535be435f25663e8a843019da3b5db2e0))

## [1.2.2](https://github.com/jbcom/agentic-fabric/compare/agentic-fabric-v1.2.1...agentic-fabric-v1.2.2) (2026-07-27)


### Bug Fixes

* harden security, close config drift, fix real lint suppressions ([#22](https://github.com/jbcom/agentic-fabric/issues/22)) ([42e7d5d](https://github.com/jbcom/agentic-fabric/commit/42e7d5d52cda2141a90b4b61e238867a11911c5f))

## [1.2.1](https://github.com/jbcom/agentic-fabric/compare/agentic-fabric-v1.2.0...agentic-fabric-v1.2.1) (2026-07-27)


### Bug Fixes

* resolve ruff 0.16 lint fallout across workspace ([#19](https://github.com/jbcom/agentic-fabric/issues/19)) ([7666a78](https://github.com/jbcom/agentic-fabric/commit/7666a7855d5b308d87541863abaea8f1f196bc2d))

## [1.2.0](https://github.com/jbcom/agentic-fabric/compare/agentic-fabric-v1.1.0...agentic-fabric-v1.2.0) (2026-06-27)


### Features

* fix all assessment findings + add Ollama E2E support ([#4](https://github.com/jbcom/agentic-fabric/issues/4)) ([37cc3b6](https://github.com/jbcom/agentic-fabric/commit/37cc3b6b62de867676d37a7959dab955ac1d331c))

## [1.1.0](https://github.com/jbcom/agentic-fabric/compare/agentic-fabric-v1.0.0...agentic-fabric-v1.1.0) (2026-06-27)


### Features

* bootstrap agentic fabric workspace ([#1](https://github.com/jbcom/agentic-fabric/issues/1)) ([2704e67](https://github.com/jbcom/agentic-fabric/commit/2704e6758a77661477c01678073a1b78ca1abcbc))

## v1.0.0 (2025-12-25)

### Initial Stable Release

Framework-agnostic AI fabric agent orchestration is now production-ready!

### Features

- **Multi-Framework Support**: Run fabric agents on CrewAI, LangGraph, or Strands
- **Auto-Detection**: Automatically selects best available framework
- **Universal YAML Format**: Define once, run anywhere
- **Single-Agent CLI Runners**: Support for aider, claude-code, ollama, and more
- **MCP Adapters**: Expose vendor-fabric catalog/data methods and Meshy capability metadata over MCP
- **Knowledge Base Integration**: Load domain knowledge from markdown files
- **Agent Archetypes**: Reusable agent templates
- **Comprehensive Testing**: 122+ unit tests, E2E test suite

### Breaking Changes

- **Minimum Python version increased from 3.10 to 3.11**
  - Required for CrewAI 1.5.0+ compatibility
  - Python 3.11, 3.12, 3.13, 3.14 now supported

### Documentation

- Complete API documentation with Sphinx
- Quick start guide and architecture overview
- jbcom dark theme branding applied
- Integration guides for vendor-fabric

### Internal

- Full test coverage across all runners
- Ruff linting and formatting
- Type hints with mypy
- Tox for multi-version testing
