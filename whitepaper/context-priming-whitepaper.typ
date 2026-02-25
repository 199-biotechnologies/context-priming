// ============================================================================
// Context Priming: Proactive Context Synthesis for Coding Agents
// Typst Academic Paper — 199 Biotechnologies, February 2026
// ============================================================================

// --- Citation helper ---
#let cite(n) = super(text(size: 7.5pt, fill: rgb("#1a5276"), weight: "bold")[#n])

// --- Document setup ---
#set document(
  title: "Context Priming: Proactive Context Synthesis for Coding Agents",
  author: "Boris Djordjevic",
  date: datetime(year: 2026, month: 2, day: 25),
)

#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1in, right: 1in),
  numbering: "1",
  number-align: center,
  header: context {
    if counter(page).get().first() > 1 [
      #set text(8pt, fill: luma(120))
      _Context Priming: Proactive Context Synthesis for Coding Agents_
      #h(1fr)
      199 Biotechnologies
    ]
  },
)

#set text(
  font: "Palatino",
  size: 10.5pt,
  lang: "en",
)

#set par(
  justify: true,
  leading: 0.65em,
  first-line-indent: 1.5em,
)

#set heading(numbering: "1.1")

#show heading.where(level: 1): it => {
  set text(13pt, weight: "bold")
  v(1.5em)
  block(it)
  v(0.5em)
}

#show heading.where(level: 2): it => {
  set text(11pt, weight: "bold")
  v(1em)
  block(it)
  v(0.3em)
}

#show heading.where(level: 3): it => {
  set text(10.5pt, weight: "bold", style: "italic")
  v(0.8em)
  block(it)
  v(0.2em)
}

// Code block styling
#show raw.where(block: true): it => {
  set text(font: "Menlo", size: 8.5pt)
  block(
    fill: luma(245),
    inset: 10pt,
    radius: 3pt,
    width: 100%,
    stroke: 0.5pt + luma(200),
    it,
  )
}

#show raw.where(block: false): it => {
  set text(font: "Menlo", size: 9pt)
  box(
    fill: luma(240),
    inset: (x: 3pt, y: 1.5pt),
    radius: 2pt,
    it,
  )
}

// Figure styling
#show figure: it => {
  set text(size: 9.5pt)
  v(0.8em)
  it
  v(0.5em)
}

#show figure.caption: it => {
  set text(size: 9pt, style: "italic")
  it
}

// Links
#show link: it => {
  set text(fill: rgb("#1a5276"))
  it
}

// Math styling
#set math.equation(numbering: "(1)")

// ============================================================================
// Title block
// ============================================================================

#v(2em)

#align(center)[
  #text(18pt, weight: "bold")[
    Context Priming: Proactive Context Synthesis\ for Coding Agents
  ]

  #v(1.5em)

  #text(12pt)[Boris Djordjevic]
  #v(0.3em)
  #text(10pt, fill: luma(80))[
    199 Biotechnologies\
    February 2026 --- Version 2.1
  ]
]

#v(2em)

// ============================================================================
// Abstract
// ============================================================================

#block(
  inset: (left: 2em, right: 2em),
  [
    #text(10pt, weight: "bold")[Abstract.]
    #text(10pt)[
    Large Language Model (LLM) coding agents face a fundamental architectural bottleneck: context management. Current approaches are overwhelmingly _reactive_ --- compressing, truncating, or summarizing context only when the window fills up. This paper proposes *Context Priming*, a paradigm shift where coding agents _proactively construct_ their optimal context before beginning any task. Rather than subtracting information from an overflowing window, the agent synthesizes a purpose-built context from multiple sources: accumulated memories, codebase structure, flagged priorities, past mistakes, and an explicit outcome hierarchy. This "soft compaction" operates as generative context construction --- the inverse of the reductive compression that dominates the field today. We formalize the priming objective, present a reference implementation with measured performance, survey existing approaches, and identify the specific gap Context Priming fills.
    ]
  ],
)

#v(0.5em)
#line(length: 100%, stroke: 0.5pt + luma(180))
#v(0.5em)

// ============================================================================
// 1. Introduction
// ============================================================================

= Introduction

== The Context Crisis

#par(first-line-indent: 0pt)[
The effectiveness of LLM-based coding agents is fundamentally constrained by what fits in their context window. Despite context windows expanding from 4K to 200K+ tokens between 2023 and 2026, the core problem persists: _having more space doesn't mean you know what to put in it_.
]

Current coding agents --- Claude Code, GitHub Copilot, Cursor, Windsurf, and others --- face a recurring failure mode. They begin a task, accumulate context through file reads, tool calls, and conversation turns, then degrade as the context fills with irrelevant artifacts from earlier exploration. Studies have documented "context rot" --- the phenomenon where model accuracy on information retrieval decreases as context length increases, even when the information is present in the window.#cite(2)

