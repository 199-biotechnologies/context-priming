# Context Priming: Proactive Context Synthesis for Coding Agents

**Authors:** Boris Djordjevic, 199 Biotechnologies
**Date:** February 2026
**Version:** 2.0

---

## Abstract

Large Language Model (LLM) coding agents face a fundamental architectural bottleneck: context management. Current approaches are overwhelmingly *reactive* — compressing, truncating, or summarizing context only when the window fills up. This paper proposes **Context Priming**, a paradigm shift where coding agents *proactively construct* their optimal context before beginning any task. Rather than subtracting information from an overflowing window, the agent synthesizes a purpose-built context from multiple sources: accumulated memories, codebase structure, flagged priorities, past mistakes, and an explicit outcome hierarchy. This "soft compaction" operates as generative context construction — the inverse of the reductive compression that dominates the field today. We survey existing approaches, identify the specific gap Context Priming fills, and propose an architecture for implementation.

---

## 1. Introduction

### 1.1 The Context Crisis

The effectiveness of LLM-based coding agents is fundamentally constrained by what fits in their context window. Despite context windows expanding from 4K to 200K+ tokens between 2023 and 2026, the core problem persists: *having more space doesn't mean you know what to put in it*.

Current coding agents — Claude Code, GitHub Copilot, Cursor, Windsurf, and others — face a recurring failure mode. They begin a task, accumulate context through file reads, tool calls, and conversation turns, then degrade as the context fills with irrelevant artifacts from earlier exploration. Studies have documented "context rot" — the phenomenon where model accuracy on information retrieval decreases as context length increases, even when the information is present in the window (JetBrains Research, 2025).

### 1.2 The Reactive Paradigm

The industry's response has been reactive context management:

- **Auto-compaction** triggers when context reaches a threshold (e.g., Claude Code compacts at 95% capacity)
- **Truncation** drops older messages beyond a sliding window
- **Recursive summarization** compresses conversation history into progressively shorter summaries
- **RAG (Retrieval-Augmented Generation)** fetches relevant documents on demand

All of these approaches share a common assumption: context is something that *accumulates and must be managed*. They are subtractive — their goal is to remove or compress what's already there.

### 1.3 The Priming Alternative

We propose inverting this assumption entirely. Instead of asking *"what should we remove?"*, Context Priming asks *"what is the optimal context to construct for this specific task?"*

A primed agent doesn't start with an empty context and reactively accumulate information. It doesn't start with a full context and reactively compress it. Instead, it begins by *synthesizing* a purpose-built context — drawing from memories, codebase knowledge, past lessons, and goal awareness — and then operates within that optimized frame.

---

## 2. The Problem Space

### 2.1 Why Context Matters More Than Model Capability

Anthropic's own engineering team has stated that "the single most important determinant of AI agent effectiveness is providing the right context" (Anthropic, 2025). The field has converged on this insight: prompt engineering is about *what you say*; context engineering is about *what the model sees*. And what the model sees matters more.

Every token in context costs attention. Larger contexts don't just consume memory — they dilute the model's focus. Research from Voltropy (2026) on Lossless Context Management demonstrated that agents allowed to manage their own memory frequently degrade their own performance through poor prioritization.

### 2.2 The Five Failure Modes

Current coding agents exhibit five recurring failure modes related to context:

1. **Cold-start blindness.** New sessions begin with no relevant context, forcing the agent to rediscover project conventions, architecture, and past decisions from scratch.

2. **Memory bloat.** Accumulated memories and lessons grow into massive files that cannot fit in context, forcing either truncation (losing valuable lessons) or no memory at all.

3. **Goal drift.** Without explicit awareness of the outcome hierarchy, agents optimize for the literal user request rather than the actual desired outcome. A request to "fix this test" may require understanding that the test exists to validate a migration that serves a larger architecture change.

4. **Lesson amnesia.** Past mistakes and their solutions are recorded but never surfaced at the right moment. A memory about "always use absolute imports in this project" is useless if it's buried on line 847 of a memory file when the agent is writing a new module.

