from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import ResearchPaperAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous research paper writer")
    parser.add_argument("topic", help="Topic of the paper")
    parser.add_argument("--audience", default="researchers, students, and engineers", help="Target audience")
    parser.add_argument("--output", default="paper_output.md", help="Output file path")
    parser.add_argument("--limit", type=int, default=6, help="Number of literature references to retrieve")
    parser.add_argument("--json", action="store_true", help="Emit a JSON summary of the research plan and evaluation")
    parser.add_argument("--strict", action="store_true", help="Run a stronger quality gate before finalizing the draft")
    args = parser.parse_args()

    agent = ResearchPaperAgent(topic=args.topic, audience=args.audience)
    refs = agent.search_literature(limit=args.limit)
    bundle = agent.generate_paper_bundle(refs)

    if args.strict:
        critique = bundle["critique"]
        if critique["weaknesses"]:
            print("Strict mode: quality warnings found:")
            for item in critique["weaknesses"]:
                print(f"- {item}")

    output_path = Path(args.output)
    output_path.write_text(bundle["paper"], encoding="utf-8")

    print(f"Paper saved to: {output_path.resolve()}")
    print(f"Title: {bundle['title']}")
    print(f"Overall quality score: {bundle['evaluation']['overall']}/100")
    print("Top recommendations:")
    for item in bundle["evaluation"]["recommendations"]:
        print(f"- {item}")

    if args.json:
        payload = {
            "title": bundle["title"],
            "gap_analysis": bundle["gap_analysis"],
            "plan": bundle["plan"],
            "critique": bundle["critique"],
            "evaluation": bundle["evaluation"],
            "references": [
                {
                    "title": ref.title,
                    "authors": ref.authors,
                    "year": ref.year,
                    "venue": ref.venue,
                    "url": ref.url,
                    "summary": ref.summary,
                }
                for ref in bundle["references"]
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