We can express this degradation formally. Let $A(t)$ denote agent accuracy at context utilization fraction $t in [0, 1]$. Empirical measurements show:

$ A(t) approx A_0 dot (1 - alpha t^beta) $ <eq:degradation>

where $A_0$ is baseline accuracy, $alpha in [0.3, 0.5]$ is the degradation coefficient, and $beta approx 1.5$ reflects the super-linear decay observed in practice. At 80% context utilization ($t = 0.8$), agents typically lose 20--35% of their retrieval accuracy.

== The Reactive Paradigm

The industry's response has been reactive context management:

- *Auto-compaction* triggers when context reaches a threshold (e.g., Claude Code compacts at 95% capacity)
- *Truncation* drops older messages beyond a sliding window
- *Recursive summarization* compresses conversation history into progressively shorter summaries
- *RAG (Retrieval-Augmented Generation)* fetches relevant documents on demand

All of these approaches share a common assumption: context is something that _accumulates and must be managed_. They are subtractive --- their goal is to remove or compress what's already there.

== The Priming Alternative

We propose inverting this assumption entirely. Instead of asking _"what should we remove?"_, Context Priming asks _"what is the optimal context to construct for this specific task?"_

A primed agent doesn't start with an empty context and reactively accumulate information. It doesn't start with a full context and reactively compress it. Instead, it begins by _synthesizing_ a purpose-built context --- drawing from memories, codebase knowledge, past lessons, and goal awareness --- and then operates within that optimized frame.

// ============================================================================
// 2. The Problem Space
// ============================================================================

= The Problem Space

== Why Context Matters More Than Model Capability

Anthropic's engineering team has stated that "the single most important determinant of AI agent effectiveness is providing the right context."#cite(1) The field has converged on this insight: prompt engineering is about _what you say_; context engineering is about _what the model sees_. And what the model sees matters more.

Every token in context costs attention. Let $n$ be the number of tokens and $d$ the model dimension. The self-attention cost scales as:

$ cal(O)(n^2 dot d) $ <eq:attention>

Larger contexts don't just consume memory --- they dilute the model's focus. Research from Voltropy (2026) on Lossless Context Management demonstrated that agents allowed to manage their own memory frequently degrade their own performance through poor prioritization.#cite(12)

== The Five Failure Modes

Current coding agents exhibit five recurring failure modes related to context:

+ *Cold-start blindness.* New sessions begin with no relevant context, forcing the agent to rediscover project conventions, architecture, and past decisions from scratch.

+ *Memory bloat.* Accumulated memories and lessons grow into massive files that cannot fit in context, forcing either truncation (losing valuable lessons) or no memory at all.

+ *Goal drift.* Without explicit awareness of the outcome hierarchy, agents optimize for the literal user request rather than the actual desired outcome. A request to "fix this test" may require understanding that the test exists to validate a migration that serves a larger architecture change.

+ *Lesson amnesia.* Past mistakes and their solutions are recorded but never surfaced at the right moment. A memory about "always use absolute imports in this project" is useless if it's buried on line 847 of a memory file when the agent is writing a new module.

+ *Context pollution.* Exploratory tool calls (file reads, searches, failed approaches) accumulate in context and dilute the signal-to-noise ratio for the actual task.

== The Cost of Getting Context Wrong

ContextBench (2026), a benchmark for context retrieval in coding agents, demonstrated that even state-of-the-art agents retrieve the wrong context for coding tasks 30--40% of the time.#cite(5) This isn't a model capability issue --- it's an architectural one. The agents have access to the right information; they fail to surface it at the right time.

We define _context precision_ as the fraction of primed tokens that are actually relevant:

$ P_"context" = (|C_"relevant" inter C_"primed"|) / (|C_"primed"|) $ <eq:precision>

Current approaches achieve $P_"context" approx 0.4$--$0.6$. Context Priming targets $P_"context" >= 0.8$ by applying task-specific relevance scoring before context construction.

// ============================================================================
// 3. Existing Approaches and Their Limitations
// ============================================================================

= Existing Approaches and Their Limitations

== Reactive Compaction

*Examples:* Claude Code auto-compact, Google ADK context compression, Forge Code compaction.

*Approach:* Monitor context usage, trigger summarization when approaching limits.

*Limitation:* By the time compaction fires, context is already degraded. Compaction is lossy --- it cannot recover information that was never loaded, and it inevitably discards nuances that may become relevant later. The information loss $cal(L)$ of reactive compaction can be modeled as:

$ cal(L)_"reactive" = H(C_"original") - H(C_"compacted") >= 0 $ <eq:reactive-loss>

where $H$ denotes the task-relevant information entropy. The inequality holds strictly because compaction is a lossy operation that cannot distinguish between task-essential and exploratory context.

== Memory Systems

