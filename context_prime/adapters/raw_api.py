"""Raw API adapter — use Context Prime with any LLM provider directly."""

from context_prime.core.gather import gather_all
from context_prime.core.score import score_relevance, filter_relevant
from context_prime.core.hierarchy import infer_hierarchy
from context_prime.core.synthesize import assemble_context


def prime_for_api(
    task: str,
    project_dir: str,
    llm_call: callable,
    memory_paths: list[str] | None = None,
    relevance_threshold: float = 0.5,
    max_context_tokens: int = 50000,
) -> dict:
    """Run the priming pipeline and return structured output for API use.

    This adapter is model-agnostic. Pass any llm_call function that
    takes a prompt string and returns a response string.

    Args:
        task: The user's task description.
        project_dir: Path to the project directory.
        llm_call: A callable(prompt: str) -> str for any LLM.
        memory_paths: Optional memory file/directory paths.
        relevance_threshold: Minimum relevance score.
        max_context_tokens: Token budget for sources.

    Returns:
        Dict with keys:
            - system_prompt: The primed context as a system prompt string
            - hierarchy: The inferred outcome hierarchy
            - sources_used: List of source names that were included
            - sources_excluded: List of source names that were filtered out
            - stats: Token counts and source statistics
    """
    # Gather
    sources = gather_all(project_dir, memory_paths)

    # Score
    scored = score_relevance(task, sources, llm_call)

    # Filter
    relevant = filter_relevant(scored, relevance_threshold, max_context_tokens)
    excluded = [s for s in scored if s not in relevant]

    # Hierarchy
    project_context = "\n".join(s.source.content[:500] for s in relevant[:5])
    hierarchy = infer_hierarchy(task, project_context, llm_call)

    # Assemble — full source content + brief executive summary
    primed = assemble_context(task, hierarchy, relevant, llm_call)

    return {
        "system_prompt": primed,
        "hierarchy": hierarchy,
        "sources_used": [
            {"name": s.source.name, "category": s.source.category, "score": s.score}
            for s in relevant
        ],
        "sources_excluded": [
            {"name": s.source.name, "category": s.source.category, "score": s.score}
            for s in excluded
        ],
        "stats": {
            "total_sources_gathered": len(sources.sources),
            "sources_included": len(relevant),
            "sources_excluded": len(excluded),
            "total_tokens_gathered": sources.total_tokens,
            "tokens_in_primed_context": len(primed) // 4,
        },
    }


def prime_messages(
    task: str,
    project_dir: str,
    llm_call: callable,
    **kwargs,
) -> list[dict]:
    """Return a messages array ready for any Chat Completions-style API.

    Usage with Anthropic:
        messages = prime_messages(task, project_dir, llm_call)
        response = client.messages.create(
            model="claude-opus-4-6",
            system=messages[0]["content"],  # primed context
            messages=messages[1:],          # task message
        )

    Usage with OpenAI:
        messages = prime_messages(task, project_dir, llm_call)
        response = client.chat.completions.create(
            model="gpt-5.3-codex",
            messages=messages,
        )
    """
    result = prime_for_api(task, project_dir, llm_call, **kwargs)

    return [
        {"role": "system", "content": result["system_prompt"]},
        {"role": "user", "content": task},
    ]
