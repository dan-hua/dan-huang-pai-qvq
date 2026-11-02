"""Local video-file ingestion for privacy-preserving frame analysis."""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .frame_pipeline import (
    FrameAssessment,
    GameFrame,
    LiveFrameMonitor,
    LocalEvidenceStore,
)


@dataclass(frozen=True)
class VideoRunResult:
    session_id: str
    frames_processed: int
    alerts_persisted: int
    highest_risk: float
    recommendation: str
    duration_seconds: float
    processing_fps: float

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "frames_processed": self.frames_processed,
            "alerts_persisted": self.alerts_persisted,
            "highest_risk": self.highest_risk,
            "recommendation": self.recommendation,
            "duration_seconds": round(self.duration_seconds, 3),
            "processing_fps": round(self.processing_fps, 2),
        }


class OpenCvMotionAnalyzer:
    """Fast visual-change baseline; flags abrupt motion for review, not cheating."""

    model_id = "opencv-motion-baseline-v1"

    def __init__(self, *, change_threshold: float = 0.22) -> None:
        if isinstance(change_threshold, bool) or not isinstance(change_threshold, (int, float)):
            raise ValueError("change_threshold must be a number from 0 to 1")
        if not 0 < change_threshold <= 1:
            raise ValueError("change_threshold must be greater than 0 and at most 1")
        self.change_threshold = float(change_threshold)
        self._previous_gray = None

    def analyze(self, frame: GameFrame) -> FrameAssessment:
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError(
                "Video analysis requires OpenCV. Install with: "
                "python -m pip install -r requirements-game-monitor.txt"
            ) from error

        if frame.image_format == "gray8":
            image = np.frombuffer(frame.image, dtype=np.uint8).reshape(
                (frame.height, frame.width)
            )
        else:
            encoded = np.frombuffer(frame.image, dtype=np.uint8)
            image = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)
        if image is None or image.shape != (frame.height, frame.width):
            raise ValueError(f"frame {frame.frame_index} image data is invalid")
        reduced = cv2.resize(image, (320, 180), interpolation=cv2.INTER_AREA)
        if self._previous_gray is None:
            self._previous_gray = reduced
            return FrameAssessment(
                model_id=self.model_id,
                risk_score=0,
                confidence=50,
                label="uncertain",
                reasons=("baseline_frame_no_temporal_context",),
            )

        difference = cv2.absdiff(reduced, self._previous_gray)
        change_ratio = float(np.mean(difference)) / 255.0
        self._previous_gray = reduced
        if change_ratio >= self.change_threshold:
            severity = min(
                100.0,
                60.0 + 40.0 * (change_ratio - self.change_threshold)
                / (1.0 - self.change_threshold),
            )
            return FrameAssessment(
                model_id=self.model_id,
                risk_score=severity,
                confidence=55,
                label="uncertain",
                reasons=("abrupt_visual_change_possible_camera_motion_or_effect",),
            )
        return FrameAssessment(
            model_id=self.model_id,
            risk_score=0,
            confidence=80,
            label="normal",
        )


def iter_video_frames(
    video_path: str | Path,
    *,
    session_id: str | None = None,
) -> Iterator[GameFrame]:
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError(
            "Video analysis requires OpenCV. Install with: "
            "python -m pip install -r requirements-game-monitor.txt"
        ) from error

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"video file not found: {path}")
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise ValueError(f"unable to open video file: {path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    if not math.isfinite(fps) or fps <= 0:
        fps = 30.0
    source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if source_width <= 0 or source_height <= 0:
        capture.release()
        raise ValueError("video has invalid dimensions")
    identifier = session_id or uuid.uuid4().hex

    try:
        index = 0
        while True:
            success, image = capture.read()
            if not success:
                break
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(
                gray,
                (320, 180),
                interpolation=cv2.INTER_AREA,
            )
            yield GameFrame(
                session_id=identifier,
                frame_index=index,
                captured_at_ms=round(index * 1000 / fps),
                width=320,
                height=180,
                image=gray.tobytes(),
                image_format="gray8",
            )
            index += 1
    finally:
        capture.release()


def analyze_video(
    video_path: str | Path,
    monitor: LiveFrameMonitor,
    *,
    session_id: str | None = None,
    evidence_store: LocalEvidenceStore | None = None,
) -> VideoRunResult:
    identifier = session_id or uuid.uuid4().hex
    start = time.perf_counter()
    processed = 0
    alerts = 0
    for frame in iter_video_frames(video_path, session_id=identifier):
        decision = monitor.process(frame)
        processed += 1
        alerts += int(decision.persisted)
    elapsed = time.perf_counter() - start
    evidence_rows = (
        evidence_store.list_evidence(session_id=identifier, limit=1000)
        if evidence_store is not None
        else []
    )
    highest_risk = max(
        (float(row["risk_score"]) for row in evidence_rows),
        default=0.0,
    )
    return VideoRunResult(
        session_id=identifier,
        frames_processed=processed,
        alerts_persisted=alerts,
        highest_risk=highest_risk,
        recommendation="review" if highest_risk >= 60 else "observe",
        duration_seconds=elapsed,
        processing_fps=processed / elapsed if elapsed > 0 else 0,
    )