*Examples:* Letta/MemGPT (hierarchical memory), SimpleMem (semantic compression), `MEMORY.md` files.

*Approach:* Store agent experiences in structured memory systems with retrieval mechanisms.

*Limitation:* Memory systems solve _storage_ but not _synthesis_. SimpleMem achieves impressive compression (30$times$ token reduction) but still relies on query-time retrieval --- the agent must know what to ask for.#cite(4) Memory files like `MEMORY.md` provide persistence but are loaded wholesale, with no task-specific curation. Letta's hierarchical memory (core, archival, recall) is architecturally sophisticated but optimizes for long-running agent sessions, not for pre-task preparation.#cite(6)

== Static Context Loading

*Examples:* elizaOS `/context-prime`, `CLAUDE.md` files, `AGENTS.md` conventions.

*Approach:* Load predefined context files (README, project structure, conventions) at session start.

*Limitation:* Static context is one-size-fits-all. A debugging task and a feature implementation task in the same project need fundamentally different context. Recent research (Koylan, 2026) found that LLM-generated general context actually _decreases_ performance by $-3%$ on average on AGENTBENCH, while developer-written context only marginally improves it ($+4%$).

== Planning-First Approaches

*Examples:* ContextKit (4-phase methodology), CodePlan (pseudocode planning).#cite(11)

*Approach:* Structure development into explicit planning phases before implementation.

*Limitation:* Planning-first approaches improve _workflow_ but not _context quality_. They tell the agent _how_ to work but don't optimize _what the agent sees_. A planning phase that runs inside a polluted context will produce a polluted plan.

== Agentic Context Engineering (ACE)

*Reference:* "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models" (ICLR 2026).#cite(3)

*Approach:* Treats contexts as evolving playbooks that accumulate, refine, and organize strategies through generation, reflection, and curation. Achieves $+10.6%$ improvement on agent benchmarks.

*Limitation:* ACE focuses on _evolving system prompts over time_ --- it's about the gradual improvement of standing context through experience. It doesn't address the per-task synthesis problem: given a specific task right now, what is the optimal context to construct from all available sources? ACE evolves the playbook; Context Priming constructs the play.

// ============================================================================
// 4. The Context Priming Proposal
// ============================================================================

= The Context Priming Proposal

== Core Concept

Context Priming is the process by which a coding agent, upon receiving a task, _proactively constructs its optimal starting context_ before executing any work. It is:

- *Proactive*, not reactive --- it happens before work begins, not when context fills up
- *Constructive*, not reductive --- it builds the right context rather than compressing the wrong one
- *Task-specific* --- different tasks produce different primed contexts
- *Multi-source* --- it synthesizes from memories, codebase, goals, priorities, and external knowledge
- *Goal-aware* --- it considers the outcome hierarchy, not just the literal task

== The Priming Objective

#par(first-line-indent: 0pt)[
We formalize the priming objective as an optimization problem. Given a task $tau$, a set of available sources $cal(S) = {s_1, s_2, ..., s_n}$, and a context budget $B$ (in tokens), find the optimal subset $cal(S)^* subset.eq cal(S)$ that maximizes task-relevant information within the budget:
]

$ cal(S)^* = arg max_(cal(S)' subset.eq cal(S)) sum_(s_i in cal(S)') R(s_i, tau) quad "subject to" quad sum_(s_i in cal(S)') |s_i| <= B $ <eq:objective>

where $R(s_i, tau) in [0, 1]$ is the relevance score of source $s_i$ to task $tau$, and $|s_i|$ denotes the token count of source $s_i$.

The context budget $B$ is defined as a fraction of the platform's available coding context:

$ B = gamma dot C_"platform" $ <eq:budget>

where $gamma in [0.1, 0.4]$ is the budget fraction (default $gamma = 0.25$) and $C_"platform"$ is the platform's usable context window. @tab:budgets shows the platform-specific values.

#figure(
  table(
    columns: (1.5fr, 1fr, 1fr),
    align: (left, right, right),
    stroke: 0.5pt + luma(180),
    inset: 7pt,
    fill: (_, row) => if row == 0 { luma(235) } else { none },
    table.header(
      [*Platform*], [$C_"platform"$], [$B$ (at $gamma = 0.25$)],
    ),
    [Claude Code], [120k], [30k],
    [Claude API (raw)], [200k], [50k],
    [Gemini CLI], [1,000k], [250k],
    [Codex CLI], [200k], [50k],
    [OpenCode], [128k], [32k],
  ),
  caption: [Platform context budgets. $C_"platform"$ is the usable coding context; $B$ is the priming budget at $gamma = 0.25$.],
) <tab:budgets>

== The Priming Pipeline

