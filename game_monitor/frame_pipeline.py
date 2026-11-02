"""Privacy-minimizing per-frame analysis and local evidence persistence.

The game/capture integration and visual model are deliberately injected by the
caller. This module never captures the desktop and never persists frame pixels.
"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


MAX_FRAME_BYTES = 4 * 1024 * 1024
MAX_FRAME_DIMENSION = 8192
MAX_REASON_LENGTH = 160
MAX_REASONS = 16


@dataclass(frozen=True)
class GameFrame:
    """One frame delivered by an authorized game-only capture integration."""

    session_id: str
    frame_index: int
    captured_at_ms: int
    width: int
    height: int
    image: bytes
    image_format: str = "jpeg"


@dataclass(frozen=True)
class FrameAssessment:
    """Normalized output from an injected local vision model."""

    model_id: str
    risk_score: float
    confidence: float
    label: str
    reasons: tuple[str, ...] = ()


class FrameAnalyzer(Protocol):
    def analyze(self, frame: GameFrame) -> FrameAssessment:
        """Analyze a single frame locally and return a normalized assessment."""


@dataclass(frozen=True)
class FrameDecision:
    frame_index: int
    risk_score: float
    confidence: float
    label: str
    reasons: tuple[str, ...]
    uncertain: bool
    persisted: bool
    evidence_id: int | None
    inference_ms: float

    def to_dict(self) -> dict[str, object]:
        return {
            "frame_index": self.frame_index,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "label": self.label,
            "reasons": list(self.reasons),
            "uncertain": self.uncertain,
            "persisted": self.persisted,
            "evidence_id": self.evidence_id,
            "inference_ms": round(self.inference_ms, 3),
        }


@dataclass(frozen=True)
class FrameMonitorConfig:
    uncertain_confidence_below: float = 65.0
    review_risk_at_or_above: float = 60.0

    def __post_init__(self) -> None:
        for name, value in (
            ("uncertain_confidence_below", self.uncertain_confidence_below),
            ("review_risk_at_or_above", self.review_risk_at_or_above),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                raise ValueError(f"{name} must be a finite number from 0 to 100")


class LocalEvidenceStore:
    """SQLite store for flagged metadata only; image bytes are never stored."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=5.0,
        )
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=NORMAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS frame_evidence (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                captured_at_ms INTEGER NOT NULL,
                model_id TEXT NOT NULL,
                risk_score REAL NOT NULL,
                confidence REAL NOT NULL,
                label TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,
                UNIQUE(session_id, frame_index)
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_frame_evidence_session "
            "ON frame_evidence(session_id, frame_index)"
        )
        self._connection.commit()

    def record(self, frame: GameFrame, assessment: FrameAssessment) -> int:
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO frame_evidence (
                    session_id, frame_index, captured_at_ms, model_id,
                    risk_score, confidence, label, reasons_json, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    frame.session_id,
                    frame.frame_index,
                    frame.captured_at_ms,
                    assessment.model_id,
                    assessment.risk_score,
                    assessment.confidence,
                    assessment.label,
                    json.dumps(assessment.reasons, ensure_ascii=True),
                    int(time.time() * 1000),
                ),
            )
            self._connection.commit()
            return int(cursor.lastrowid)

    def list_evidence(
        self,
        *,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer from 1 to 1000")
        with self._lock:
            if session_id is None:
                rows = self._connection.execute(
                    """
                    SELECT id, session_id, frame_index, captured_at_ms, model_id,
                           risk_score, confidence, label, reasons_json, created_at_ms
                    FROM frame_evidence ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = self._connection.execute(
                    """
                    SELECT id, session_id, frame_index, captured_at_ms, model_id,
                           risk_score, confidence, label, reasons_json, created_at_ms
                    FROM frame_evidence WHERE session_id = ?
                    ORDER BY frame_index DESC LIMIT ?
                    """,
                    (session_id, limit),
                ).fetchall()
        columns = (
            "id",
            "session_id",
            "frame_index",
            "captured_at_ms",
            "model_id",
            "risk_score",
            "confidence",
            "label",
            "reasons_json",
            "created_at_ms",
        )
        results: list[dict[str, object]] = []
        for row in rows:
            result = dict(zip(columns, row))
            result["reasons"] = json.loads(str(result.pop("reasons_json")))
            results.append(result)
        return results

    def delete_older_than(self, created_at_ms: int) -> int:
        if isinstance(created_at_ms, bool) or not isinstance(created_at_ms, int) or created_at_ms < 0:
            raise ValueError("created_at_ms must be a non-negative integer")
        with self._lock:
            cursor = self._connection.execute(
                "DELETE FROM frame_evidence WHERE created_at_ms < ?",
                (created_at_ms,),
            )
            self._connection.commit()
            return cursor.rowcount

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class LiveFrameMonitor:
    """Analyze every submitted frame and synchronously persist uncertain alerts."""

    def __init__(
        self,
        analyzer: FrameAnalyzer,
        evidence_store: LocalEvidenceStore,
        config: FrameMonitorConfig | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._store = evidence_store
        self._config = config or FrameMonitorConfig()
        self._lock = threading.Lock()
        self._last_frame_by_session: dict[str, tuple[int, int]] = {}

    def process(self, frame: GameFrame) -> FrameDecision:
        self._validate_frame(frame)
        with self._lock:
            previous = self._last_frame_by_session.get(frame.session_id)
            if previous is not None and (
                frame.frame_index <= previous[0] or frame.captured_at_ms < previous[1]
            ):
                raise ValueError("frame indexes must increase and timestamps must not go backwards")

            started = time.perf_counter()
            assessment = self._analyzer.analyze(frame)
            inference_ms = (time.perf_counter() - started) * 1000
            self._validate_assessment(assessment)

            uncertain = (
                assessment.label != "normal"
                or assessment.confidence < self._config.uncertain_confidence_below
                or assessment.risk_score >= self._config.review_risk_at_or_above
            )
            evidence_id = self._store.record(frame, assessment) if uncertain else None
            self._last_frame_by_session[frame.session_id] = (
                frame.frame_index,
                frame.captured_at_ms,
            )
            return FrameDecision(
                frame_index=frame.frame_index,
                risk_score=assessment.risk_score,
                confidence=assessment.confidence,
                label=assessment.label,
                reasons=assessment.reasons,
                uncertain=uncertain,
                persisted=evidence_id is not None,
                evidence_id=evidence_id,
                inference_ms=inference_ms,
            )

    @staticmethod
    def _validate_frame(frame: GameFrame) -> None:
        if not isinstance(frame, GameFrame):
            raise ValueError("frame must be a GameFrame")
        if not isinstance(frame.session_id, str) or not frame.session_id.strip() or len(frame.session_id) > 128:
            raise ValueError("session_id must be a non-empty pseudonymous identifier")
        for name, value in (
            ("frame_index", frame.frame_index),
            ("captured_at_ms", frame.captured_at_ms),
            ("width", frame.width),
            ("height", frame.height),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if frame.frame_index < 0 or frame.captured_at_ms < 0:
            raise ValueError("frame index and timestamp must not be negative")
        if not 1 <= frame.width <= MAX_FRAME_DIMENSION or not 1 <= frame.height <= MAX_FRAME_DIMENSION:
            raise ValueError("frame dimensions are outside the allowed range")
        if not isinstance(frame.image, bytes) or not 0 < len(frame.image) <= MAX_FRAME_BYTES:
            raise ValueError("frame image must be bytes no larger than 4 MiB")
        if not isinstance(frame.image_format, str) or frame.image_format not in {
            "jpeg",
            "png",
            "gray8",
        }:
            raise ValueError("frame image_format must be jpeg, png, or gray8")
        if frame.image_format == "gray8" and len(frame.image) != frame.width * frame.height:
            raise ValueError("gray8 frame byte length must match its dimensions")

    @staticmethod
    def _validate_assessment(assessment: FrameAssessment) -> None:
        if not isinstance(assessment, FrameAssessment):
            raise ValueError("analyzer must return FrameAssessment")
        if not isinstance(assessment.model_id, str) or not assessment.model_id.strip():
            raise ValueError("assessment model_id must be non-empty")
        for name, value in (
            ("risk_score", assessment.risk_score),
            ("confidence", assessment.confidence),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                raise ValueError(f"assessment {name} must be a finite number from 0 to 100")
        if assessment.label not in {"normal", "suspicious", "uncertain"}:
            raise ValueError("assessment label must be normal, suspicious, or uncertain")
        if (
            not isinstance(assessment.reasons, tuple)
            or len(assessment.reasons) > MAX_REASONS
            or any(
                not isinstance(reason, str)
                or not reason.strip()
                or len(reason) > MAX_REASON_LENGTH
                for reason in assessment.reasons
            )
        ):
            raise ValueError("assessment reasons must be up to 16 short non-empty strings")
