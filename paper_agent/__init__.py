"""Autonomous research paper writing agent."""

from .core import PaperReference, ResearchPlan, ResearchPaperAgent, generate_paper, generate_paper_bundle

__all__ = [
    "PaperReference",
    "ResearchPlan",
    "ResearchPaperAgent",
    "generate_paper",
    "generate_paper_bundle",
]
