"""Context synthesis — combine relevant sources into a primed context block."""

from context_prime.core.score import ScoredSource


SYNTHESIS_PROMPT = """Synthesize the following sources into an optimal primed context for a coding agent.

## Task
{task}

## Outcome Hierarchy
- Immediate: {immediate}
- Mid-term: {midterm}
- Final: {final}

## Relevant Sources (scored by relevance)
{sources_block}

## Instructions
Create a single, coherent "Primed Context" document that a coding agent
will use as its starting context before working on this task.

Rules:
1. Synthesize, don't concatenate. Merge overlapping information.
2. Lead with what matters most for THIS specific task.
3. Include specific file paths, function names, and code patterns.
4. Surface past mistakes and lessons that apply to this task type.
5. Note constraints and conventions the agent must follow.
6. Keep the outcome hierarchy visible so the agent understands the bigger picture.
7. Be dense. Every sentence should carry information the agent needs.
8. Target 1500-3000 tokens. Enough to be useful, short enough to leave room for work.

Format the output as a markdown document with clear sections."""


def build_synthesis_prompt(
    task: str,
    hierarchy: dict,
    relevant_sources: list[ScoredSource],
) -> str:
    """Build the prompt for context synthesis."""
    sources_block = ""
    for ss in relevant_sources:
        sources_block += (
            f"\n### [{ss.source.category}] {ss.source.name} "
            f"(relevance: {ss.score:.1f})\n"
            f"{ss.source.content}\n"
        )

    return SYNTHESIS_PROMPT.format(
        task=task,
        immediate=hierarchy.get("immediate", task),
        midterm=hierarchy.get("midterm") or "Not inferred",
        final=hierarchy.get("final") or "Not inferred",
        sources_block=sources_block,
    )


def synthesize_context(
    task: str,
    hierarchy: dict,
    relevant_sources: list[ScoredSource],
    llm_call: callable,
) -> str:
    """Synthesize relevant sources into a primed context block.

    Args:
        task: The user's task description.
        hierarchy: Outcome hierarchy dict from infer_hierarchy().
        relevant_sources: Filtered, scored sources from filter_relevant().
        llm_call: A callable(prompt: str) -> str that calls an LLM.

    Returns:
        A markdown string — the primed context ready for injection.
    """
    prompt = build_synthesis_prompt(task, hierarchy, relevant_sources)
    return llm_call(prompt)


def format_primed_context(
    task: str,
    hierarchy: dict,
    synthesized: str,
) -> str:
    """Wrap the synthesized context with standard framing.

    This produces the final primed context block that gets injected
    into the coding agent's context window.
    """
    header = "# Primed Context\n\n"
    header += "> This context was automatically synthesized for your current task.\n"
    header += "> It draws from project memories, codebase analysis, and past lessons.\n\n"

    goal_section = "## Outcome Hierarchy\n\n"
    goal_section += f"- **Final goal:** {hierarchy.get('final') or 'Not inferred'}\n"
    goal_section += f"- **Mid-term:** {hierarchy.get('midterm') or 'Not inferred'}\n"
    goal_section += f"- **Immediate task:** {hierarchy.get('immediate', task)}\n\n"

    return header + goal_section + synthesized
