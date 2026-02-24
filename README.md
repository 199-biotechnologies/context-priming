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

## Key Differentiators

| Property | Auto-compact | RAG | MEMORY.md | Context Priming |
|----------|-------------|-----|-----------|----------------|
| Proactive | No | Partial | No | **Yes** |
| Task-specific | No | Partial | No | **Yes** |
| Multi-source | No | No | No | **Yes** |
| Goal-aware | No | No | No | **Yes** |
| Cold-start capable | No | Partial | No | **Yes** |

## Soft Compaction

We call this **"soft compaction"** — it's not compressing what's already in the window, it's *constructing what should be there from scratch*. The distinction matters:

- **Hard compaction**: Context is full → summarize/truncate → hope nothing important was lost
- **Soft compaction**: Task arrives → synthesize optimal context from all sources → start clean

## Outcome Hierarchy

A unique aspect of Context Priming is goal awareness. Agents don't just see the task — they understand what it serves:

```
Final Outcome:     Ship the v2 platform by Q2
                        │
Mid-term Goal:     Complete the database migration
                        │
Immediate Task:    Fix the failing migration test
```

This prevents narrow optimizations that conflict with broader objectives.

## Whitepaper

See [`whitepaper/context-priming-whitepaper.md`](whitepaper/context-priming-whitepaper.md) for the full research paper with detailed analysis of existing approaches, the complete architecture proposal, and references.

## Status

This is a concept proposal backed by a survey of the current landscape (February 2026). The building blocks exist — memory systems, codebase indexing, planning frameworks, context compression — but nobody has built the orchestration layer that synthesizes them into a single, task-optimized starting context.

## Related Work

- [ACE: Agentic Context Engineering](https://arxiv.org/abs/2510.04618) — Evolving contexts for self-improving LLMs (ICLR 2026)
- [SimpleMem](https://github.com/aiming-lab/SimpleMem) — Efficient lifelong memory for LLM agents
- [ContextKit](https://github.com/FlineDev/ContextKit) — Planning system for Claude Code
- [Anthropic's Context Engineering Guide](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [ContextBench](https://arxiv.org/abs/2602.05892) — Benchmark for context retrieval in coding agents

## License

MIT

---

*[199 Biotechnologies](https://github.com/199-biotechnologies) — February 2026*
