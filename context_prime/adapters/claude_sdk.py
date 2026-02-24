"""Claude Agent SDK adapter — run a primed coding agent."""

import asyncio
from context_prime.core.gather import gather_all
from context_prime.core.score import score_relevance, filter_relevant
from context_prime.core.hierarchy import infer_hierarchy
from context_prime.core.synthesize import synthesize_context, format_primed_context


def make_anthropic_llm_call(model: str = "claude-sonnet-4-6"):
    """Create an LLM call function using the Anthropic API.

    Uses a fast model for priming steps (scoring, hierarchy, synthesis)
    to minimize overhead before the main agent starts.
    """
    from anthropic import Anthropic
    client = Anthropic()

    def llm_call(prompt: str) -> str:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    return llm_call


def prime(
    task: str,
    project_dir: str,
    memory_paths: list[str] | None = None,
    priming_model: str = "claude-sonnet-4-6",
    relevance_threshold: float = 0.5,
    max_context_tokens: int = 50000,
) -> str:
    """Run the full priming pipeline and return the primed context.

    Args:
        task: The user's task description.
        project_dir: Path to the project directory.
        memory_paths: Optional list of memory file/directory paths.
        priming_model: Model to use for priming steps (fast model recommended).
        relevance_threshold: Minimum relevance score to include a source.
        max_context_tokens: Maximum tokens for the primed context sources.

    Returns:
        A formatted primed context string ready for agent injection.
    """
    llm_call = make_anthropic_llm_call(priming_model)

    # 1. Gather all sources
    sources = gather_all(project_dir, memory_paths)

    # 2. Score relevance against the task
    scored = score_relevance(task, sources, llm_call)

    # 3. Filter to relevant sources
    relevant = filter_relevant(scored, relevance_threshold, max_context_tokens)

    # 4. Build project context for hierarchy inference
    project_context = "\n".join(
        s.source.content[:500] for s in relevant[:5]
    )

    # 5. Infer outcome hierarchy
    hierarchy = infer_hierarchy(task, project_context, llm_call)

    # 6. Synthesize into primed context
    synthesized = synthesize_context(task, hierarchy, relevant, llm_call)

    # 7. Format with standard framing
    return format_primed_context(task, hierarchy, synthesized)


async def run_primed_agent(
    task: str,
    project_dir: str,
    agent_model: str = "claude-opus-4-6",
    priming_model: str = "claude-sonnet-4-6",
    memory_paths: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    verbose: bool = False,
):
    """Run a coding agent with a primed context.

    This is the main entry point for the Claude Agent SDK adapter.
    It primes the context, then launches an agent with the Claude Agent SDK.

    Args:
        task: The user's task description.
        project_dir: Path to the project directory.
        agent_model: Model for the main coding agent.
        priming_model: Model for priming steps (fast model saves cost).
        memory_paths: Optional memory file/directory paths.
        allowed_tools: Tools the agent can use. Defaults to all.
        verbose: Print priming details.
    """
    # --- Priming Phase ---
    if verbose:
        print("[prime] Gathering sources...")

    primed_context = prime(
        task=task,
        project_dir=project_dir,
        memory_paths=memory_paths,
        priming_model=priming_model,
    )

    if verbose:
        print(f"[prime] Primed context: {len(primed_context)} chars")
        print("[prime] Launching agent with primed context...")

    # --- Execution Phase ---
    # Import here to make Agent SDK an optional dependency
    try:
        from claude_code_sdk import query, ClaudeCodeOptions

        system_prompt = primed_context + "\n\n---\n\n## Your Task\n\n" + task

        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            cwd=project_dir,
            model=agent_model,
        )
        if allowed_tools:
            options.allowed_tools = allowed_tools

        async for message in query(prompt=task, options=options):
            if hasattr(message, "content"):
                print(message.content)

    except ImportError:
        # Fallback: use raw Anthropic API with tool use
        print("[prime] Claude Agent SDK not installed. Using raw API fallback.")
        print("[prime] Install with: pip install claude-code-sdk")
        print()
        _run_with_raw_api(task, primed_context, project_dir, agent_model)


def _run_with_raw_api(
    task: str,
    primed_context: str,
    project_dir: str,
    model: str,
):
    """Fallback: run with raw Anthropic Messages API."""
    from anthropic import Anthropic
    client = Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=primed_context,
        messages=[{"role": "user", "content": task}],
    )

    print("\n--- Primed Agent Response ---\n")
    print(response.content[0].text)
