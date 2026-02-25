#!/usr/bin/env python3
"""Full pipeline test for Context Prime using OpenRouter.

Tests each stage independently, then runs the full end-to-end pipeline,
and finally tests a parallel multi-task (subagent-style) orchestration.
"""

import json
import os
import sys
import time
import concurrent.futures
from pathlib import Path

# OpenRouter setup
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-6")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Set up OpenRouter LLM call
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


def openrouter_call(prompt: str) -> str:
    """LLM call via OpenRouter."""
    r = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content


def separator(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_gather():
    """Test 1: Source gathering (no LLM needed)."""
    separator("TEST 1: GATHER SOURCES")
    from context_prime.core.gather import gather_all

    t0 = time.time()
    task = "Improve the context scoring module to batch sources and reduce LLM calls"
    sources = gather_all(PROJECT_DIR, task=task)
    elapsed = time.time() - t0

    print(f"Gathered {len(sources.sources)} sources in {elapsed:.2f}s")
    print(f"Total estimated tokens: {sources.total_tokens}")
    print()
    for s in sources.sources:
        print(f"  [{s.category:10s}] {s.name:40s} (~{s.token_estimate:5d} tokens)")

    assert len(sources.sources) > 0, "FAIL: No sources gathered"
    print(f"\n  PASS: {len(sources.sources)} sources gathered")
    return sources


def test_score(sources, task: str):
    """Test 2: Relevance scoring."""
    separator("TEST 2: RELEVANCE SCORING")
    from context_prime.core.score import score_relevance, filter_relevant

    t0 = time.time()
    scored = score_relevance(task, sources, openrouter_call)
    elapsed = time.time() - t0

    print(f"Scored {len(scored)} sources in {elapsed:.2f}s")
    print()
    for ss in scored:
        print(f"  {ss.score:.2f}  [{ss.source.category:10s}] {ss.source.name}")
        if ss.reasoning:
            print(f"         Reason: {ss.reasoning[:80]}")

    # Filter
    relevant = filter_relevant(scored, threshold=0.5)
    excluded = [s for s in scored if s not in relevant]
    print(f"\nKept {len(relevant)}/{len(scored)} sources (threshold=0.5)")
    print(f"Filtered out {len(excluded)} irrelevant sources")

    assert len(scored) == len(sources.sources), \
        f"FAIL: scored {len(scored)} but gathered {len(sources.sources)}"
    assert all(0.0 <= ss.score <= 1.0 for ss in scored), "FAIL: scores out of range"
    print(f"\n  PASS: Scoring returned valid results")
    return relevant


def test_hierarchy(task: str, relevant):
    """Test 3: Outcome hierarchy inference."""
    separator("TEST 3: OUTCOME HIERARCHY")
    from context_prime.core.hierarchy import infer_hierarchy

    project_context = "\n".join(s.source.content[:500] for s in relevant[:5])

    t0 = time.time()
    hierarchy = infer_hierarchy(task, project_context, openrouter_call)
    elapsed = time.time() - t0

    print(f"Hierarchy inferred in {elapsed:.2f}s")
    print(f"\n  Immediate:  {hierarchy.get('immediate', 'N/A')}")
    print(f"  Mid-term:   {hierarchy.get('midterm', 'N/A')}")
    print(f"  Final:      {hierarchy.get('final', 'N/A')}")
    print(f"  Confidence: {hierarchy.get('confidence', 'N/A')}")
    print(f"  Reasoning:  {hierarchy.get('reasoning', 'N/A')[:120]}")

    assert "immediate" in hierarchy, "FAIL: Missing 'immediate' key"
    assert hierarchy.get("confidence") in ("high", "medium", "low", None), \
        f"FAIL: Invalid confidence: {hierarchy.get('confidence')}"
    print(f"\n  PASS: Hierarchy structure valid")
    return hierarchy


def test_synthesize(task: str, hierarchy: dict, relevant):
    """Test 4: Context assembly (full sources + executive summary)."""
    separator("TEST 4: CONTEXT ASSEMBLY")
    from context_prime.core.synthesize import assemble_context

    t0 = time.time()
    primed = assemble_context(task, hierarchy, relevant, openrouter_call)
    elapsed = time.time() - t0

    print(f"Assembled in {elapsed:.2f}s")
    print(f"Primed context: {len(primed)} chars (~{len(primed)//4} tokens)")
    print()
    # Print first 2000 chars of the primed context
    print(primed[:2000])
    if len(primed) > 2000:
        print(f"\n  ... [{len(primed) - 2000} more chars]")

    assert len(primed) > 200, "FAIL: Assembly too short"
    assert "Primed Context" in primed, "FAIL: Missing header"
    assert "Outcome Hierarchy" in primed, "FAIL: Missing hierarchy section"
    assert "starting point" in primed.lower(), "FAIL: Missing guidance framing"
    assert "source-content" in primed, "FAIL: Missing trust boundary markers"
    print(f"\n  PASS: Assembly produced valid primed context with trust boundaries")
    return primed


def test_full_pipeline(task: str):
    """Test 5: Full end-to-end pipeline."""
    separator("TEST 5: FULL PIPELINE (end-to-end)")
    from context_prime.core.gather import gather_all
    from context_prime.core.score import score_relevance, filter_relevant
    from context_prime.core.hierarchy import infer_hierarchy
    from context_prime.core.synthesize import assemble_context

    t0 = time.time()

    # Full pipeline — pass task to gather so code files are found
    sources = gather_all(PROJECT_DIR, task=task)
    scored = score_relevance(task, sources, openrouter_call)
    relevant = filter_relevant(scored, threshold=0.4)
    project_ctx = "\n".join(s.source.content[:500] for s in relevant[:5])
    hierarchy = infer_hierarchy(task, project_ctx, openrouter_call)
    primed = assemble_context(task, hierarchy, relevant, openrouter_call)

    elapsed = time.time() - t0

    print(f"Full pipeline: {elapsed:.1f}s total")
    print(f"  Sources gathered: {len(sources.sources)}")
    print(f"  Sources kept:     {len(relevant)}")
    print(f"  Primed context:   {len(primed)} chars (~{len(primed)//4} tokens)")
    print(f"\n  PASS: Full pipeline completed in {elapsed:.1f}s")
    return primed


def test_parallel_orchestration():
    """Test 6: Parallel multi-task orchestration (subagent pattern)."""
    separator("TEST 6: PARALLEL ORCHESTRATION (3 tasks)")
    from context_prime.core.gather import gather_all
    from context_prime.core.score import score_relevance, filter_relevant
    from context_prime.core.hierarchy import infer_hierarchy
    from context_prime.core.synthesize import assemble_context

    tasks = [
        "Add a new API endpoint for user search with pagination",
        "Fix the context synthesis module to handle empty source lists",
        "Write comprehensive tests for the scoring pipeline",
    ]

    # Gather once with combined keywords (shared across all tasks)
    combined_task = " ".join(tasks)
    sources = gather_all(PROJECT_DIR, task=combined_task)
    print(f"Shared gather: {len(sources.sources)} sources\n")

    def prime_single_task(task: str) -> dict:
        """Prime a single task (would be a subagent in production)."""
        t0 = time.time()
        scored = score_relevance(task, sources, openrouter_call)
        relevant = filter_relevant(scored, threshold=0.4)
        project_ctx = "\n".join(s.source.content[:500] for s in relevant[:5])
        hierarchy = infer_hierarchy(task, project_ctx, openrouter_call)
        primed = assemble_context(task, hierarchy, relevant, openrouter_call)
        elapsed = time.time() - t0
        return {
            "task": task,
            "elapsed": elapsed,
            "sources_kept": len(relevant),
            "primed_length": len(primed),
            "hierarchy": hierarchy,
        }

    # Run all 3 tasks in parallel (simulating subagent orchestration)
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(prime_single_task, t): t for t in tasks}
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    total_elapsed = time.time() - t0
    sequential_time = sum(r["elapsed"] for r in results)

    print("Results:")
    for r in results:
        print(f"\n  Task: {r['task'][:60]}...")
        print(f"    Time:    {r['elapsed']:.1f}s")
        print(f"    Sources: {r['sources_kept']} kept")
        print(f"    Context: {r['primed_length']} chars")
        print(f"    Goal:    {r['hierarchy'].get('immediate', 'N/A')[:60]}")

    speedup = sequential_time / total_elapsed if total_elapsed > 0 else 1
    print(f"\n  Parallel:   {total_elapsed:.1f}s")
    print(f"  Sequential: {sequential_time:.1f}s")
    print(f"  Speedup:    {speedup:.1f}x")
    print(f"\n  PASS: Parallel orchestration completed ({speedup:.1f}x speedup)")


