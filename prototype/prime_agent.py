#!/usr/bin/env python3
"""Context Priming — Agent SDK Prototype

End-to-end demonstration of Context Priming for a coding agent.
The agent primes itself before starting work, constructing an optimal
context from memories, codebase, git history, and goal awareness.

Usage:
    python prime_agent.py "Fix the auth middleware bug" --project /path/to/project
    python prime_agent.py "Add pagination to the API" --project . --verbose

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-...

Optional (for full Agent SDK mode):
    pip install claude-code-sdk
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent

from anthropic import Anthropic


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PRIMING_MODEL = "claude-sonnet-4-6"      # Fast model for priming steps
AGENT_MODEL = "claude-opus-4-6"          # Best model for actual work
RELEVANCE_THRESHOLD = 0.5
MAX_CONTEXT_TOKENS = 50000


# ---------------------------------------------------------------------------
# Source Gathering (lightweight, no LLM needed)
# ---------------------------------------------------------------------------

def gather_sources(project_dir: str) -> list[dict]:
    """Gather all available context sources from the project."""
    sources = []
    project = Path(project_dir)

    # 1. Memory files
    memory_locations = [
        project / "MEMORY.md",
        Path.home() / ".claude" / "memory",
        Path.home() / ".claude" / "projects",
    ]
    for loc in memory_locations:
        if loc.is_file():
            sources.append({
                "category": "memories",
                "name": loc.name,
                "content": loc.read_text(errors="replace")[:4000],
            })
        elif loc.is_dir():
            for md in sorted(loc.glob("**/*.md"))[:10]:
                content = md.read_text(errors="replace")
                if content.strip():
                    sources.append({
                        "category": "memories",
                        "name": str(md.relative_to(loc)),
                        "content": content[:4000],
                    })

    # 2. Project config
    for fname in ["README.md", "CLAUDE.md", "AGENTS.md", "package.json",
                   "pyproject.toml", "Cargo.toml", "go.mod"]:
        fpath = project / fname
        if fpath.is_file():
            sources.append({
                "category": "codebase",
                "name": fname,
                "content": fpath.read_text(errors="replace")[:4000],
            })

    # 3. Directory structure
    try:
        result = subprocess.run(
            ["find", ".", "-maxdepth", "3", "-type", "f",
             "-not", "-path", "./.git/*", "-not", "-path", "./node_modules/*",
             "-not", "-path", "./.venv/*"],
            capture_output=True, text=True, cwd=project_dir, timeout=5,
        )
        if result.stdout:
            sources.append({
                "category": "codebase",
                "name": "directory_structure",
                "content": result.stdout[:3000],
            })
    except Exception:
        pass

    # 4. Git history
    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "-15"],
            capture_output=True, text=True, cwd=project_dir, timeout=5,
        )
        if log.returncode == 0 and log.stdout:
            sources.append({
                "category": "git",
                "name": "recent_commits",
                "content": log.stdout,
            })

        diff = subprocess.run(
            ["git", "diff", "--stat", "HEAD~5..HEAD"],
            capture_output=True, text=True, cwd=project_dir, timeout=5,
        )
        if diff.returncode == 0 and diff.stdout:
            sources.append({
                "category": "git",
                "name": "recent_changes",
                "content": diff.stdout,
            })
    except Exception:
        pass

    return sources


# ---------------------------------------------------------------------------
# Priming Pipeline (3 LLM calls: score → hierarchy → synthesize)
# ---------------------------------------------------------------------------

def llm_call(client: Anthropic, prompt: str, model: str = PRIMING_MODEL) -> str:
    """Make a single LLM call for priming steps."""
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def score_sources(client: Anthropic, task: str, sources: list[dict]) -> list[dict]:
    """Score each source's relevance to the task."""
    sources_block = ""
    for i, s in enumerate(sources):
        preview = s["content"][:800]
        sources_block += f"\n### Source {i}: [{s['category']}] {s['name']}\n{preview}\n"

    prompt = f"""Score each source's relevance to this task. Return JSON array only.

Task: {task}

Sources:{sources_block}

Return: [{{"index": 0, "score": 0.85, "reason": "..."}}, ...]
Scores: 0.9-1.0 = essential, 0.7-0.9 = important, 0.4-0.7 = tangential, <0.4 = irrelevant."""

    response = llm_call(client, prompt)

    # Parse scores
    import re
    match = re.search(r'\[[\s\S]*\]', response)
    if not match:
        return [{"source": s, "score": 0.5} for s in sources]

    try:
        scores = json.loads(match.group())
        scored = []
        for item in scores:
            idx = item.get("index", -1)
            if 0 <= idx < len(sources):
                scored.append({
                    "source": sources[idx],
                    "score": item.get("score", 0.5),
                    "reason": item.get("reason", ""),
                })
        # Add any unscored sources
        scored_indices = {item.get("index") for item in scores}
        for i, s in enumerate(sources):
            if i not in scored_indices:
                scored.append({"source": s, "score": 0.3, "reason": "Not scored"})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
    except json.JSONDecodeError:
        return [{"source": s, "score": 0.5} for s in sources]


