# Context Priming

**Proactive context synthesis for coding agents.**

Instead of reactively compressing context when the window fills up, Context Priming makes coding agents *construct their optimal starting context* before beginning any task.

## The Problem

LLM coding agents (Claude Code, Copilot, Cursor, etc.) manage context reactively:
- **Auto-compaction** fires when the window is ~95% full — by then, quality has already degraded
- **Memory files** are loaded wholesale regardless of task relevance
- **Static context** (CLAUDE.md, AGENTS.md) is one-size-fits-all
- **RAG** requires the agent to know what to ask for

The result: agents start tasks with either too little context (cold start), too much irrelevant context (bloat), or context optimized for a different task entirely.

## The Proposal

Context Priming inverts the approach. Before executing any task, the agent:

1. **Analyzes the task** — parses user request, identifies true intent and outcome hierarchy
2. **Gathers sources** — scans memories, codebase, git history, flagged priorities, past mistakes
3. **Scores relevance** — filters everything against *this specific task*
4. **Synthesizes** — constructs a compact, task-optimized starting context
5. **Frames outcomes** — prepends the goal hierarchy (final → mid-term → immediate)

```
Task arrives → Agent primes itself → Agent works with optimal context
```

This is **constructive** (builds the right context) rather than **reductive** (compresses the wrong one).

## Quick Start

### Install

```bash
pip install -e ".[anthropic]"
export ANTHROPIC_API_KEY=sk-...
```

### CLI

```bash
# Full priming pipeline
context-prime prime --task "Fix the auth middleware bug" --project ./myapp --verbose

# Gather sources only (see what's available)
context-prime gather --project ./myapp

# Prime only, output as JSON
context-prime prime --task "Add pagination" --project . --format json
```

### Prototype (standalone demo)

```bash
cd prototype
pip install -r requirements.txt

# Prime + execute with raw API
python prime_agent.py "Fix the auth middleware bug" --project /path/to/project --verbose

# Prime only (see the synthesized context)
python prime_agent.py "Add pagination" --project . --prime-only

# Use Claude Agent SDK for full tool access
python prime_agent.py "Refactor the database layer" --project . --use-sdk
```

### As a Library

```python
from context_prime import gather_all, score_relevance, filter_relevant
from context_prime import infer_hierarchy, synthesize_context

# Bring your own LLM call
def my_llm(prompt: str) -> str:
    return my_api.complete(prompt)

# 1. Gather
sources = gather_all("./myapp")

# 2. Score + filter
scored = score_relevance("Fix the auth bug", sources, my_llm)
relevant = filter_relevant(scored, threshold=0.5)

# 3. Hierarchy
hierarchy = infer_hierarchy("Fix the auth bug", project_context, my_llm)

# 4. Synthesize
primed = synthesize_context("Fix the auth bug", hierarchy, relevant, my_llm)
```

### Claude Agent SDK (recommended for production)

```python
from context_prime.adapters.claude_sdk import run_primed_agent

await run_primed_agent(
    task="Fix the auth middleware bug",
    project_dir="./myapp",
    agent_model="claude-opus-4-6",
    priming_model="claude-sonnet-4-6",
)
```

### Claude Code Hook (for existing Claude Code users)

Add to `.claude/settings.json`:

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

## Architecture

```
context-prime
│
├── Core Engine (model-agnostic)
│   ├── gather.py     — Scan memories, codebase, git, config
│   ├── score.py      — LLM relevance scoring per task
│   ├── hierarchy.py  — Outcome hierarchy inference
│   └── synthesize.py — Merge into primed context block
│
├── Adapters
│   ├── claude_sdk.py  — Claude Agent SDK (full context control)
│   ├── claude_hook.sh — Claude Code hooks (SessionStart/UserPromptSubmit)
│   └── raw_api.py     — Any Chat Completions API
│
└── CLI
    └── context-prime prime --task "..." --project ./myapp
```

The core engine is model-agnostic — every LLM call takes a `callable(prompt) -> str`. The adapters handle platform-specific context injection.

## Key Differentiators

| Property | Auto-compact | RAG | MEMORY.md | Context Priming |
|----------|-------------|-----|-----------|----------------|
| Proactive | No | Partial | No | **Yes** |
| Task-specific | No | Partial | No | **Yes** |
| Multi-source | No | No | No | **Yes** |
| Goal-aware | No | No | No | **Yes** |
| Cold-start capable | No | Partial | No | **Yes** |

## Soft Compaction

We call this **"soft compaction"** — it's not compressing what's already in the window, it's *constructing what should be there from scratch*:

- **Hard compaction**: Context is full → summarize/truncate → hope nothing important was lost
- **Soft compaction**: Task arrives → synthesize optimal context from all sources → start clean

## Outcome Hierarchy

Agents don't just see the task — they understand what it serves:

```
Final Outcome:     Ship the v2 platform by Q2
                        │
Mid-term Goal:     Complete the database migration
                        │
Immediate Task:    Fix the failing migration test
```

## Whitepaper

See [`whitepaper/context-priming-whitepaper.md`](whitepaper/context-priming-whitepaper.md) for the full research paper with literature survey, architecture proposal, platform analysis, and prototype results.

## Project Structure

```
context-priming/
├── context_prime/          # pip-installable library
│   ├── core/               # Model-agnostic priming engine
│   │   ├── gather.py       # Source gathering
│   │   ├── score.py        # Relevance scoring
│   │   ├── hierarchy.py    # Outcome hierarchy inference
│   │   └── synthesize.py   # Context synthesis
│   ├── adapters/           # Platform integrations
│   │   ├── claude_sdk.py   # Claude Agent SDK
│   │   ├── claude_hook.sh  # Claude Code hooks
│   │   └── raw_api.py      # Raw API (any provider)
│   └── cli.py              # CLI entry point
├── prototype/              # Standalone Agent SDK demo
│   ├── prime_agent.py      # End-to-end prototype
│   └── example_memories/   # Sample memory files
├── whitepaper/             # Research paper
└── pyproject.toml          # Package config
```

## Related Work

- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618) — Evolving contexts for self-improving LLMs (ICLR 2026)
- [SimpleMem](https://github.com/aiming-lab/SimpleMem) — Efficient lifelong memory for LLM agents
- [ContextKit](https://github.com/FlineDev/ContextKit) — Planning system for Claude Code
- [Anthropic's Context Engineering Guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [ContextBench](https://arxiv.org/abs/2602.05892) — Benchmark for context retrieval in coding agents
- [OpenCode](https://github.com/opencode-ai/opencode) — Open-source AI coding agent (potential integration target)

## License

MIT

---

*[199 Biotechnologies](https://github.com/199-biotechnologies) — February 2026*
