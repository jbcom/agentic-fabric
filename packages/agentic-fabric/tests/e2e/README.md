# End-to-End Tests

This directory contains end-to-end tests for framework runners (CrewAI, LangGraph, Strands).

## Overview

E2E tests verify that each framework runner works correctly with:
- Real LLM API calls
- Complete fabric_agent execution flows
- Multi-agent collaboration
- Knowledge source integration
- Tool usage

## Running E2E Tests

E2E tests are **disabled by default** to avoid:
- Unexpected API costs
- Network dependency in CI/CD
- Slow test execution

### Two marker systems

E2E tests carry both the local markers (`e2e`, `crewai`/`langgraph`/`strands`)
and the published `pytest-agentic-fabric` markers (`agentic_e2e`,
`agentic_runtime("crewai")`). Either system can enable them:

```bash
# Local markers (requires --e2e flag)
uv run pytest tests/e2e/ --e2e -v

# Published plugin markers (requires --agentic-e2e flag)
uv run pytest tests/e2e/ --agentic-e2e -v
```

### Run framework-specific tests

```bash
# Only CrewAI tests
uv run pytest tests/e2e/ --e2e --framework=crewai -v

# Only LangGraph tests (requires langgraph installed)
uv run pytest tests/e2e/ --e2e --framework=langgraph -v

# Only Strands tests (requires strands-agents installed)
uv run pytest tests/e2e/ --e2e --framework=strands -v
```

### Run specific test

```bash
uv run pytest tests/e2e/test_crewai_e2e.py::TestCrewAISimpleExecution::test_simple_crew_execution --e2e -v
```

## Local Ollama E2E (no API key needed)

E2E tests can run against a local [Ollama](https://ollama.com) instance instead
of Anthropic/AWS Bedrock. This is the mode used in CI (`.github/workflows/e2e-ollama.yml`).

### Prerequisites

1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Start the server: `ollama serve &`
3. Pull a small model: `ollama pull qwen2.5:0.5b`

### Running

```bash
# Set env vars to route runners to Ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=qwen2.5:0.5b
export AGENTIC_FABRIC_LLM_PROVIDER=ollama

# Run e2e tests — no API key needed
uv run pytest tests/e2e/ --e2e -v
```

When `AGENTIC_FABRIC_LLM_PROVIDER=ollama` is set:
- **CrewAI** routes through litellm's `ollama_chat/` provider
- **LangGraph** uses `langchain_ollama.ChatOllama`
- **Strands** uses `strands.models.ollama.OllamaModel`

### Recommended models for CI

| Model | Size | Reliability | Notes |
|-------|------|-------------|-------|
| `qwen2.5:0.5b` | ~400 MB | Good for simple Q&A | **Recommended** — smallest reliable model |
| `qwen2.5:1.5b` | ~1 GB | Better | More world knowledge |
| `llama3.2:1b` | ~1.3 GB | Good | Alternative |

Use `qwen2.5:0.5b` for CI. It reliably answers "What is 2+2?" and "What is the
capital of France?" at temperature 0.

### Test assertions

Assertions use `in` checks (e.g., `"4" in result`, `"paris" in result.lower()`)
rather than exact matches, since small models may include extra text.

## Environment Variables

### For Anthropic (default, non-Ollama)

- `ANTHROPIC_API_KEY` - For Claude LLM (CrewAI, LangGraph)

### For Strands with AWS Bedrock

- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `AWS_REGION` - AWS region (e.g., `us-west-2`)

### For Ollama (local, no API key)

- `OLLAMA_BASE_URL` - Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - Model name (default: `qwen2.5:0.5b`)
- `AGENTIC_FABRIC_LLM_PROVIDER` - Set to `ollama` to force Ollama mode

#### Bedrock Model IDs

When using Strands with Bedrock (non-Ollama), use the official model IDs:

| Model | Bedrock Model ID |
|-------|------------------|
| Claude Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` |
| Claude Sonnet 4.5 | `anthropic.claude-sonnet-4-5-20250929-v1:0` |

## CI/CD Integration

### Ollama E2E workflow

The `.github/workflows/e2e-ollama.yml` workflow runs E2E tests against a local
Ollama instance on every PR and push to `main`. It:

1. Installs Ollama and pulls `qwen2.5:0.5b`
2. Installs all framework extras + crewai
3. Runs `pytest tests/e2e/ --e2e` with `AGENTIC_FABRIC_LLM_PROVIDER=ollama`

This verifies the runner→LLM integration for all three frameworks without API
keys or cloud credentials.

### Traditional (Anthropic/AWS) E2E

For scheduled runs with real cloud LLMs, use secrets:

```yaml
# .github/workflows/e2e.yml
name: E2E Tests (Cloud)
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hynek/setup-cached-uv@v2
      - run: uv sync --extra tests --extra langgraph --extra strands
      - run: uv pip install crewai
      - run: uv run pytest tests/e2e/ --e2e -v
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Writing New E2E Tests

1. Mark tests with `@pytest.mark.e2e` (local) and `@pytest.mark.agentic_e2e` (published)
2. Add framework marker: `@pytest.mark.crewai` and `@pytest.mark.agentic_runtime("crewai")`
3. Use `check_api_key` fixture to verify required credentials (skips if not set)
4. Keep tests focused and minimal to reduce API costs
5. Use `in` assertions (not exact match) for LLM responses

Example:

```python
@pytest.mark.e2e
@pytest.mark.crewai
@pytest.mark.agentic_e2e
@pytest.mark.agentic_runtime("crewai")
def test_my_feature(
    check_api_key: None,
    simple_fabric_agent_config: dict[str, Any],
) -> None:
    """Test my new feature."""
    from agentic_fabric.runners.crewai_runner import CrewAIRunner

    runner = CrewAIRunner()
    result = runner.build_and_run(simple_fabric_agent_config, {"input": "test"})
    assert result is not None
```

## Debugging

If tests fail:

1. Check API key is set: `echo $ANTHROPIC_API_KEY`
2. Or check Ollama is running: `curl http://localhost:11434/api/tags`
3. Verify framework is installed: `pip list | grep crewai`
4. Run with verbose output: `-vv`
5. Run single test to isolate issue

## Cost Considerations

### Cloud LLM (Anthropic/AWS)

E2E tests make real API calls which incur costs:
- **Total estimated cost per full E2E run**: ~$0.16-1.10

### Local Ollama

E2E tests with Ollama are **free** — no API costs, fully local.
Pull time is ~20-40s cold (cached after first run).

To minimize costs:
- Use Ollama mode for CI (`AGENTIC_FABRIC_LLM_PROVIDER=ollama`)
- Run cloud-based E2E only on schedule or manually
- Use `--framework` filter for specific tests