5. **Context pollution.** Exploratory tool calls (file reads, searches, failed approaches) accumulate in context and dilute the signal-to-noise ratio for the actual task.

### 2.3 The Cost of Getting Context Wrong

ContextBench (2026), a benchmark for context retrieval in coding agents, demonstrated that even state-of-the-art agents retrieve the wrong context for coding tasks 30-40% of the time. This isn't a model capability issue — it's an architectural one. The agents have access to the right information; they fail to surface it at the right time.

---

## 3. Existing Approaches and Their Limitations

### 3.1 Reactive Compaction

**Examples:** Claude Code auto-compact, Google ADK context compression, Forge Code compaction.

**Approach:** Monitor context usage, trigger summarization when approaching limits.

**Limitation:** By the time compaction fires, context is already degraded. Compaction is lossy — it cannot recover information that was never loaded, and it inevitably discards nuances that may become relevant later. It also treats all context as equally worth compressing, rather than distinguishing between what's essential for the current task and what was merely exploratory.

### 3.2 Memory Systems

**Examples:** Letta/MemGPT (hierarchical memory), SimpleMem (semantic compression), MEMORY.md files.

**Approach:** Store agent experiences in structured memory systems with retrieval mechanisms.

**Limitation:** Memory systems solve *storage* but not *synthesis*. SimpleMem achieves impressive compression (30x token reduction) but still relies on query-time retrieval — the agent must know what to ask for. Memory files like MEMORY.md provide persistence but are loaded wholesale, with no task-specific curation. Letta's hierarchical memory (core, archival, recall) is architecturally sophisticated but optimizes for long-running agent sessions, not for pre-task preparation.

### 3.3 Static Context Loading

**Examples:** elizaOS `/context-prime`, CLAUDE.md files, AGENTS.md conventions.

**Approach:** Load predefined context files (README, project structure, conventions) at session start.

**Limitation:** Static context is one-size-fits-all. A debugging task and a feature implementation task in the same project need fundamentally different context. Loading the same CLAUDE.md regardless of task wastes tokens on irrelevant information and misses task-specific knowledge. Recent research (Koylan, 2026) found that LLM-generated general context actually *decreases* performance by -3% on average on AGENTBENCH, while developer-written context only marginally improves it (+4%).

### 3.4 Planning-First Approaches

**Examples:** ContextKit (4-phase methodology), CodePlan (pseudocode planning).

**Approach:** Structure development into explicit planning phases before implementation.

**Limitation:** Planning-first approaches improve *workflow* but not *context quality*. They tell the agent *how* to work but don't optimize *what the agent sees*. A planning phase that runs inside a polluted context will produce a polluted plan.

### 3.5 Agentic Context Engineering (ACE)

**Reference:** "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" (ICLR 2026).

**Approach:** Treats contexts as evolving playbooks that accumulate, refine, and organize strategies through generation, reflection, and curation. Achieves +10.6% improvement on agent benchmarks.

**Limitation:** ACE focuses on *evolving system prompts over time* — it's about the gradual improvement of standing context through experience. It doesn't address the per-task synthesis problem: given a specific task right now, what is the optimal context to construct from all available sources? ACE evolves the playbook; Context Priming constructs the play.

---

## 4. The Context Priming Proposal

### 4.1 Core Concept

Context Priming is the process by which a coding agent, upon receiving a task, *proactively constructs its optimal starting context* before executing any work. It is:

- **Proactive**, not reactive — it happens before work begins, not when context fills up
- **Constructive**, not reductive — it builds the right context rather than compressing the wrong one
- **Task-specific** — different tasks produce different primed contexts
- **Multi-source** — it synthesizes from memories, codebase, goals, priorities, and external knowledge
- **Goal-aware** — it considers the outcome hierarchy, not just the literal task

### 4.2 The Priming Pipeline

