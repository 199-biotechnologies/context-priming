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
        # Fallback: score everything at 0.5
        return [
            ScoredSource(source=s, score=0.5, reasoning="Scoring failed, default score")
            for s in sources.sources
        ]

    try:
        scores = json.loads(json_match.group())
    except json.JSONDecodeError:
        return [
            ScoredSource(source=s, score=0.5, reasoning="Scoring failed, default score")
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


def filter_relevant(
    scored_sources: list[ScoredSource],
    threshold: float = 0.5,
    max_tokens: int = 50000,
) -> list[ScoredSource]:
    """Filter scored sources by threshold and token budget.

    Args:
        scored_sources: Sources with scores, sorted by score descending.
        threshold: Minimum score to include (default 0.5).
        max_tokens: Maximum total tokens to include.

    Returns:
        Filtered list respecting both threshold and token budget.
    """
    filtered = []
    token_count = 0

    for ss in scored_sources:
        if ss.score < threshold:
            continue
        if token_count + ss.source.token_estimate > max_tokens:
            continue
        filtered.append(ss)
        token_count += ss.source.token_estimate

    return filtered