def infer_hierarchy(client: Anthropic, task: str, context: str) -> dict:
    """Infer the outcome hierarchy — immediate, mid-term, final goals."""
    prompt = f"""Analyze this task and infer the outcome hierarchy. Return JSON only.

Task: {task}

Project context:
{context[:2000]}

Return: {{"immediate": "...", "midterm": "... or null", "final": "... or null", "confidence": "high|medium|low"}}"""

    response = llm_call(client, prompt)
    import re
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"immediate": task, "midterm": None, "final": None, "confidence": "low"}


def synthesize(
    client: Anthropic,
    task: str,
    hierarchy: dict,
    relevant_sources: list[dict],
) -> str:
    """Synthesize relevant sources into a primed context block."""
    sources_block = ""
    for item in relevant_sources:
        s = item["source"]
        sources_block += f"\n### [{s['category']}] {s['name']} (relevance: {item['score']:.1f})\n{s['content']}\n"

    prompt = f"""Synthesize these sources into a primed context for a coding agent.

Task: {task}

Outcome Hierarchy:
- Immediate: {hierarchy.get('immediate', task)}
- Mid-term: {hierarchy.get('midterm') or 'Not inferred'}
- Final: {hierarchy.get('final') or 'Not inferred'}

Sources:{sources_block}

Create a dense, task-specific briefing document (1500-3000 tokens).
Include: relevant file paths, patterns, past lessons, constraints.
Synthesize — don't concatenate. Every sentence should carry signal."""

    return llm_call(client, prompt)


def prime(client: Anthropic, task: str, project_dir: str, verbose: bool = False) -> str:
    """Run the full priming pipeline. Returns the primed context."""
    t0 = time.time()

    # Gather
    if verbose:
        print("[1/4] Gathering sources...", file=sys.stderr)
    sources = gather_sources(project_dir)
    if verbose:
        print(f"      Found {len(sources)} sources", file=sys.stderr)

    # Score
    if verbose:
        print("[2/4] Scoring relevance...", file=sys.stderr)
    scored = score_sources(client, task, sources)
    relevant = [s for s in scored if s["score"] >= RELEVANCE_THRESHOLD]
    if verbose:
        print(f"      Kept {len(relevant)}/{len(scored)} sources", file=sys.stderr)
        for r in relevant:
            print(f"        {r['score']:.1f} [{r['source']['category']}] {r['source']['name']}", file=sys.stderr)

    # Hierarchy
    if verbose:
        print("[3/4] Inferring outcome hierarchy...", file=sys.stderr)
    context_preview = "\n".join(r["source"]["content"][:500] for r in relevant[:5])
    hierarchy = infer_hierarchy(client, task, context_preview)
    if verbose:
        print(f"      Immediate: {hierarchy.get('immediate')}", file=sys.stderr)
        print(f"      Mid-term:  {hierarchy.get('midterm')}", file=sys.stderr)
        print(f"      Final:     {hierarchy.get('final')}", file=sys.stderr)

    # Synthesize
    if verbose:
        print("[4/4] Synthesizing primed context...", file=sys.stderr)
    synthesized = synthesize(client, task, hierarchy, relevant)

    elapsed = time.time() - t0
    if verbose:
        print(f"\n[done] Primed in {elapsed:.1f}s ({len(synthesized)} chars)", file=sys.stderr)

    # Format
    primed = f"""# Primed Context

> Automatically synthesized for: {task}
> Priming took {elapsed:.1f}s | {len(relevant)} sources used | {len(scored)} total gathered

## Outcome Hierarchy
- **Final goal:** {hierarchy.get('final') or 'Not inferred'}
- **Mid-term:** {hierarchy.get('midterm') or 'Not inferred'}
- **Immediate task:** {hierarchy.get('immediate', task)}

{synthesized}"""

    return primed