```
Task Received
     │
     ▼
┌─────────────────────────┐
│   1. TASK ANALYSIS       │  Parse user request → identify true intent,
│                          │  immediate task, and likely outcome hierarchy
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   2. SOURCE GATHERING    │  Scan memories, codebase structure, recent
│                          │  git history, flagged priorities, past errors
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   3. RELEVANCE SCORING   │  Score each source against the analyzed task
│                          │  Filter: what matters for THIS specific task?
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   4. SYNTHESIS           │  Compress and interleave relevant sources
│                          │  into a coherent, task-optimized context
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   5. OUTCOME FRAMING     │  Prepend outcome hierarchy:
│                          │  Final goal → Mid-term goal → Immediate task
└──────────┬──────────────┘
           │
           ▼
    Primed Context Ready
    → Agent begins work
```

### 4.3 Source Categories

Context Priming draws from six source categories, each contributing different signal:

| Source | Signal | Example |
|--------|--------|---------|
| **Accumulated Memories** | Past lessons, patterns, mistakes | "This project's API always requires auth headers" |
| **Codebase Structure** | Architecture, conventions, dependencies | Module layout, import patterns, test structure |
| **Flagged Priorities** | What the team/user considers important | "Performance is critical — always benchmark" |
| **Outcome Hierarchy** | The real goal beyond the literal task | Fix test → validate migration → ship v2 |
| **Recent History** | What was recently changed and why | Last 10 commits, recent branches |
| **External Knowledge** | Documentation, research, standards | API docs, framework best practices |

### 4.4 Outcome Hierarchy

A key innovation of Context Priming is explicit outcome awareness. Most agents treat each task atomically — "fix this bug" or "add this feature." But tasks exist in hierarchies:

```
Final Outcome:     Ship the v2 platform by Q2
                        │
Mid-term Goal:     Complete the database migration
                        │
Immediate Task:    Fix the failing migration test
```

An agent that only sees "fix the failing migration test" may apply a narrow patch. An agent that understands the outcome hierarchy will fix the test *in a way that serves the migration*, which serves the v2 launch. This awareness changes the agent's decisions about trade-offs, code quality, test coverage, and error handling.

### 4.5 Cold-Start Priming

A distinctive capability of Context Priming is operating from zero prior context. When encountering an unfamiliar project or domain, the agent can:

1. **Scan the project** — README, package files, directory structure, recent commits
2. **Research externally** — Framework documentation, similar project patterns, best practices
3. **Synthesize a working context** — Even without memories, construct an informed starting point

This transforms the cold-start problem from "the agent knows nothing" to "the agent has done its homework."

### 4.6 Soft Compaction vs. Hard Compaction

We introduce the term **"soft compaction"** to distinguish Context Priming from traditional compaction:

| Dimension | Hard Compaction | Soft Compaction (Context Priming) |
|-----------|----------------|-----------------------------------|
| **When** | Reactive (context full) | Proactive (before task begins) |
| **Direction** | Subtractive (remove/compress) | Constructive (build/synthesize) |
| **Input** | Current context window contents | All available knowledge sources |
| **Output** | Shorter version of existing context | Task-optimized starting context |
| **Task awareness** | None (compresses everything equally) | Full (curates for specific task) |
| **Information loss** | Inevitable (compression is lossy) | Minimal (selects rather than compresses) |

---

## 5. Proposed Architecture

### 5.1 Implementation as a Coding Agent Skill

Context Priming can be implemented as an invocable skill within existing coding agent frameworks. When a user invokes `/prime` (or the agent auto-triggers it), the following process executes:

```
/prime [task description]
         │
         ├─── Read: MEMORY.md + topic memories
         ├─── Read: CLAUDE.md / project instructions
         ├─── Run: git log --oneline -20
         ├─── Run: directory structure scan
         ├─── Read: README.md / package.json
         └─── (Optional) Web: research relevant docs
                   │
                   ▼
         ┌─────────────────┐
         │  SYNTHESIS STEP  │
         │                  │
         │  Filter by task  │
         │  relevance       │
         │  Score memories  │
         │  Rank priorities │
         │  Build hierarchy │
         └────────┬────────┘
                  │
                  ▼
         Output: Primed Context Block
         (injected into conversation)
```

