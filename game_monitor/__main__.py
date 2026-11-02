"""Command-line entry point for evaluating one match's telemetry JSONL."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import BinaryIO

from .core import (
    MAX_EVENTS_PER_EVALUATION,
    GameMonitor,
    TelemetryEvent,
)
from .frame_pipeline import LiveFrameMonitor, LocalEvidenceStore

MAX_EVENT_LINE_BYTES = 16 * 1024


def read_events(stream: BinaryIO) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    line_number = 0
    while True:
        raw_line = stream.readline(MAX_EVENT_LINE_BYTES + 1)
        if not raw_line:
            break
        line_number += 1
        if len(raw_line) > MAX_EVENT_LINE_BYTES:
            raise ValueError(f"line {line_number}: event exceeds size limit")
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"line {line_number}: input must be UTF-8") from error
        if not line.strip():
            continue
        if len(events) >= MAX_EVENTS_PER_EVALUATION:
            raise ValueError(
                f"input exceeds the {MAX_EVENTS_PER_EVALUATION}-event limit"
            )
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"line {line_number}: invalid JSON: {error.msg}") from error
        if not isinstance(record, dict) or set(record) != {
            "timestamp_ms",
            "kind",
            "data",
        }:
            raise ValueError(
                f"line {line_number}: expected timestamp_ms, kind, and data fields"
            )
        events.append(
            TelemetryEvent(
                timestamp_ms=record["timestamp_ms"],
                kind=record["kind"],
                data=record["data"],
            )
        )
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze match telemetry or a local gameplay video."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--input",
        default=None,
        metavar="PATH",
        help="UTF-8 JSONL telemetry file; use - for standard input",
    )
    source.add_argument(
        "--video",
        metavar="PATH",
        help="analyze a local video file frame by frame (requires OpenCV)",
    )
    parser.add_argument(
        "--ace-status",
        choices=("healthy", "unavailable", "tampered"),
        default="unavailable",
        help="ACE status from an authorized integration only (default: unavailable)",
    )
    parser.add_argument(
        "--db",
        default="monitor-evidence.sqlite3",
        metavar="PATH",
        help="local SQLite evidence database for video findings",
    )
    parser.add_argument(
        "--session-id",
        help="pseudonymous session identifier; generated randomly if omitted",
    )
    parser.add_argument(
        "--motion-threshold",
        type=float,
        default=0.22,
        metavar="0..1",
        help="visual-change threshold for the demo analyzer (default: 0.22)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=7,
        metavar="DAYS",
        help="remove older local evidence at startup (default: 7 days; 0 disables cleanup)",
    )
    args = parser.parse_args(argv)

    try:
        if args.video:
            from .video import OpenCvMotionAnalyzer, analyze_video

            if args.retention_days < 0:
                raise ValueError("--retention-days must not be negative")
            store = LocalEvidenceStore(args.db)
            try:
                if args.retention_days:
                    cutoff_ms = int(
                        (time.time() - args.retention_days * 24 * 60 * 60) * 1000
                    )
                    store.delete_older_than(cutoff_ms)
                monitor = LiveFrameMonitor(
                    OpenCvMotionAnalyzer(change_threshold=args.motion_threshold),
                    store,
                )
                result = analyze_video(
                    args.video,
                    monitor,
                    session_id=args.session_id,
                    evidence_store=store,
                )
                report = result.to_dict()
                report["evidence"] = store.list_evidence(
                    session_id=result.session_id,
                    limit=1000,
                )
            finally:
                store.close()
        elif args.input is None or args.input == "-":
            events = read_events(sys.stdin.buffer)
            report = GameMonitor().evaluate(
                events,
                ace_status=args.ace_status,
            ).to_dict()
        else:
            with Path(args.input).open("rb") as stream:
                events = read_events(stream)
            report = GameMonitor().evaluate(
                events,
                ace_status=args.ace_status,
            ).to_dict()
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as error:
        print(f"game-monitor: {error}", file=sys.stderr)
        return 2
    except RuntimeError as error:
        print(f"game-monitor: {error}", file=sys.stderr)
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
