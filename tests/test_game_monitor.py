import unittest

from game_monitor import GameMonitor, MonitorConfig, TelemetryEvent


def shot(timestamp_ms, *, hit, visible, blocked):
    return TelemetryEvent(
        timestamp_ms,
        "shot",
        {
            "hit": hit,
            "target_visible": visible,
            "line_of_sight_blocked": blocked,
        },
    )


def aim(timestamp_ms, *, delta, reaction_ms, visible=True, occluded_alignment=False):
    return TelemetryEvent(
        timestamp_ms,
        "aim",
        {
            "angular_delta_deg": delta,
            "reaction_ms": reaction_ms,
            "target_visible": visible,
            "occluded_target_alignment": occluded_alignment,
        },
    )


class GameMonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = GameMonitor()

    def test_normal_telemetry_is_observed_without_escalation(self):
        result = self.monitor.evaluate(
            [
                aim(10, delta=4, reaction_ms=240),
                shot(20, hit=True, visible=True, blocked=False),
            ],
            ace_status="healthy",
        )
        self.assertEqual(result.recommendation, "observe")
        self.assertEqual(result.risk_score, 0)

    def test_one_impossible_hit_is_reviewed_but_not_automatically_kicked(self):
        result = self.monitor.evaluate(
            [shot(10, hit=True, visible=False, blocked=True)]
        )
        self.assertEqual(result.recommendation, "review")
        self.assertEqual(result.evidence["server_confirmed_blocked_hits"], 1)

    def test_repeated_server_confirmed_blocked_hits_recommend_kick(self):
        result = self.monitor.evaluate(
            [
                shot(10, hit=True, visible=False, blocked=True),
                shot(20, hit=True, visible=False, blocked=True),
            ]
        )
        self.assertEqual(result.recommendation, "kick")
        self.assertEqual(result.risk_score, 100)

    def test_repeated_aim_pattern_requires_multiple_events_and_only_reviews(self):
        events = [aim(i * 10, delta=35, reaction_ms=80) for i in range(3)]
        result = self.monitor.evaluate(events)
        self.assertEqual(result.recommendation, "review")
        self.assertEqual(result.evidence["extreme_aim_fast_reaction_events"], 3)
        self.assertNotEqual(result.recommendation, "kick")

    def test_aim_events_without_visible_target_do_not_raise_risk(self):
        events = [aim(i * 10, delta=60, reaction_ms=10, visible=False) for i in range(5)]
        self.assertEqual(self.monitor.evaluate(events).risk_score, 0)

    def test_repeated_server_confirmed_alignment_with_occluded_targets_is_reviewed(self):
        events = [
            aim(
                i * 10,
                delta=2,
                reaction_ms=300,
                visible=False,
                occluded_alignment=True,
            )
            for i in range(3)
        ]
        result = self.monitor.evaluate(events)
        self.assertEqual(result.recommendation, "review")
        self.assertEqual(
            result.evidence["server_confirmed_occluded_target_alignments"],
            3,
        )
        self.assertNotEqual(result.recommendation, "kick")

    def test_ace_integrity_signal_adds_context_but_never_kicks_alone(self):
        result = self.monitor.evaluate([], ace_status="tampered")
        self.assertEqual(result.recommendation, "review")
        self.assertEqual(result.risk_score, 20)

    def test_invalid_input_is_rejected(self):
        invalid_cases = [
            ([shot(10, hit=True, visible=True, blocked=True)], "visible"),
            ([aim(10, delta=181, reaction_ms=10)], "between"),
            ([aim(10, delta=5, reaction_ms=100, occluded_alignment=True)], "cannot be visible"),
            ([shot(20, hit=False, visible=False, blocked=False), shot(10, hit=False, visible=False, blocked=False)], "ordered"),
            ([shot(-1, hit=False, visible=False, blocked=False)], "ordered"),
        ]
        for events, message in invalid_cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.monitor.evaluate(events)

    def test_invalid_ace_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "ace_status"):
            self.monitor.evaluate([], ace_status=[])

    def test_custom_thresholds_are_validated(self):
        with self.assertRaises(ValueError):
            MonitorConfig(review_score=0)
        with self.assertRaises(ValueError):
            MonitorConfig(review_score=True)


if __name__ == "__main__":
    unittest.main()
