import json
import subprocess
import sys
import unittest
from io import BytesIO
from pathlib import Path

from game_monitor.__main__ import read_events


ROOT = Path(__file__).resolve().parents[1]


class GameMonitorCliTests(unittest.TestCase):
    def test_reads_jsonl_events(self):
        stream = BytesIO(
            b'{"timestamp_ms":1,"kind":"shot","data":'
            b'{"hit":false,"target_visible":false,"line_of_sight_blocked":false}}\n'
        )
        events = read_events(stream)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "shot")

    def test_rejects_malformed_and_unexpected_jsonl(self):
        for line in ('{bad json}\n', '{"timestamp_ms":1}\n'):
            with self.subTest(line=line):
                with self.assertRaises(ValueError):
                    read_events(BytesIO(line.encode("utf-8")))

    def test_rejects_oversized_line_with_bounded_read(self):
        stream = BytesIO(b"x" * (16 * 1024 + 1024))
        with self.assertRaisesRegex(ValueError, "size limit"):
            read_events(stream)
        self.assertEqual(stream.tell(), 16 * 1024 + 1)

    def test_cli_prints_report_for_sample_file(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "game_monitor",
                "--input",
                str(ROOT / "examples" / "game_telemetry.jsonl"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["recommendation"], "review")
        self.assertEqual(report["risk_score"], 50)

    def test_cli_rejects_invalid_record_with_nonzero_exit(self):
        completed = subprocess.run(
            [sys.executable, "-m", "game_monitor"],
            cwd=ROOT,
            input='{"timestamp_ms":true,"kind":"shot","data":{}}\n',
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("timestamp_ms", completed.stderr)


if __name__ == "__main__":
    unittest.main()
