import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from game_monitor import LiveFrameMonitor, LocalEvidenceStore, OpenCvMotionAnalyzer
from game_monitor.video import analyze_video


@unittest.skipIf(cv2 is None, "optional OpenCV dependency is not installed")
class VideoMonitorTests(unittest.TestCase):
    def test_video_is_processed_frame_by_frame_and_alerts_are_persisted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "sample.avi"
            database_path = Path(temp_dir) / "evidence.sqlite3"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                20.0,
                (64, 64),
            )
            self.assertTrue(writer.isOpened())
            try:
                for value in (0, 0, 255, 255, 0):
                    writer.write(np.full((64, 64, 3), value, dtype=np.uint8))
            finally:
                writer.release()

            store = LocalEvidenceStore(database_path)
            try:
                monitor = LiveFrameMonitor(
                    OpenCvMotionAnalyzer(change_threshold=0.1),
                    store,
                )
                result = analyze_video(video_path, monitor, session_id="test-session")
                evidence = store.list_evidence(session_id="test-session")
            finally:
                store.close()

            self.assertEqual(result.frames_processed, 5)
            self.assertGreaterEqual(result.alerts_persisted, 1)
            self.assertGreater(result.processing_fps, 0)
            self.assertEqual(len(evidence), result.alerts_persisted)
            self.assertNotIn("image", evidence[0])

    def test_video_command_returns_summary_and_evidence_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "sample.avi"
            database_path = Path(temp_dir) / "evidence.sqlite3"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                20.0,
                (64, 64),
            )
            self.assertTrue(writer.isOpened())
            try:
                for value in (0, 0, 255):
                    writer.write(np.full((64, 64, 3), value, dtype=np.uint8))
            finally:
                writer.release()

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "game_monitor",
                    "--video",
                    str(video_path),
                    "--db",
                    str(database_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["frames_processed"], 3)
            self.assertGreaterEqual(report["alerts_persisted"], 1)
            self.assertEqual(report["recommendation"], "review")
            self.assertTrue(report["evidence"])

    def test_missing_video_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = LocalEvidenceStore(Path(temp_dir) / "evidence.sqlite3")
            try:
                with self.assertRaises(FileNotFoundError):
                    analyze_video(
                        Path(temp_dir) / "missing.mp4",
                        LiveFrameMonitor(OpenCvMotionAnalyzer(), store),
                    )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
