<div align="center">

# Context Priming

**Proactive context synthesis for coding agents. Build the right context before the first token.**

[![Star this repo](https://img.shields.io/github/stars/199-biotechnologies/context-priming?style=for-the-badge&logo=github&label=%E2%AD%90%20Star%20this%20repo&color=yellow)](https://github.com/199-biotechnologies/context-priming/stargazers)
[![Follow @longevityboris](https://img.shields.io/badge/Follow_%40longevityboris-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/longevityboris)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-cc785c?style=for-the-badge&logo=anthropic&logoColor=white)](https://docs.anthropic.com/en/docs/claude-code)

</div>

---

Coding agents start every task with the wrong context. They load static memory files, bloat the window with irrelevant code, or start cold with nothing at all. Then they hit the context limit and auto-compact throws away half of what they gathered.

Context Priming fixes this. It analyzes the task, scans all available sources, scores relevance, and synthesizes a compact starting context _before the agent writes a single line of code_. Constructive, not reductive. Task-specific, not one-size-fits-all.

**[Why This Exists](#why-this-exists)** | **[Before vs After](#before-vs-after)** | **[Install](#install)** | **[Quick Start](#quick-start)** | **[How It Works](#how-it-works)** | **[Features](#features)** | **[Whitepaper](#whitepaper)** | **[Contributing](#contributing)** | **[License](#license)**

---

## Why This Exists

LLM coding agents manage context reactively. They wait until the window fills, then compress. This is backwards.

- **Auto-compaction** fires at ~95% capacity. Quality has already degraded by then.
- **Memory files** load wholesale regardless of what the task actually needs.
- **Static context** (CLAUDE.md, AGENTS.md) is the same for every task.
- **RAG** requires the agent to know what to ask for. It often doesn't.

The result: cold starts, context bloat, or context optimized for a different task entirely. Agents spend their best tokens figuring out what they should already know.

## Before vs After

### Without Priming

```
Task arrives
  → Agent starts cold (no relevant context)
  → Agent explores codebase (burns tokens on discovery)
  → Context window fills with exploration artifacts
  → Auto-compact fires (loses important details)
  → Agent works with degraded context
```

### With Priming

```
Task arrives
  → Context Priming analyzes the task
  → Scans memories, codebase, git history, configs
  → Scores and filters for this specific task
  → Synthesizes compact, goal-aware starting context
  → Agent starts with exactly what it needs
```

The difference: agents spend tokens on the work, not on figuring out what the work is.

## Install

```bash
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=sk-...
```

Supports Python 3.11+. Optional extras: `openai`, `claude-sdk`, or `all`.

## Quick Start

### CLI

```bash
# Full priming pipeline
context-prime prime --task "Fix the auth middleware bug" --project ./myapp --verbose

# Gather sources only (see what's available)
context-prime gather --project ./myapp

# Prime and output as JSON
context-prime prime --task "Add pagination" --project . --format json
```

### As a Library

```python
from context_prime import gather_all, score_relevance, filter_relevant
from context_prime import infer_hierarchy, synthesize_context

# Bring your own LLM call
def my_llm(prompt: str) -> str:
    return my_api.complete(prompt)

# 1. Gather all sources
sources = gather_all("./myapp")

# 2. Score and filter for this task
scored = score_relevance("Fix the auth bug", sources, my_llm)
relevant = filter_relevant(scored, threshold=0.5)

# 3. Infer outcome hierarchy
hierarchy = infer_hierarchy("Fix the auth bug", project_context, my_llm)

# 4. Synthesize primed context
primed = synthesize_context("Fix the auth bug", hierarchy, relevant, my_llm)
```

### Claude Agent SDK

```python
from context_prime.adapters.claude_sdk import run_primed_agent

await run_primed_agent(
    task="Fix the auth middleware bug",
    project_dir="./myapp",
    agent_model="claude-opus-4-6",
    priming_model="claude-sonnet-4-6",
)
```

### Claude Code Hook

Drop this into `.claude/settings.json` to prime every session automatically:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "python -m context_prime.cli prime --project $CLAUDE_PROJECT_DIR --mode session --format hook",
        "timeout": 30
      }]
    }]
  }
}
```

### Standalone Prototype

```bash
cd prototype
pip install -r requirements.txt

