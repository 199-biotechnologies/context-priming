"""Relevance scoring — score gathered sources against a specific task."""

from dataclasses import dataclass
from context_prime.core.gather import Source, GatheredSources


@dataclass
class ScoredSource:
    """A source with its relevance score and reasoning."""
    source: Source
    score: float         # 0.0 to 1.0
    reasoning: str = ""  # why this score


SCORING_PROMPT = """Score the relevance of each source to the given task.

## Task
{task}

## Sources
{sources_block}

## Instructions
For each source, return a JSON array of objects:
```json
[
  {{"index": 0, "score": 0.85, "reasoning": "Directly relevant because..."}},
  ...
]
```

Score meaning:
- 0.9-1.0: Directly addresses the task (must include)
- 0.7-0.9: Provides important context (should include)
- 0.4-0.7: Tangentially related (include if space permits)
- 0.0-0.4: Not relevant to this task (exclude)

Be aggressive with low scores. The goal is to surface only what matters
for THIS specific task, not everything that might be vaguely useful.

Return ONLY the JSON array, no other text."""


def build_scoring_prompt(task: str, sources: GatheredSources) -> str:
    """Build the prompt for LLM-based relevance scoring."""
    sources_block = ""
    for i, src in enumerate(sources.sources):
        # Truncate individual sources for scoring (we just need enough to judge)
        content_preview = src.content[:1000]
        if len(src.content) > 1000:
            content_preview += "..."
        sources_block += f"\n### Source {i}: [{src.category}] {src.name}\n{content_preview}\n"

    return SCORING_PROMPT.format(task=task, sources_block=sources_block)


def parse_scores(response_text: str, sources: GatheredSources) -> list[ScoredSource]:
    """Parse LLM scoring response into ScoredSource objects."""
    import json
    import re

    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r'\[[\s\S]*\]', response_text)
    if not json_match:
        # Fail-closed: low score so threshold filter excludes by default
        return [
            ScoredSource(source=s, score=0.2, reasoning="Scoring parse failed — fail-closed")
            for s in sources.sources
        ]

    try:
        scores = json.loads(json_match.group())
    except json.JSONDecodeError:
        return [
            ScoredSource(source=s, score=0.2, reasoning="Scoring parse failed — fail-closed")
            for s in sources.sources
        ]

    scored = []
    for item in scores:
        idx = item.get("index", -1)
        if 0 <= idx < len(sources.sources):
            scored.append(ScoredSource(
                source=sources.sources[idx],
                score=min(1.0, max(0.0, float(item.get("score", 0.5)))),
                reasoning=item.get("reasoning", ""),
            ))

    # Add any sources that weren't scored
    scored_indices = {item.get("index") for item in scores}
    for i, src in enumerate(sources.sources):
        if i not in scored_indices:
            scored.append(ScoredSource(source=src, score=0.3, reasoning="Not scored"))

    return scored


def score_relevance(
    task: str,
    sources: GatheredSources,
    llm_call: callable,
) -> list[ScoredSource]:
    """Score all sources against a task using an LLM.

    Args:
        task: The user's task description.
        sources: Gathered sources to score.
        llm_call: A callable(prompt: str) -> str that calls an LLM.
                  This keeps the scoring engine model-agnostic.

    Returns:
        List of ScoredSource objects, sorted by score descending.
    """
    prompt = build_scoring_prompt(task, sources)
    response = llm_call(prompt)
    scored = parse_scores(response, sources)
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored


# Default context budgets for known platforms (coding-available tokens)
PLATFORM_CONTEXT_BUDGETS = {
    "claude_code": 120_000,   # Claude Code reserves ~80k for tools/MCP
    "claude_api": 200_000,    # Raw API, full window
    "opencode": 128_000,
    "gemini_cli": 1_000_000,  # Gemini 3 Pro
    "codex_cli": 200_000,
    "default": 128_000,
}


def filter_relevant(
    scored_sources: list[ScoredSource],
    threshold: float = 0.5,
    max_tokens: int | None = None,
    context_budget_pct: float = 0.25,
    platform: str = "claude_code",
) -> list[ScoredSource]:
    """Filter scored sources by threshold and context budget.

    The budget is a percentage of the platform's available coding context,
    not a fixed token count. Context Priming should use up to 25% of
    available context with highly relevant sources — the value is in
    selection, not compression.

    Uses categorical budgets to ensure memories and config sources aren't
    crowded out by code files, even if code scores slightly higher.

    Args:
        scored_sources: Sources with scores, sorted by score descending.
        threshold: Minimum score to include (default 0.5).
        max_tokens: Explicit token limit (overrides percentage calculation).
        context_budget_pct: Fraction of platform context to use (default 0.25).
        platform: Platform name for budget lookup (default "claude_code").

    Returns:
        Filtered list respecting both threshold and token budget.
    """
    if max_tokens is None:
        total_context = PLATFORM_CONTEXT_BUDGETS.get(
            platform, PLATFORM_CONTEXT_BUDGETS["default"]
        )
        max_tokens = int(total_context * context_budget_pct)

    # Reserve a portion of budget for non-code categories (memories, config, git)
    # This prevents code files from crowding out the lessons and priorities
    # that are the whole point of Context Priming.
    reserved_categories = {"memories", "config"}
    reserved_budget = int(max_tokens * 0.15)  # 15% reserved for memories+config
    code_budget = max_tokens - reserved_budget

    # First pass: include reserved-category sources that meet threshold
    filtered = []
    reserved_tokens = 0
    code_tokens = 0

    # Separate into reserved and general pools
    reserved_pool = [ss for ss in scored_sources if ss.source.category in reserved_categories]
    general_pool = [ss for ss in scored_sources if ss.source.category not in reserved_categories]

    # Fill reserved pool first (memories, config)
    for ss in reserved_pool:
        if ss.score < threshold:
            continue
        if reserved_tokens + ss.source.token_estimate > reserved_budget:
            continue
        filtered.append(ss)
        reserved_tokens += ss.source.token_estimate

    # Fill general pool (code, codebase, git) with remaining budget
    for ss in general_pool:
        if ss.score < threshold:
            continue
        if code_tokens + ss.source.token_estimate > code_budget:
            continue
        filtered.append(ss)
        code_tokens += ss.source.token_estimate

    # Re-sort by score descending for assembly
    filtered.sort(key=lambda s: s.score, reverse=True)
    return filtered