### 5.2 The Primed Context Block

The output of Context Priming is a structured block that becomes the agent's working frame:

```markdown
## Primed Context

### Outcome Hierarchy
- Final: [what this ultimately serves]
- Mid-term: [the milestone this task contributes to]
- Immediate: [the specific task]

### Relevant Project Knowledge
- [synthesized codebase context specific to this task]

### Applicable Lessons
- [filtered memories relevant to this task type]
- [past mistakes to avoid]

### Key Constraints
- [flagged priorities that apply]
- [conventions to follow]

### Working Plan
- [initial approach informed by all of the above]
```

### 5.3 Integration Points

Context Priming can integrate with existing agent architectures at three levels:

1. **Manual invocation** — User calls `/prime` before complex tasks
2. **Auto-trigger** — Hook fires on session start or when task complexity exceeds a threshold
3. **Continuous re-priming** — Agent re-primes when context drifts or task pivots

---

## 6. Comparison with Related Work

| Approach | Proactive | Task-Specific | Multi-Source | Goal-Aware | Cold-Start Capable |
|----------|-----------|---------------|--------------|------------|-------------------|
| Auto-compaction | No | No | No | No | No |
| RAG | Partial | Partial | No | No | Partial |
| MEMORY.md | No | No | No | No | No |
| ContextKit | Yes | Partial | No | Partial | No |
| ACE (ICLR 2026) | Partial | No | Partial | No | No |
| SimpleMem | No | Partial | No | No | No |
| Letta/MemGPT | No | Partial | Partial | No | No |
| **Context Priming** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** |

Context Priming is the first approach to combine all five properties. It is complementary to — not a replacement for — existing memory systems and compaction strategies. ACE can evolve the memories that Context Priming draws from. SimpleMem can compress the memories before priming retrieves them. Auto-compaction can manage the context *after* priming constructs it.

---

## 7. Potential Impact

### 7.1 For Coding Agents

- **Reduced context waste.** Agents start with curated, relevant context rather than accumulating irrelevant exploration artifacts.
- **Fewer mistakes.** Task-relevant lessons are surfaced proactively rather than discovered after the mistake is repeated.
- **Better architectural decisions.** Goal awareness prevents narrow optimizations that conflict with broader objectives.
- **Improved cold starts.** New projects and unfamiliar codebases become immediately productive.

### 7.2 For Developers

- **Less babysitting.** Agents that prime themselves need less manual context-setting from developers.
- **Compound learning.** Memories from past sessions actually influence future sessions at the right moments.
- **Transparency.** The primed context block is visible, auditable, and correctable before work begins.

### 7.3 For the Field

- **New benchmark dimension.** ContextBench and similar benchmarks could add priming quality as a metric.
- **Complementary to scaling.** Larger context windows don't solve the "what goes in them" problem — priming does.
- **Framework-agnostic.** Context Priming can be implemented in any agent framework as a pre-execution step.

---

## 8. Reference Implementation

### 8.1 Architecture Overview

We provide a reference implementation as an open-source Python library (`context-prime`) with a standalone prototype and platform adapters. The architecture separates the model-agnostic priming engine from platform-specific injection mechanisms.

```
context-prime (pip install context-prime)
│
├── Core Engine (model-agnostic)
│   ├── gather    — Scan memories, codebase, git history, project config
│   ├── score     — LLM-based relevance scoring against the task
│   ├── hierarchy — Outcome hierarchy inference
│   └── synthesize — Compress and merge into primed context block
│
├── Adapters (platform-specific injection)
│   ├── Claude Agent SDK  — Full context control, subagent priming
│   ├── Claude Code Hooks — SessionStart / UserPromptSubmit injection
│   ├── Raw API           — Any Chat Completions-style API
│   └── (Extensible to OpenCode, Gemini CLI, Codex CLI)
│
└── CLI
    └── context-prime prime --task "..." --project ./myapp
```

### 8.2 The Priming Pipeline in Practice