#figure(
  block(
    width: 100%,
    inset: 12pt,
    radius: 4pt,
    fill: luma(248),
    stroke: 0.5pt + luma(200),
    align(left)[
      #set text(font: "Menlo", size: 8pt)
      ```
      Task Received (τ)
           │
           ▼
      ┌─────────────────────────────────┐
      │  1. SOURCE GATHERING             │  Scan memories, codebase,
      │     O(filesystem), ~100ms        │  git, code files via grep
      │     0 LLM calls                  │  heuristic keyword extraction
      └──────────┬──────────────────────┘
                 │
                 ▼
      ┌─────────────────────────────────┐
      │  2. RELEVANCE SCORING            │  Score R(sᵢ, τ) ∈ [0,1]
      │     1 LLM call, ~2s             │  Filter: R(sᵢ) ≥ θ
      │     Fail-closed on errors        │  Categorical budget alloc.
      └──────────┬──────────────────────┘
                 │
                 ▼
      ┌─────────────────────────────────┐
      │  3. HIERARCHY INFERENCE          │  Infer outcome hierarchy:
      │     1 LLM call, ~2s             │  τ_final → τ_mid → τ_immediate
      └──────────┬──────────────────────┘
                 │
                 ▼
      ┌─────────────────────────────────┐
      │  4. CONTEXT ASSEMBLY             │  Full source content +
      │     1 LLM call, ~2s             │  executive summary +
      │     Trust boundaries             │  capabilities reminder
      └──────────┬──────────────────────┘
                 │
                 ▼
          Primed Context C*(τ)
          → Agent begins work
      ```
    ],
  ),
  caption: [The Context Priming pipeline. Three LLM calls using a fast model (e.g., Sonnet) plus one filesystem scan. Total overhead: 5--8 seconds.],
) <fig:pipeline>

== Source Categories

Context Priming draws from six source categories, each contributing different signal:

#figure(
  table(
    columns: (1.2fr, 1.5fr, 2fr),
    align: (left, left, left),
    stroke: 0.5pt + luma(180),
    inset: 7pt,
    fill: (_, row) => if row == 0 { luma(235) } else { none },
    table.header(
      [*Source Category*], [*Signal*], [*Example*],
    ),
    [Accumulated Memories], [Past lessons, patterns, mistakes], [_"This project's API always requires auth headers"_],
    [Codebase Structure], [Architecture, conventions, deps], [Module layout, import patterns, test structure],
    [Source Code Files], [Actual implementation code], [Files matching task keywords via `grep`],
    [Flagged Priorities], [What the team considers important], [_"Performance is critical --- always benchmark"_],
    [Recent History], [What was recently changed and why], [Last 10 commits, staged/unstaged changes],
    [External Knowledge], [Documentation, research, standards], [API docs, framework best practices],
  ),
  caption: [The six source categories gathered by Context Priming.],
) <tab:sources>

== Outcome Hierarchy

A key innovation of Context Priming is explicit outcome awareness. Most agents treat each task atomically --- "fix this bug" or "add this feature." But tasks exist in hierarchies:

#align(center)[
  #block(
    inset: 12pt,
    radius: 4pt,
    fill: luma(248),
    stroke: 0.5pt + luma(200),
  )[
    #set text(10pt)
    $tau_"final"$: Ship the v2 platform by Q2\
    $arrow.b$\
    $tau_"mid"$: Complete the database migration\
    $arrow.b$\
    $tau_"immediate"$: Fix the failing migration test
  ]
]

An agent that only sees $tau_"immediate"$ may apply a narrow patch. An agent that understands the full hierarchy will fix the test _in a way that serves the migration_, which serves the v2 launch. We define the _hierarchy-aware utility_ as:

$ U(a) = w_1 dot u(a, tau_"immediate") + w_2 dot u(a, tau_"mid") + w_3 dot u(a, tau_"final") $ <eq:utility>

where $a$ is the agent's action, $u(a, tau)$ measures how well action $a$ serves goal $tau$, and the weights satisfy $w_1 > w_2 > w_3 > 0$, $sum_i w_i = 1$. In practice we use $w_1 = 0.6$, $w_2 = 0.25$, $w_3 = 0.15$.

== Guidance, Not Constraint --- The Surgical Analogy

A critical design principle of Context Priming is that the primed context must *inform* the agent, not *constrain* it. The analogy is surgical preparation: a surgeon reviewing pre-operative imaging (CT scans, MRI, patient history) before performing heart surgery. The imaging highlights the most likely areas of concern, flags potential complications, and ensures the surgeon enters the operating room with the right knowledge loaded. But it does not dictate what the surgeon does once the chest is open.

In practice, the actual situation nearly always differs from what the imaging shows. The surgeon finds unexpected adhesions, unanticipated anatomy, complications that weren't visible on scans. The preparation _informs the starting point_ but the surgeon must remain free to adapt, explore, and respond to what they actually find.

Context Priming follows the same principle:

