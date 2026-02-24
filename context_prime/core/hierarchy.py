"""Outcome hierarchy inference — understand the goal beyond the literal task."""


HIERARCHY_PROMPT = """Analyze this task and infer the outcome hierarchy.

## Task
{task}

## Project Context
{project_context}

## Instructions
Infer three levels of outcomes. The user stated the immediate task, but
there's usually a mid-term goal it serves and a final outcome beyond that.

If you can't confidently infer higher levels from the context, say so
honestly rather than fabricating goals.

Return as JSON:
```json
{{
  "immediate": "The specific task to complete right now",
  "midterm": "The milestone or goal this task contributes to (or null if unclear)",
  "final": "The ultimate outcome this work serves (or null if unclear)",
  "reasoning": "Brief explanation of how you inferred the hierarchy",
  "confidence": "high|medium|low"
}}
```

Return ONLY the JSON, no other text."""


def build_hierarchy_prompt(task: str, project_context: str) -> str:
    """Build the prompt for outcome hierarchy inference."""
    # Truncate project context if too long
    if len(project_context) > 3000:
        project_context = project_context[:3000] + "\n... [truncated]"
    return HIERARCHY_PROMPT.format(task=task, project_context=project_context)


def parse_hierarchy(response_text: str) -> dict:
    """Parse LLM response into hierarchy dict."""
    import json
    import re

    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        return {
            "immediate": "Unknown",
            "midterm": None,
            "final": None,
            "reasoning": "Failed to parse hierarchy",
            "confidence": "low",
        }

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return {
            "immediate": "Unknown",
            "midterm": None,
            "final": None,
            "reasoning": "Failed to parse hierarchy",
            "confidence": "low",
        }


def infer_hierarchy(
    task: str,
    project_context: str,
    llm_call: callable,
) -> dict:
    """Infer the outcome hierarchy for a task.

    Args:
        task: The user's task description.
        project_context: Synthesized project context (README, config, etc.)
        llm_call: A callable(prompt: str) -> str that calls an LLM.

    Returns:
        Dict with keys: immediate, midterm, final, reasoning, confidence.
    """
    prompt = build_hierarchy_prompt(task, project_context)
    response = llm_call(prompt)
    return parse_hierarchy(response)