# ---------------------------------------------------------------------------
# Execution — launch agent with primed context
# ---------------------------------------------------------------------------

def run_with_raw_api(client: Anthropic, task: str, primed_context: str):
    """Run the coding agent using the raw Messages API."""
    print("\n" + "=" * 60)
    print("PRIMED AGENT EXECUTING")
    print("=" * 60 + "\n")

    response = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=8192,
        system=primed_context,
        messages=[{"role": "user", "content": task}],
    )

    print(response.content[0].text)


async def run_with_agent_sdk(task: str, primed_context: str, project_dir: str):
    """Run the coding agent using the Claude Agent SDK."""
    try:
        from claude_code_sdk import query, ClaudeCodeOptions

        print("\n" + "=" * 60)
        print("PRIMED AGENT EXECUTING (Agent SDK)")
        print("=" * 60 + "\n")

        options = ClaudeCodeOptions(
            system_prompt=primed_context,
            cwd=project_dir,
            model=AGENT_MODEL,
        )

        async for msg in query(prompt=task, options=options):
            if hasattr(msg, "content"):
                print(msg.content, end="", flush=True)
        print()

    except ImportError:
        return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Context Priming — Agent SDK Prototype",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            Examples:
              python prime_agent.py "Fix the auth middleware bug" --project ./myapp
              python prime_agent.py "Add pagination to the API" --project . --verbose
              python prime_agent.py "Refactor the database layer" --prime-only
        """),
    )
    parser.add_argument("task", help="The task for the coding agent")
    parser.add_argument("--project", "-p", default=".", help="Project directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show priming details")
    parser.add_argument("--prime-only", action="store_true", help="Only prime, don't execute")
    parser.add_argument("--use-sdk", action="store_true", help="Use Claude Agent SDK (if installed)")
    parser.add_argument("--priming-model", default=PRIMING_MODEL, help="Model for priming steps")
    parser.add_argument("--agent-model", default=AGENT_MODEL, help="Model for execution")

    args = parser.parse_args()

    # Validate
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: Set ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    project_dir = os.path.abspath(args.project)
    if not os.path.isdir(project_dir):
        print(f"Error: {project_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    global PRIMING_MODEL, AGENT_MODEL
    PRIMING_MODEL = args.priming_model
    AGENT_MODEL = args.agent_model

    client = Anthropic()

    # --- Prime ---
    primed_context = prime(client, args.task, project_dir, verbose=args.verbose)

    if args.prime_only:
        print(primed_context)
        return

    if args.verbose:
        print("\n--- PRIMED CONTEXT ---\n", file=sys.stderr)
        print(primed_context, file=sys.stderr)
        print("\n--- END PRIMED CONTEXT ---\n", file=sys.stderr)

    # --- Execute ---
    if args.use_sdk:
        success = asyncio.run(
            run_with_agent_sdk(args.task, primed_context, project_dir)
        )
        if not success:
            print("[fallback] Agent SDK not available, using raw API.", file=sys.stderr)
            run_with_raw_api(client, args.task, primed_context)
    else:
        run_with_raw_api(client, args.task, primed_context)


if __name__ == "__main__":
    main()