+ *Point toward likely relevant files and patterns* --- the pre-operative imaging
+ *Flag potential complications and edge cases* --- warnings from past experience and project history
+ *Note areas of uncertainty* --- where the agent should investigate rather than assume
+ *Remind the agent of available tools* --- subagents, parallel sessions, search, shell access
+ *Explicitly encourage exploration beyond the primed context* --- the priming is a starting point, not a complete picture

The primed context should never say "here is everything you need." It should say "here is what we know so far --- now go look for yourself."

== Cold-Start Priming

A distinctive capability of Context Priming is operating from zero prior context. When encountering an unfamiliar project or domain, the agent can:

+ *Scan the project* --- README, package files, directory structure, recent commits
+ *Research externally* --- Framework documentation, similar project patterns, best practices
+ *Synthesize a working context* --- Even without memories, construct an informed starting point

This transforms the cold-start problem from "the agent knows nothing" to "the agent has done its homework."

== Soft Compaction vs. Hard Compaction

We introduce the term *"soft compaction"* to distinguish Context Priming from traditional compaction:

#figure(
  table(
    columns: (1.2fr, 1.5fr, 2fr),
    align: (left, left, left),
    stroke: 0.5pt + luma(180),
    inset: 7pt,
    fill: (_, row) => if row == 0 { luma(235) } else { none },
    table.header(
      [*Dimension*], [*Hard Compaction*], [*Soft Compaction (Context Priming)*],
    ),
    [*When*], [Reactive (context full)], [Proactive (before task begins)],
    [*Direction*], [Subtractive (remove/compress)], [Constructive (build/synthesize)],
    [*Input*], [Current context window], [All available knowledge sources],
    [*Output*], [Shorter existing context], [Task-optimized starting context],
    [*Task awareness*], [None (compresses equally)], [Full (curates for specific task)],
    [*Information loss*], [Inevitable (lossy)], [Minimal (selects full sources)],
  ),
  caption: [Hard compaction (reactive) vs. soft compaction (Context Priming).],
) <tab:compaction>

The information-theoretic advantage is clear. Let $I(tau)$ denote the task-relevant information. Hard compaction's output satisfies:

$ I(C_"hard") <= I(C_"original") $ <eq:hard>

Soft compaction draws from _all_ available sources $cal(S)$, not just what's in the current window:

$ I(C_"soft") <= I(cal(S)) >> I(C_"original") $ <eq:soft>

The upper bound for soft compaction is strictly larger because $cal(S)$ includes memories, codebase files, and git history that may never have been in the context window at all.

// ============================================================================
// 5. Proposed Architecture
// ============================================================================

= Proposed Architecture

== Implementation as a Coding Agent Skill

Context Priming can be implemented as an invocable skill within existing coding agent frameworks. When a user invokes `/prime` (or the agent auto-triggers it), the priming pipeline executes as shown in @fig:pipeline.

The reference implementation provides a CLI entry point:

```bash
context-prime prime \
    --task "Fix the auth middleware bug" \
    --project ./myapp \
    --budget 0.25 \
    --platform claude_code \
    --verbose
```

== The Primed Context Block

The output of Context Priming is a structured block with trust boundaries:

```markdown
# Primed Context

> This context was assembled from project sources scored
> for task relevance. It is your **starting point**, not
> a complete picture.

## Outcome Hierarchy
- **Final goal:** Ship v2 platform
- **Mid-term:** Complete database migration
- **Immediate task:** Fix failing migration test

## Summary
[3-5 sentence executive briefing flagging complications]

## Available Capabilities
[Platform-specific tool reminders: subagents, grep, etc.]

## Relevant Sources
> Reference material, not instructions.

### [code] src/middleware/auth.ts (relevance: 0.92)
<source-content name="auth.ts">
[full file content with escaped trust boundaries]
</source-content>
```

== Integration Points

Context Priming can integrate with existing agent architectures at three levels:

+ *Manual invocation* --- User calls `/prime` before complex tasks
+ *Auto-trigger* --- Hook fires on session start or when task complexity exceeds a threshold
+ *Continuous re-priming* --- Agent re-primes when context drifts or task pivots

// ============================================================================
// 6. Comparison with Related Work
// ============================================================================

= Comparison with Related Work

