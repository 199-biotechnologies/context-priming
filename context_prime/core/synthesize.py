"""Context synthesis — assemble relevant sources into a primed context block.

Design philosophy: Context Priming is about SELECTION, not compression.
The scoring step decides what's relevant. The synthesis step assembles it.

A primed context can use 5k, 25k, or 40k tokens — as long as it's all
relevant to the task. The constraint is a percentage of available context
(default 25%), not a fixed small number. Including full source content is
better than a lossy summary. The agent needs the actual data.
"""

from context_prime.core.score import ScoredSource


# Light synthesis prompt — just a brief executive summary, not a rewrite
BRIEF_SYNTHESIS_PROMPT = """Write a 3-5 sentence executive summary for a coding agent about to work on this task.

Task: {task}

Outcome Hierarchy:
- Immediate: {immediate}
- Mid-term: {midterm}
- Final: {final}

Key sources available: {source_names}

Write ONLY the summary paragraph. Be specific about what files to touch, what to watch out for, and what the real goal is. No headers, no formatting — just the paragraph."""


def assemble_context(
    task: str,
    hierarchy: dict,
    relevant_sources: list[ScoredSource],
    llm_call=None,
) -> str:
    """Assemble relevant sources into a primed context block.

    This is the primary synthesis function. It includes full source content
    (not summaries) because the value is in selection, not compression.
    The scoring step already filtered irrelevant sources. What remains
    should be included in full.

    If llm_call is provided, adds a brief executive summary at the top.
    If not, assembles sources directly (zero LLM calls, instant).

    Args:
        task: The user's task description.
        hierarchy: Outcome hierarchy dict from infer_hierarchy().
        relevant_sources: Filtered, scored sources from filter_relevant().
        llm_call: Optional callable(prompt: str) -> str. If provided,
                  generates a brief executive summary. If None, skips it.

    Returns:
        A markdown string — the primed context ready for injection.
    """
    parts = []

    # Header
    parts.append("# Primed Context\n")
    parts.append("> Auto-assembled from project sources scored for task relevance.\n")

    # Outcome hierarchy
    parts.append("## Outcome Hierarchy\n")
    final = hierarchy.get("final")
    midterm = hierarchy.get("midterm")
    immediate = hierarchy.get("immediate", task)
    if final:
        parts.append(f"- **Final goal:** {final}")
    if midterm:
        parts.append(f"- **Mid-term:** {midterm}")
    parts.append(f"- **Immediate task:** {immediate}")
    parts.append("")

    # Brief executive summary (1 LLM call, fast)
    if llm_call:
        source_names = ", ".join(
            f"{s.source.name} ({s.source.category})" for s in relevant_sources
        )
        prompt = BRIEF_SYNTHESIS_PROMPT.format(
            task=task,
            immediate=immediate,
            midterm=midterm or "Not inferred",
            final=final or "Not inferred",
            source_names=source_names,
        )
        summary = llm_call(prompt)
        parts.append("## Summary\n")
        parts.append(summary.strip())
        parts.append("")

    # Full source content — ordered by relevance, highest first
    parts.append("## Relevant Sources\n")
    for ss in relevant_sources:
        parts.append(
            f"### [{ss.source.category}] {ss.source.name} "
            f"(relevance: {ss.score:.2f})\n"
        )
        parts.append(ss.source.content)
        parts.append("")

    return "\n".join(parts)


# Keep the old function name as an alias for backward compatibility
def synthesize_context(
    task: str,
    hierarchy: dict,
    relevant_sources: list[ScoredSource],
    llm_call: callable,
) -> str:
    """Synthesize relevant sources into a primed context block.

    Now delegates to assemble_context which includes full source content
    instead of compressing into a tiny summary. Uses 1 fast LLM call for
    a brief executive summary, then includes sources in full.
    """
    return assemble_context(task, hierarchy, relevant_sources, llm_call)


def format_primed_context(
    task: str,
    hierarchy: dict,
    synthesized: str,
) -> str:
    """Format compatibility wrapper.

    With the new assemble_context, the output is already fully formatted.
    This function exists for backward compatibility with code that calls
    synthesize_context() + format_primed_context() separately.
    """
    # If synthesized already has the header (from assemble_context), return as-is
    if synthesized.startswith("# Primed Context"):
        return synthesized

    # Legacy path: wrap raw synthesis output
    header = "# Primed Context\n\n"
    header += "> This context was automatically synthesized for your current task.\n\n"

    goal_section = "## Outcome Hierarchy\n\n"
    goal_section += f"- **Final goal:** {hierarchy.get('final') or 'Not inferred'}\n"
    goal_section += f"- **Mid-term:** {hierarchy.get('midterm') or 'Not inferred'}\n"
    goal_section += f"- **Immediate task:** {hierarchy.get('immediate', task)}\n\n"

    return header + goal_section + synthesized
