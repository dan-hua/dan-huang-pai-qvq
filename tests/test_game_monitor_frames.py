import sqlite3
import tempfile
import unittest
from pathlib import Path

from game_monitor import (
    FrameAssessment,
    FrameMonitorConfig,
    GameFrame,
    LiveFrameMonitor,
    LocalEvidenceStore,
)


class StaticAnalyzer:
    def __init__(self, assessment):
        self.assessment = assessment
        self.seen = []

    def analyze(self, frame):
        self.seen.append(frame.frame_index)
        return self.assessment


def frame(index, *, session="match-abc", timestamp=None):
    return GameFrame(
        session_id=session,
        frame_index=index,
        captured_at_ms=index * 16 if timestamp is None else timestamp,
        width=1920,
        height=1080,
        image=b"frame-bytes",
    )


class FramePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "evidence.sqlite"
        self.store = LocalEvidenceStore(self.database)

    def tearDown(self):
        self.store.close()
        self.temp_dir.cleanup()

    def test_analyzes_every_frame_and_only_persists_uncertain_findings(self):
        analyzer = StaticAnalyzer(
            FrameAssessment(
                model_id="local-test-model",
                risk_score=15,
                confidence=90,
                label="normal",
            )
        )
        monitor = LiveFrameMonitor(analyzer, self.store)
        decisions = [monitor.process(frame(i)) for i in range(3)]
        self.assertEqual(analyzer.seen, [0, 1, 2])
        self.assertTrue(all(not decision.persisted for decision in decisions))
        self.assertEqual(self.store.list_evidence(), [])

    def test_uncertain_frame_is_immediately_persisted_without_pixels(self):
        analyzer = StaticAnalyzer(
            FrameAssessment(
                model_id="local-test-model",
                risk_score=12,
                confidence=42,
                label="uncertain",
                reasons=("low_visual_confidence",),
            )
        )
        decision = LiveFrameMonitor(analyzer, self.store).process(frame(1))
        self.assertTrue(decision.uncertain)
        self.assertTrue(decision.persisted)
        evidence = self.store.list_evidence()[0]
        self.assertEqual(evidence["frame_index"], 1)
        self.assertEqual(evidence["reasons"], ["low_visual_confidence"])
        self.assertNotIn("image", evidence)
        connection = sqlite3.connect(self.database)
        try:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(frame_evidence)")
            }
        finally:
            connection.close()
        self.assertNotIn("image", columns)

    def test_high_risk_frame_is_persisted_even_at_high_confidence(self):
        analyzer = StaticAnalyzer(
            FrameAssessment("local-test-model", 80, 95, "suspicious", ("aim_pattern",))
        )
        decision = LiveFrameMonitor(analyzer, self.store).process(frame(1))
        self.assertEqual(decision.evidence_id, 1)
        self.assertEqual(len(self.store.list_evidence()), 1)

    def test_frame_order_is_enforced_per_session(self):
        monitor = LiveFrameMonitor(
            StaticAnalyzer(FrameAssessment("model", 1, 99, "normal")),
            self.store,
        )
        monitor.process(frame(3))
        with self.assertRaisesRegex(ValueError, "frame indexes"):
            monitor.process(frame(2))
        monitor.process(frame(1, session="another-match"))

    def test_invalid_frame_and_model_outputs_are_rejected(self):
        bad_frame = GameFrame("session", 0, 0, 1920, 1080, b"")
        with self.assertRaisesRegex(ValueError, "image"):
            LiveFrameMonitor(
                StaticAnalyzer(FrameAssessment("model", 1, 99, "normal")),
                self.store,
            ).process(bad_frame)
        with self.assertRaisesRegex(ValueError, "risk_score"):
            LiveFrameMonitor(
                StaticAnalyzer(FrameAssessment("model", float("nan"), 99, "normal")),
                self.store,
            ).process(frame(0))

    def test_config_uses_percentage_scale_and_rejects_bad_threshold(self):
        self.assertEqual(FrameMonitorConfig().uncertain_confidence_below, 65.0)
        with self.assertRaises(ValueError):
            FrameMonitorConfig(uncertain_confidence_below=101)


if __name__ == "__main__":
    unittest.main()