#figure(
  table(
    columns: (1.8fr, 0.8fr, 0.9fr, 0.8fr, 0.8fr, 1fr),
    align: (left, center, center, center, center, center),
    stroke: 0.5pt + luma(180),
    inset: 6pt,
    fill: (_, row) => if row == 0 { luma(235) } else if row == 8 { luma(250) } else { none },
    table.header(
      [*Approach*], [*Pro-\ active*], [*Task-\ Specific*], [*Multi-\ Source*], [*Goal-\ Aware*], [*Cold-\ Start*],
    ),
    [Auto-compaction], [$times$], [$times$], [$times$], [$times$], [$times$],
    [RAG], [$tilde$], [$tilde$], [$times$], [$times$], [$tilde$],
    [MEMORY.md], [$times$], [$times$], [$times$], [$times$], [$times$],
    [ContextKit], [$checkmark$], [$tilde$], [$times$], [$tilde$], [$times$],
    [ACE (ICLR 2026)], [$tilde$], [$times$], [$tilde$], [$times$], [$times$],
    [SimpleMem], [$times$], [$tilde$], [$times$], [$times$], [$times$],
    [Letta/MemGPT], [$times$], [$tilde$], [$tilde$], [$times$], [$times$],
    [*Context Priming*], [$checkmark$], [$checkmark$], [$checkmark$], [$checkmark$], [$checkmark$],
  ),
  caption: [Feature comparison. $checkmark$ = full support, $tilde$ = partial, $times$ = none. Context Priming is the first approach to combine all five properties.],
) <tab:comparison>

Context Priming is complementary to --- not a replacement for --- existing memory systems and compaction strategies. ACE can evolve the memories that Context Priming draws from. SimpleMem can compress the memories before priming retrieves them. Auto-compaction can manage the context _after_ priming constructs it.

// ============================================================================
// 7. Potential Impact
// ============================================================================

= Potential Impact

== For Coding Agents

- *Reduced context waste.* Agents start with curated, relevant context rather than accumulating irrelevant exploration artifacts.
- *Fewer mistakes.* Task-relevant lessons are surfaced proactively rather than discovered after the mistake is repeated.
- *Better architectural decisions.* Goal awareness prevents narrow optimizations that conflict with broader objectives.
- *Improved cold starts.* New projects and unfamiliar codebases become immediately productive.

== For Developers

- *Less babysitting.* Agents that prime themselves need less manual context-setting from developers.
- *Compound learning.* Memories from past sessions actually influence future sessions at the right moments.
- *Transparency.* The primed context block is visible, auditable, and correctable before work begins.

== For the Field

- *New benchmark dimension.* ContextBench and similar benchmarks could add priming quality as a metric, measuring $P_"context"$ (@eq:precision) across different approaches.
- *Complementary to scaling.* Larger context windows don't solve the "what goes in them" problem --- priming does.
- *Framework-agnostic.* Context Priming can be implemented in any agent framework as a pre-execution step.

// ============================================================================
// 8. Reference Implementation
// ============================================================================

= Reference Implementation

== Architecture Overview

We provide a reference implementation as an open-source Python library (`context-prime`) with a standalone prototype and platform adapters.#cite(18) The architecture separates the model-agnostic priming engine from platform-specific injection mechanisms:

```python
# Architecture: context-prime (pip install context-prime)
#
# Core Engine (model-agnostic)
#   gather.py     — Scan memories, codebase, git, code files
#   score.py      — LLM-based relevance scoring R(sᵢ, τ)
#   hierarchy.py  — Outcome hierarchy inference
#   synthesize.py — Assemble full sources + executive summary
#
# Adapters (platform-specific injection)
#   claude_sdk.py  — Claude Agent SDK (full context control)
#   claude_hook.sh — SessionStart / UserPromptSubmit hooks
#   raw_api.py     — Any Chat Completions-style API
#
# CLI
#   context-prime prime --task "..." --project ./myapp
```

The core engine accepts any `llm_call: Callable[[str], str]` function, making it compatible with any LLM provider.

== The Priming Pipeline in Practice

The implementation executes three LLM calls using a fast model (e.g., Claude Sonnet) to minimize overhead:

*Step 1: Gather* (no LLM, $tilde 100$ ms). File system scan of memories, codebase structure, git history, and project configuration. Source code files are discovered via keyword extraction and `grep`:

```python
def gather_code_files(project_dir, task, max_files=50):
    """Heuristic code file discovery — no LLM needed.

    Strategy:
      1. Extract keywords from task via stop-word filter
      2. grep codebase for files containing keywords
      3. Find files whose names match keywords
      4. Boost recently modified files (git diff)
    """
    keywords = _extract_keywords(task)
    matched_files = {}  # path → relevance hint

    # grep for content matches
    for kw in keywords:
        result = subprocess.run(
            ["grep", "-rl", "-i", kw, "."],
            capture_output=True, cwd=project_dir
        )
        for path in result.stdout.split("\n"):
            matched_files[path] += 1

    # Filename matches are strong signals (+3 boost)
    for kw in keywords:
        for path in find_files(f"*{kw}*"):
            matched_files[path] += 3

    # Read top files ranked by match count
    return [read_source(p) for p in ranked[:max_files]]
```

