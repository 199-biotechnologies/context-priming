"""Context Prime CLI — prime your coding agent from the command line."""

import argparse
import json
import os
import sys
from pathlib import Path


def get_llm_call(model: str = "claude-sonnet-4-6"):
    """Create an LLM call function. Tries Anthropic first, then OpenAI."""
    if os.environ.get("ANTHROPIC_API_KEY"):
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
            "Error: Set ANTHROPIC_API_KEY or OPENAI_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_prime(args):
    """Run the priming pipeline."""
    from context_prime.core.gather import gather_all
    from context_prime.core.score import score_relevance, filter_relevant
    from context_prime.core.hierarchy import infer_hierarchy
    from context_prime.core.synthesize import synthesize_context, format_primed_context

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
        # Session mode: just output gathered context summary, no task-specific scoring
        output = "## Project Context (auto-primed at session start)\n\n"
        for src in sources.sources:
            if src.category in ("codebase", "config"):
                content = src.content[:500]
                output += f"### {src.name}\n{content}\n\n"

        # Include all memories
        for src in sources.sources:
            if src.category == "memories":
                output += f"### Memory: {src.name}\n{src.content}\n\n"

        if args.format == "hook":
            print(output)
        else:
            print(output)
        return

    task = args.task or "General development work"

    # Score
    if args.verbose:
        print("[score] Scoring relevance...", file=sys.stderr)
    scored = score_relevance(task, sources, llm_call)

    # Filter
    relevant = filter_relevant(scored, args.threshold, args.max_tokens)
    if args.verbose:
        print(
            f"[filter] Kept {len(relevant)}/{len(scored)} sources",
            file=sys.stderr,
        )

    # Hierarchy
    if args.verbose:
        print("[hierarchy] Inferring outcome hierarchy...", file=sys.stderr)
    project_context = "\n".join(s.source.content[:500] for s in relevant[:5])
    hierarchy = infer_hierarchy(task, project_context, llm_call)

    # Synthesize
    if args.verbose:
        print("[synthesize] Building primed context...", file=sys.stderr)
    synthesized = synthesize_context(task, hierarchy, relevant, llm_call)
    primed = format_primed_context(task, hierarchy, synthesized)

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
    p_prime.add_argument("--max-tokens", type=int, default=50000, help="Max context tokens")
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