The implementation executes four sequential LLM calls using a fast model (e.g., Sonnet) to minimize overhead:

1. **Gather** (no LLM, ~100ms) — File system scan of memories, codebase structure, git history, and project configuration. Produces a list of `Source` objects with category, name, content, and token estimates.

2. **Score** (1 LLM call, ~2s) — Each source receives a relevance score (0.0–1.0) against the specific task. Sources below the threshold are filtered. A token budget prevents the primed context from exceeding a configurable limit.

3. **Hierarchy** (1 LLM call, ~2s) — The task is analyzed in the context of the project to infer the outcome hierarchy: immediate task, mid-term goal, and final outcome. The model reports its confidence level and avoids fabricating goals when evidence is insufficient.

4. **Synthesize** (1 LLM call, ~3s) — Relevant sources and the outcome hierarchy are merged into a single, dense briefing document (1500–3000 tokens). The LLM synthesizes rather than concatenates — overlapping information is merged, and every sentence carries task-specific signal.

Total priming overhead: approximately 5–10 seconds. The resulting primed context then serves as the system prompt for the execution agent.

### 8.3 Platform Integration

**Claude Agent SDK (recommended for production).** The Agent SDK provides full programmatic control over the context window. The priming engine constructs the system prompt and initial messages before the agent begins work. Each task gets a fresh context containing only the synthesized primed content.

```python
from context_prime.adapters.claude_sdk import run_primed_agent

await run_primed_agent(
    task="Fix the auth middleware bug",
    project_dir="./myapp",
    agent_model="claude-opus-4-6",
    priming_model="claude-sonnet-4-6",
)
```

**Claude Code Hooks (for existing Claude Code users).** A `SessionStart` hook provides session-level priming at launch (when context is empty). A `UserPromptSubmit` hook provides per-task priming by analyzing each user message and injecting relevant context via `additionalContext`. Hooks cannot replace context — they are additive only. This limits their use to injecting primed context on top of existing conversation state.

**Raw API (model-agnostic).** The `raw_api` adapter returns the primed context as a structured dict compatible with any Chat Completions-style API (Anthropic, OpenAI, Google). This enables integration with any coding agent framework or custom application.

### 8.4 Cross-Platform Potential

The core priming engine is deliberately model-agnostic. The `llm_call` parameter accepts any callable that takes a prompt string and returns a response string. This enables integration with:

- **OpenCode** — As a custom agent definition. OpenCode's agent system supports custom prompts and tool access, making it a natural fit for priming integration.
- **Gemini CLI** — Via `before_model_call` hooks, which can modify prompts and inject context before the model processes a request.
- **Codex CLI** — Via MCP servers that run the priming pipeline and return context when queried by the agent.
- **Any future agent** — The library's adapter interface is intentionally minimal: implement `inject(primed_context, task)` for any platform.

### 8.5 Prototype Results

The prototype demonstrates the full pipeline on a sample Express.js project with accumulated memory files. Given the task "Fix the auth middleware bug":

- **Gathered:** 12 sources (~8,000 tokens) from memories, codebase, and git history
- **Scored:** 5 sources kept (relevance > 0.5), 7 filtered out
- **Hierarchy inferred:** Immediate → fix auth bug; Mid-term → harden middleware layer; Final → ship v2
- **Synthesized:** 2,100-token briefing including the specific past lesson about token expiry edge cases, the project convention of httpOnly cookies, and the relevant file paths
- **Priming overhead:** ~7 seconds using Sonnet for the three LLM calls

The resulting primed context surfaces the exact past mistake ("Always validate both `exp` AND `iat` claims") that is directly relevant to the task — a lesson that would otherwise remain buried in a 500-line memory file.

---

## 9. Limitations and Future Work

### 8.1 Current Limitations

- **Priming overhead.** The synthesis step consumes tokens and time before any "real" work begins. For simple tasks, this overhead may not be justified.
- **Quality dependency.** Priming quality depends on the quality of available memories and codebase documentation. Garbage in, curated garbage out.
- **Outcome hierarchy accuracy.** Inferring the correct outcome hierarchy from a task description is itself an LLM inference challenge that may introduce errors.