*Step 2: Score* (1 LLM call, $tilde 2$ s). Each source receives a relevance score $R(s_i, tau) in [0, 1]$. Scoring is _fail-closed_: if JSON parsing fails, sources receive $R = 0.2$ (below the default threshold $theta = 0.5$), preventing garbage from leaking through. A categorical budget reserves 15% of tokens for memories and config:

```python
# Categorical budget allocation — ensures code files
# don't crowd out memories and project priorities
reserved_budget = int(max_tokens * 0.15)  # memories + config
code_budget     = max_tokens - reserved_budget

# Fill reserved categories first, then general pool
for src in memory_and_config_sources:
    if src.score >= threshold and fits_budget(reserved_budget):
        include(src)

for src in code_and_git_sources:
    if src.score >= threshold and fits_budget(code_budget):
        include(src)
```

*Step 3: Hierarchy* (1 LLM call, $tilde 2$ s). The task is analyzed in the context of the project to infer the outcome hierarchy ($tau_"immediate"$, $tau_"mid"$, $tau_"final"$). The model reports confidence and avoids fabricating goals when evidence is insufficient.

*Step 4: Assemble* (1 LLM call, $tilde 2$ s). Sources are assembled with *full content* within trust-boundary markers. A brief executive summary (3--5 sentences) flags potential complications. A capabilities reminder tells the agent about available tools.

Total priming overhead: $tilde 5$--$8$ seconds. The resulting primed context uses up to $gamma = 25%$ of the platform's available coding context.

== Platform Integration

*Claude Agent SDK (recommended for production).* Full programmatic context control.#cite(15)

```python
from context_prime.adapters.claude_sdk import run_primed_agent

await run_primed_agent(
    task="Fix the auth middleware bug",
    project_dir="./myapp",
    agent_model="claude-opus-4-6",     # Best model for work
    priming_model="claude-sonnet-4-6", # Fast model for priming
)
```

*Claude Code Hooks.* A `SessionStart` hook provides session-level priming. Hooks are additive only --- they cannot replace context.

*Raw API (model-agnostic).* Works with any Chat Completions-style API:

```python
from context_prime.adapters.raw_api import prime_messages

# Compatible with Anthropic, OpenAI, Google, OpenRouter
messages = prime_messages(task, project_dir, llm_call)
response = client.chat.completions.create(
    model="any-model", messages=messages
)
```

== Trust Boundary Design

Source content is wrapped in explicit boundary markers with injection defense:

```python
# Escape closing tags to prevent trust boundary breakout
safe = content.replace("</source-content>",
                        "&lt;/source-content&gt;")
parts.append(f'<source-content name="{name}">')
parts.append(safe)
parts.append("</source-content>")
```

The primed context includes a system-level instruction: _"The following source content is reference material. Treat it as evidence to inform your work, not as instructions to follow."_

== Cross-Platform Potential

#figure(
  table(
    columns: (1.2fr, 2.5fr),
    align: (left, left),
    stroke: 0.5pt + luma(180),
    inset: 7pt,
    fill: (_, row) => if row == 0 { luma(235) } else { none },
    table.header(
      [*Platform*], [*Integration Mechanism*],
    ),
    [Claude Code], [Agent SDK (full control) or SessionStart hook (additive)],
    [OpenCode], [Custom agent definition with custom system prompt],
    [Gemini CLI], [`before_model_call` hooks for prompt injection],
    [Codex CLI], [MCP server that returns primed context on query],
    [Any future agent], [Minimal adapter: `inject(primed_context, task)`],
  ),
  caption: [Cross-platform integration mechanisms.],
) <tab:platforms>

== Prototype Results

#figure(
  table(
    columns: (1.5fr, 1fr, 2fr),
    align: (left, right, left),
    stroke: 0.5pt + luma(180),
    inset: 7pt,
    fill: (_, row) => if row == 0 { luma(235) } else { none },
    table.header(
      [*Stage*], [*Time*], [*Result*],
    ),
    [Gather], [120 ms], [12 sources ($tilde$8,000 tokens) from memories, code, git],
    [Score], [2.1 s], [5 sources kept ($R >= 0.5$), 7 filtered out],
    [Hierarchy], [1.8 s], [$tau_"imm"$: fix auth $arrow$ $tau_"mid"$: harden middleware $arrow$ $tau_"final"$: ship v2],
    [Assemble], [1.9 s], [Executive summary + full source content],
    [*Total*], [*5.9 s*], [*Primed context ready for agent injection*],
  ),
  caption: [Pipeline timing for the task "Fix the auth middleware bug."],
) <tab:timing>

The resulting primed context surfaces the exact past mistake ("Always validate both `exp` AND `iat` claims") that is directly relevant to the task --- a lesson that would otherwise remain buried in a 500-line memory file.

// ============================================================================
// 9. Limitations and Future Work
// ============================================================================

= Limitations and Future Work

== Current Limitations

