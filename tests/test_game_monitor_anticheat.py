import tempfile
import unittest
from pathlib import Path

from game_monitor import (
    AntiCheatIngestor,
    EvidenceFusion,
    GameMonitor,
    IntegritySignalStore,
    TelemetryEvent,
    VendorAntiCheatAdapter,
    VerifiedSdkEvent,
)


class TestSdkBridge:
    def __init__(self, event=None):
        self.event = event
        self.calls = 0

    def verify_event(self, raw_event):
        self.calls += 1
        if isinstance(self.event, Exception):
            raise self.event
        return self.event


def verified_event(
    *,
    event_id="evt-1",
    session_id="match-1",
    severity="high",
    vendor="test-ac",
    code="integrity_violation",
):
    return VerifiedSdkEvent(
        vendor=vendor,
        event_id=event_id,
        session_id=session_id,
        occurred_at_ms=1234,
        severity=severity,
        code=code,
    )


class AntiCheatAdapterTests(unittest.TestCase):
    def test_adapter_normalizes_official_sdk_event(self):
        bridge = TestSdkBridge(verified_event())
        signal = VendorAntiCheatAdapter(
            bridge,
            expected_vendor="test-ac",
        ).ingest({"opaque": "provider payload"})
        self.assertEqual(signal.vendor, "test-ac")
        self.assertEqual(signal.risk_score, 75)
        self.assertEqual(bridge.calls, 1)

    def test_adapter_rejects_bad_vendor_and_duplicate_event(self):
        adapter = VendorAntiCheatAdapter(
            TestSdkBridge(verified_event(vendor="unexpected")),
            expected_vendor="test-ac",
        )
        with self.assertRaisesRegex(ValueError, "vendor"):
            adapter.ingest({})

        bridge = TestSdkBridge(verified_event())
        adapter = VendorAntiCheatAdapter(bridge, expected_vendor="test-ac")
        adapter.ingest({})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            adapter.ingest({})

    def test_adapter_surfaces_failed_sdk_verification(self):
        adapter = VendorAntiCheatAdapter(
            TestSdkBridge(RuntimeError("SDK signature check failed")),
            expected_vendor="test-ac",
        )
        with self.assertRaisesRegex(RuntimeError, "signature"):
            adapter.ingest({})

    def test_integrity_signals_persist_and_reload_from_sqlite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = IntegritySignalStore(Path(temp_dir) / "signals.sqlite3")
            try:
                signal = VendorAntiCheatAdapter(
                    TestSdkBridge(verified_event(severity="critical")),
                    expected_vendor="test-ac",
                ).ingest({})
                store.record(signal)
                self.assertEqual(store.list_signals(session_id="match-1"), [signal])
            finally:
                store.close()

    def test_ingestor_verifies_then_persists_signal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = IntegritySignalStore(Path(temp_dir) / "signals.sqlite3")
            try:
                ingestor = AntiCheatIngestor(
                    VendorAntiCheatAdapter(
                        TestSdkBridge(verified_event()),
                        expected_vendor="test-ac",
                    ),
                    store,
                )
                signal = ingestor.ingest({"provider_event": "signed"})
                self.assertEqual(store.list_signals(session_id="match-1"), [signal])
            finally:
                store.close()

    def test_evidence_fusion_combines_independent_signals(self):
        telemetry = GameMonitor().evaluate(
            [
                TelemetryEvent(
                    1,
                    "shot",
                    {
                        "hit": True,
                        "target_visible": False,
                        "line_of_sight_blocked": True,
                    },
                )
            ]
        )
        signal = VendorAntiCheatAdapter(
            TestSdkBridge(verified_event(severity="high")),
            expected_vendor="test-ac",
        ).ingest({})
        report = EvidenceFusion().evaluate(
            session_id="match-1",
            telemetry=telemetry,
            frame_evidence=[{"risk_score": 70, "label": "suspicious"}],
            integrity_signals=[signal],
        )
        self.assertEqual(report.source_count, 3)
        self.assertEqual(report.risk_score, 85)
        self.assertEqual(report.recommendation, "review")
        self.assertEqual(len(report.reasons), 3)

    def test_verified_critical_signal_proposes_kick_but_does_not_execute_it(self):
        signal = VendorAntiCheatAdapter(
            TestSdkBridge(verified_event(severity="critical")),
            expected_vendor="test-ac",
        ).ingest({})
        report = EvidenceFusion().evaluate(
            session_id="match-1",
            integrity_signals=[signal],
        )
        self.assertEqual(report.recommendation, "kick")
        self.assertEqual(report.risk_score, 95)

    def test_fusion_rejects_cross_match_and_bad_scores(self):
        signal = VendorAntiCheatAdapter(
            TestSdkBridge(verified_event(session_id="other-match")),
            expected_vendor="test-ac",
        ).ingest({})
        with self.assertRaisesRegex(ValueError, "does not match"):
            EvidenceFusion().evaluate(
                session_id="match-1",
                integrity_signals=[signal],
            )
        with self.assertRaisesRegex(ValueError, "risk_score"):
            EvidenceFusion().evaluate(
                session_id="match-1",
                frame_evidence=[{"risk_score": float("nan")}],
            )


if __name__ == "__main__":
    unittest.main()
