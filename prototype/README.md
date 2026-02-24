# Context Priming — Agent SDK Prototype

End-to-end demonstration of Context Priming. The agent primes itself before starting work by gathering sources, scoring relevance, inferring the outcome hierarchy, and synthesizing an optimal starting context.

## Quick Start

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...

# Prime + execute
python prime_agent.py "Fix the auth middleware bug" --project /path/to/project

# Prime only (see the primed context without executing)
python prime_agent.py "Add pagination to the API" --project . --prime-only --verbose

# Use Agent SDK for execution (if installed)
pip install claude-code-sdk
python prime_agent.py "Refactor the database layer" --project . --use-sdk
```

## What It Does

```
Task → Gather → Score → Hierarchy → Synthesize → Execute
        │         │        │            │           │
     memories   filter   infer       merge      agent starts
     codebase   by task  goals      sources     with primed
     git log    relevance            into one    context
     config                          briefing
```

1. **Gather** — Scans memory files, codebase structure, git history, project config
2. **Score** — LLM scores each source's relevance to the specific task (0.0-1.0)
3. **Hierarchy** — LLM infers the outcome hierarchy (immediate → mid-term → final goal)
4. **Synthesize** — LLM merges relevant sources into a dense, task-specific briefing
5. **Execute** — Agent starts with the synthesized context as its system prompt

## Flags

| Flag | Description |
|------|-------------|
| `--project, -p` | Project directory (default: `.`) |
| `--verbose, -v` | Show priming details (sources found, scores, timing) |
| `--prime-only` | Output the primed context without running the agent |
| `--use-sdk` | Use Claude Agent SDK for execution (tools, file editing) |
| `--priming-model` | Model for priming steps (default: `claude-sonnet-4-6`) |
| `--agent-model` | Model for execution (default: `claude-opus-4-6`) |

## Architecture

The prototype uses a fast model (Sonnet) for the 3 priming LLM calls and the best model (Opus) for the actual coding work. This keeps priming overhead low (~5-10s) while maximizing execution quality.