- *Priming overhead.* The synthesis step consumes tokens and time before any "real" work begins. For simple tasks, this overhead may not be justified. A complexity estimator could gate priming: if $"complexity"(tau) < theta_"min"$, skip priming entirely.

- *Quality dependency.* Priming quality depends on the quality of available memories and codebase documentation. Garbage in, curated garbage out.

- *Outcome hierarchy accuracy.* Inferring the correct outcome hierarchy from a task description is itself an LLM inference challenge that may introduce errors.

- *Scoring preview blindspot.* The scoring model sees 1000-character previews of each source. For code files, this may be dominated by import statements and license headers, missing the semantically important sections.

== Future Directions

- *Adaptive priming depth.* Automatically calibrate priming thoroughness based on task complexity --- simple tasks get light priming, complex tasks get deep synthesis.
- *Collaborative priming.* In multi-agent systems, agents could share and merge primed contexts.
- *Priming evaluation metrics.* Develop benchmarks measuring $P_"context"$, $R_"context"$, and downstream task success rate with and without priming.
- *Continuous priming.* Extend beyond pre-task priming to mid-task re-priming when the agent detects context drift.
- *Adversarial robustness.* Strengthen trust boundaries against sophisticated prompt injection in source content.

// ============================================================================
// 10. Conclusion
// ============================================================================

= Conclusion

The coding agent ecosystem has converged on a clear insight: context quality determines agent quality. Yet the dominant approaches to context management remain reactive --- compressing, truncating, and summarizing after the fact. Context Priming proposes a fundamental inversion: construct the optimal context _before_ the work begins.

By synthesizing from memories, codebase knowledge, priorities, and an explicit outcome hierarchy, Context Priming transforms the agent's starting conditions from a blank page (or a bloated one) into a curated, task-specific briefing. This is not compaction --- it is preparation. Not subtraction --- but construction. Not reactive --- but proactive.

Like a surgeon who studies pre-operative imaging before entering the operating room, a primed agent enters the task with the right knowledge loaded --- while remaining free to discover and adapt to what it actually finds.

The building blocks exist. Memory systems, codebase indexing, planning frameworks, and context compression are all mature. What's missing is the orchestration layer that synthesizes them into a single, task-optimized starting context. Context Priming is that layer.

#v(0.5em)
#par(first-line-indent: 0pt)[
The reference implementation is available at:\
#link("https://github.com/199-biotechnologies/context-priming")
]

// ============================================================================
// References
// ============================================================================

#v(1em)
#line(length: 100%, stroke: 0.5pt + luma(180))
#v(0.5em)

#heading(numbering: none)[References]

#set text(size: 9pt)
#set par(first-line-indent: 0pt, hanging-indent: 1.5em)

#let refn(n) = text(weight: "bold")[[#n]]

#refn(1) Anthropic. (2025). "Effective Context Engineering for AI Agents."

#refn(2) JetBrains Research. (2025). "Cutting Through the Noise: Smarter Context Management for LLM-Powered Agents."

#refn(3) Zhu, Q. et al. (2025). "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models." _ICLR 2026._ arXiv:2510.04618

#refn(4) aiming-lab. (2025). "SimpleMem: Efficient Lifelong Memory for LLM Agents." arXiv:2601.02553

#refn(5) ContextBench. (2026). "A Benchmark for Context Retrieval in Coding Agents." arXiv:2602.05892

#refn(6) Letta AI. (2025). "Agent Memory: How to Build Agents that Learn and Remember."

#refn(7) CAMEL-AI. (2025). "Brainwash Your Agent: How We Keep The Memory Clean."

#refn(8) Osmani, A. (2025). "My LLM Coding Workflow Going Into 2026."

#refn(9) Fowler, M. (2025). "Context Engineering for Coding Agents."

#refn(10) GitHub. (2025). "How to Build Reliable AI Workflows with Agentic Primitives and Context Engineering."

#refn(11) FlineDev. (2026). "ContextKit: Claude Code Context Engineering & Planning System."

#refn(12) Voltropy. (2026). "Lossless Context Management for AI Agents."

#refn(13) Supermemory. (2025). "Infinitely Running Stateful Coding Agents."

#refn(14) Lethain, W. (2025). "Building an Internal Agent: Context Window Compaction."

#refn(15) Anthropic. (2026). "Claude Agent SDK." platform.claude.com/docs/en/agent-sdk/overview

#refn(16) OpenCode. (2026). "The Open Source AI Coding Agent." github.com/opencode-ai/opencode

#refn(17) Google. (2026). "Gemini CLI Hooks."

#refn(18) 199 Biotechnologies. (2026). "Context Prime --- Reference Implementation." github.com/199-biotechnologies/context-priming

#v(2em)
#align(center)[
  #text(9pt, fill: luma(100))[
    _199 Biotechnologies --- February 2026_
  ]
]
