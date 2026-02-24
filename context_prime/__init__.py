"""Context Prime — Proactive context synthesis for coding agents."""

__version__ = "0.1.0"

from context_prime.core.gather import gather_all
from context_prime.core.score import score_relevance, filter_relevant
from context_prime.core.synthesize import synthesize_context
from context_prime.core.hierarchy import infer_hierarchy

__all__ = [
    "gather_all",
    "score_relevance",
    "filter_relevant",
    "synthesize_context",
    "infer_hierarchy",
]