# Prime and execute
python prime_agent.py "Fix the auth middleware bug" --project /path/to/project --verbose

# Prime only (inspect the synthesized context)
python prime_agent.py "Add pagination" --project . --prime-only
```

## How It Works

Context Priming runs a four-stage pipeline before the agent begins any task:

```
┌─────────────────────────────────────────────────────┐
│                  CONTEXT PRIMING                     │
│                                                      │
│  1. GATHER    Scan memories, codebase, git history,  │
│               configs, flagged priorities             │
│                                                      │
│  2. SCORE     LLM-based relevance scoring per task   │
│               Filter below threshold                  │
│                                                      │
│  3. FRAME     Infer outcome hierarchy                │
│               Final → Mid-term → Immediate            │
│                                                      │
│  4. SYNTHESIZE  Merge into compact primed context    │
│                 Goal-aware, task-specific              │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
              Agent starts with optimal context
```

The core engine is model-agnostic. Every LLM call takes a `callable(prompt) -> str`. Adapters handle platform-specific context injection for Claude Code, Claude Agent SDK, and any Chat Completions API.

### Outcome Hierarchy

Agents don't just see the task. They understand what it serves:

```
Final Outcome:     Ship the v2 platform by Q2
                        │
Mid-term Goal:     Complete the database migration
                        │
Immediate Task:    Fix the failing migration test
```

This prevents agents from making locally correct but globally wrong decisions.

### Soft Compaction

We call this **soft compaction** -- constructing what should be in the window, rather than compressing what's already there:

| | Hard Compaction | Soft Compaction |
|---|---|---|
| **When** | Context window full | Before task starts |
| **How** | Summarize/truncate | Synthesize from all sources |
| **Risk** | Loses important details | None (additive) |
| **Result** | Degraded context | Optimal context |

## Features

| Property | Auto-compact | RAG | MEMORY.md | Context Priming |
|---|---|---|---|---|
| Proactive | No | Partial | No | **Yes** |
| Task-specific | No | Partial | No | **Yes** |
| Multi-source | No | No | No | **Yes** |
| Goal-aware | No | No | No | **Yes** |
| Cold-start capable | No | Partial | No | **Yes** |

### Architecture

```
context-prime/
├── context_prime/          # pip-installable library
│   ├── core/               # Model-agnostic priming engine
│   │   ├── gather.py       # Source gathering (memories, code, git, config)
│   │   ├── score.py        # LLM relevance scoring per task
│   │   ├── hierarchy.py    # Outcome hierarchy inference
│   │   └── synthesize.py   # Context synthesis
│   ├── adapters/           # Platform integrations
│   │   ├── claude_sdk.py   # Claude Agent SDK
│   │   ├── claude_hook.sh  # Claude Code hooks
│   │   └── raw_api.py      # Any Chat Completions API
│   └── cli.py              # CLI entry point
├── prototype/              # Standalone demo
├── whitepaper/             # Research paper
└── pyproject.toml
```

## Whitepaper

The full research paper covers literature survey, architecture proposal, platform analysis, and prototype results: [`whitepaper/context-priming-whitepaper.md`](whitepaper/context-priming-whitepaper.md)

## Related Work

- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618) -- Evolving contexts for self-improving LLMs (ICLR 2026)
- [SimpleMem](https://github.com/aiming-lab/SimpleMem) -- Efficient lifelong memory for LLM agents
- [ContextKit](https://github.com/FlineDev/ContextKit) -- Planning system for Claude Code
- [Anthropic's Context Engineering Guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [ContextBench](https://arxiv.org/abs/2602.05892) -- Benchmark for context retrieval in coding agents

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)

---

<div align="center">

Built by [Boris Djordjevic](https://github.com/longevityboris) at [199 Biotechnologies](https://github.com/199-biotechnologies) | [Paperfoot AI](https://paperfoot.ai)

[![Star this repo](https://img.shields.io/github/stars/199-biotechnologies/context-priming?style=for-the-badge&logo=github&label=%E2%AD%90%20Star%20this%20repo&color=yellow)](https://github.com/199-biotechnologies/context-priming/stargazers)
[![Follow @longevityboris](https://img.shields.io/badge/Follow_%40longevityboris-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/longevityboris)

</div>
