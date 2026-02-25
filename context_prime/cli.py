"""Context Prime CLI — prime your coding agent from the command line."""

import argparse
import json
import os
import sys
from pathlib import Path


def get_llm_call(model: str = "claude-sonnet-4-6"):
    """Create an LLM call function. Tries OpenRouter, Anthropic, then OpenAI."""
    if os.environ.get("OPENROUTER_API_KEY"):
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        # Map short model names to OpenRouter format
        or_model = model
        if "/" not in model:
            or_model = f"anthropic/{model}"

        def call(prompt: str) -> str:
            r = client.chat.completions.create(
                model=or_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return r.choices[0].message.content
        return call

    elif os.environ.get("ANTHROPIC_API_KEY"):
        from anthropic import Anthropic
        client = Anthropic()

        def call(prompt: str) -> str:
            r = client.messages.create(
                model=model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return r.content[0].text
        return call

    elif os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI()

        def call(prompt: str) -> str:
            r = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return r.choices[0].message.content
        return call

    else:
        print(
            "Error: Set OPENROUTER_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_prime(args):
    """Run the priming pipeline."""
    from context_prime.core.gather import gather_all
    from context_prime.core.score import score_relevance, filter_relevant
    from context_prime.core.hierarchy import infer_hierarchy
    from context_prime.core.synthesize import assemble_context

    llm_call = get_llm_call(args.model)
    project_dir = os.path.abspath(args.project)

    # Gather
    if args.verbose:
        print("[gather] Scanning sources...", file=sys.stderr)

    memory_paths = args.memory.split(",") if args.memory else None
    sources = gather_all(project_dir, memory_paths)

    if args.verbose:
        print(
            f"[gather] Found {len(sources.sources)} sources "
            f"(~{sources.total_tokens} tokens)",
            file=sys.stderr,
        )

    if args.mode == "session" and not args.task:
        # Session mode: include full source content, no scoring needed
        output = "## Project Context (auto-primed at session start)\n\n"
        for src in sources.sources:
            output += f"### [{src.category}] {src.name}\n{src.content}\n\n"

        print(output)
        return

    task = args.task or "General development work"

    # Score
    if args.verbose:
        print("[score] Scoring relevance...", file=sys.stderr)
    scored = score_relevance(task, sources, llm_call)

    # Filter — budget is % of available context, include full content
    relevant = filter_relevant(
        scored, args.threshold,
        context_budget_pct=args.budget,
        platform=args.platform,
    )
    if args.verbose:
        budget_tokens = int({
            "claude_code": 120_000, "claude_api": 200_000,
            "gemini_cli": 1_000_000, "default": 128_000,
        }.get(args.platform, 128_000) * args.budget)
        print(
            f"[filter] Kept {len(relevant)}/{len(scored)} sources "
            f"(budget: {args.budget:.0%} = ~{budget_tokens:,} tokens)",
            file=sys.stderr,
        )

    # Hierarchy
    if args.verbose:
        print("[hierarchy] Inferring outcome hierarchy...", file=sys.stderr)
    project_context = "\n".join(s.source.content[:500] for s in relevant[:5])
    hierarchy = infer_hierarchy(task, project_context, llm_call)

    # Assemble — full source content + brief exec summary
    if args.verbose:
        print("[assemble] Building primed context...", file=sys.stderr)
    primed = assemble_context(task, hierarchy, relevant, llm_call)

    # Output
    if args.format == "json":
        output = {
            "primed_context": primed,
            "hierarchy": hierarchy,
            "sources_used": len(relevant),
            "total_sources": len(sources.sources),
        }
        print(json.dumps(output, indent=2))
    elif args.format == "hook":
        # Hook format: just the primed context as stdout
        print(primed)
    else:
        print(primed)


def cmd_gather(args):
    """Gather sources only (no scoring or synthesis)."""
    from context_prime.core.gather import gather_all

    project_dir = os.path.abspath(args.project)
    memory_paths = args.memory.split(",") if args.memory else None
    sources = gather_all(project_dir, memory_paths)

    if args.format == "json":
        output = {
            "project_dir": project_dir,
            "total_sources": len(sources.sources),
            "total_tokens": sources.total_tokens,
            "sources": [
                {
                    "category": s.category,
                    "name": s.name,
                    "tokens": s.token_estimate,
                    "preview": s.content[:200],
                }
                for s in sources.sources
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Gathered {len(sources.sources)} sources (~{sources.total_tokens} tokens)\n")
        for s in sources.sources:
            print(f"  [{s.category}] {s.name} (~{s.token_estimate} tokens)")


def main():
    parser = argparse.ArgumentParser(
        prog="context-prime",
        description="Context Prime — Proactive context synthesis for coding agents",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # prime command
    p_prime = subparsers.add_parser("prime", help="Run the full priming pipeline")
    p_prime.add_argument("--task", "-t", help="The task description")
    p_prime.add_argument("--project", "-p", default=".", help="Project directory")
    p_prime.add_argument("--memory", "-m", help="Comma-separated memory paths")
    p_prime.add_argument("--model", default="claude-sonnet-4-6", help="LLM model for priming")
    p_prime.add_argument("--threshold", type=float, default=0.5, help="Relevance threshold")
    p_prime.add_argument("--budget", type=float, default=0.25,
                         help="Context budget as fraction of platform context (default 0.25)")
    p_prime.add_argument("--platform", default="claude_code",
                         choices=["claude_code", "claude_api", "gemini_cli", "opencode", "codex_cli"],
                         help="Target platform for budget calculation")
    p_prime.add_argument("--mode", choices=["task", "session"], default="task")
    p_prime.add_argument("--format", choices=["text", "json", "hook"], default="text")
    p_prime.add_argument("--verbose", "-v", action="store_true")
    p_prime.set_defaults(func=cmd_prime)

    # gather command
    p_gather = subparsers.add_parser("gather", help="Gather sources only")
    p_gather.add_argument("--project", "-p", default=".", help="Project directory")
    p_gather.add_argument("--memory", "-m", help="Comma-separated memory paths")
    p_gather.add_argument("--format", choices=["text", "json"], default="text")
    p_gather.set_defaults(func=cmd_gather)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