### 8.2 Future Directions

- **Adaptive priming depth.** Automatically calibrate priming thoroughness based on task complexity — simple tasks get light priming, complex tasks get deep synthesis.
- **Collaborative priming.** In multi-agent systems, agents could share and merge primed contexts.
- **Priming evaluation metrics.** Develop benchmarks that measure priming quality: relevance of surfaced memories, accuracy of outcome hierarchy, and downstream task performance.
- **Continuous priming.** Extend beyond pre-task priming to mid-task re-priming when the agent detects context drift.

---

## 10. Conclusion

The coding agent ecosystem has converged on a clear insight: context quality determines agent quality. Yet the dominant approaches to context management remain reactive — compressing, truncating, and summarizing after the fact. Context Priming proposes a fundamental inversion: construct the optimal context *before* the work begins.

By synthesizing from memories, codebase knowledge, priorities, and an explicit outcome hierarchy, Context Priming transforms the agent's starting conditions from a blank page (or a bloated one) into a curated, task-specific briefing. This is not compaction — it is preparation. Not subtraction — but construction. Not reactive — but proactive.

The building blocks exist. Memory systems, codebase indexing, planning frameworks, and context compression are all mature. What's missing is the orchestration layer that synthesizes them into a single, task-optimized starting context. Context Priming is that layer.

---

## References

1. Anthropic. (2025). "Effective Context Engineering for AI Agents." https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

2. JetBrains Research. (2025). "Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents." https://blog.jetbrains.com/research/2025/12/efficient-context-management/

3. Zhu, Q. et al. (2025). "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models." ICLR 2026. https://arxiv.org/abs/2510.04618

4. aiming-lab. (2025). "SimpleMem: Efficient Lifelong Memory for LLM Agents." https://arxiv.org/abs/2601.02553

5. ContextBench. (2026). "A Benchmark for Context Retrieval in Coding Agents." https://arxiv.org/abs/2602.05892

6. Letta AI. (2025). "Agent Memory: How to Build Agents that Learn and Remember." https://www.letta.com/blog/agent-memory

7. CAMEL-AI. (2025). "Brainwash Your Agent: How We Keep The Memory Clean." https://www.camel-ai.org/blogs/brainwash-your-agent-how-we-keep-the-memory-clean

8. Osmani, A. (2025). "My LLM Coding Workflow Going Into 2026." https://medium.com/@addyosmani/my-llm-coding-workflow-going-into-2026-52fe1681325e

9. Fowler, M. (2025). "Context Engineering for Coding Agents." https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html

10. GitHub. (2025). "How to Build Reliable AI Workflows with Agentic Primitives and Context Engineering." https://github.blog/ai-and-ml/github-copilot/how-to-build-reliable-ai-workflows-with-agentic-primitives-and-context-engineering/

11. FlineDev. (2026). "ContextKit: Claude Code Context Engineering & Planning System." https://github.com/FlineDev/ContextKit

12. Voltropy. (2026). "Lossless Context Management for AI Agents."

13. Supermemory. (2025). "Infinitely Running Stateful Coding Agents." https://blog.supermemory.ai/infinitely-running-stateful-coding-agents/

14. Lethain, W. (2025). "Building an Internal Agent: Context Window Compaction." https://lethain.com/agents-context-compaction/

15. Anthropic. (2026). "Claude Agent SDK." https://platform.claude.com/docs/en/agent-sdk/overview

16. OpenCode. (2026). "The Open Source AI Coding Agent." https://github.com/opencode-ai/opencode

17. Google. (2026). "Gemini CLI Hooks." https://developers.googleblog.com/tailor-gemini-cli-to-your-workflow-with-hooks/

18. 199 Biotechnologies. (2026). "Context Prime — Reference Implementation." https://github.com/199-biotechnologies/context-priming

---

*199 Biotechnologies — February 2026*
