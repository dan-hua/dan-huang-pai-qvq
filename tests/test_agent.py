import unittest

from paper_agent.core import ResearchPaperAgent


class TestResearchPaperAgent(unittest.TestCase):
    def test_outline_contains_expected_sections(self):
        agent = ResearchPaperAgent("AI agents for software engineering")
        refs = agent.search_literature(limit=2)
        outline = agent.build_outline(refs)
        self.assertIn("Introduction", "\n".join(outline))
        self.assertIn("Methodology and System Design", outline)

    def test_draft_is_nonempty(self):
        agent = ResearchPaperAgent("AI agents for software engineering")
        paper = agent.draft_paper(references=agent.search_literature(limit=2))
        self.assertIn("#", paper)
        self.assertGreater(len(paper), 1200)

    def test_research_plan_gap_analysis_and_evaluation_are_structured(self):
        agent = ResearchPaperAgent("AI agents for software engineering")
        bundle = agent.generate_paper_bundle()
        self.assertIn("research_questions", bundle["plan"])
        self.assertIn("gap", bundle["gap_analysis"])
        self.assertIn("overall", bundle["evaluation"])
        self.assertGreater(bundle["evaluation"]["overall"], 80)


if __name__ == "__main__":
    unittest.main()