def test_raw_api_adapter():
    """Test 7: Raw API adapter (model-agnostic output)."""
    separator("TEST 7: RAW API ADAPTER")
    from context_prime.adapters.raw_api import prime_for_api, prime_messages

    task = "Add error handling to the gather module"

    t0 = time.time()
    result = prime_for_api(
        task=task,
        project_dir=PROJECT_DIR,
        llm_call=openrouter_call,
        relevance_threshold=0.4,
    )
    elapsed = time.time() - t0

    print(f"Raw API adapter: {elapsed:.1f}s")
    print(f"\n  Stats:")
    for k, v in result["stats"].items():
        print(f"    {k}: {v}")
    print(f"\n  Sources used:")
    for s in result["sources_used"]:
        print(f"    {s['score']:.2f} [{s['category']}] {s['name']}")
    print(f"\n  Sources excluded:")
    for s in result["sources_excluded"][:5]:
        print(f"    {s['score']:.2f} [{s['category']}] {s['name']}")

    assert "system_prompt" in result, "FAIL: Missing system_prompt"
    assert "hierarchy" in result, "FAIL: Missing hierarchy"
    assert "stats" in result, "FAIL: Missing stats"

    # Test prime_messages
    messages = prime_messages(task, PROJECT_DIR, openrouter_call)
    assert len(messages) == 2, f"FAIL: Expected 2 messages, got {len(messages)}"
    assert messages[0]["role"] == "system", "FAIL: First message should be system"
    assert messages[1]["role"] == "user", "FAIL: Second message should be user"
    print(f"\n  Messages array: {len(messages)} messages ready for API")
    print(f"  System prompt:  {len(messages[0]['content'])} chars")

    print(f"\n  PASS: Raw API adapter works correctly")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("  CONTEXT PRIME — FULL PIPELINE TEST")
    print(f"  Project: {PROJECT_DIR}")
    print(f"  Model:   {OPENROUTER_MODEL} (via OpenRouter)")
    print("=" * 70)

    task = "Improve the context scoring module to batch sources and reduce LLM calls"
    all_passed = True
    timings = {}

    try:
        # Stage tests
        t0 = time.time()
        sources = test_gather()
        timings["gather"] = time.time() - t0

        t0 = time.time()
        relevant = test_score(sources, task)
        timings["score"] = time.time() - t0

        t0 = time.time()
        hierarchy = test_hierarchy(task, relevant)
        timings["hierarchy"] = time.time() - t0

        t0 = time.time()
        primed = test_synthesize(task, hierarchy, relevant)
        timings["synthesize"] = time.time() - t0

        # Full pipeline
        t0 = time.time()
        test_full_pipeline("Fix the memory gathering to handle symlinks correctly")
        timings["full_pipeline"] = time.time() - t0

        # Parallel orchestration
        t0 = time.time()
        test_parallel_orchestration()
        timings["parallel"] = time.time() - t0

        # Raw API adapter
        t0 = time.time()
        test_raw_api_adapter()
        timings["raw_api"] = time.time() - t0

    except Exception as e:
        print(f"\n  FAIL: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # Summary
    separator("SUMMARY")
    total = sum(timings.values())
    for name, t in timings.items():
        status = "PASS"
        print(f"  {status}  {name:20s}  {t:.1f}s")
    print(f"\n  Total: {total:.1f}s")
    print(f"  Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
