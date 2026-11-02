"""Vendor-neutral adapter and evidence fusion for authorized anti-cheat SDKs.

The adapter consumes events only after the vendor's official SDK has
authenticated them. It does not inspect, inject into, or communicate with any
anti-cheat process or driver.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Protocol, Sequence

from .core import MonitorResult, Recommendation


Severity = Literal["info", "low", "medium", "high", "critical"]
MAX_EVENT_ID_LENGTH = 128
MAX_SIGNAL_CODE_LENGTH = 96
MAX_VENDOR_LENGTH = 64

_SEVERITY_SCORE: dict[Severity, int] = {
    "info": 0,
    "low": 20,
    "medium": 45,
    "high": 75,
    "critical": 95,
}
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


@dataclass(frozen=True)
class VerifiedSdkEvent:
    """Normalized result of a successful official SDK verification step.

    Construct this only inside a vendor SDK bridge after signature/authenticity
    and freshness checks succeed. A client-supplied JSON field is not proof.
    """

    vendor: str
    event_id: str
    session_id: str
    occurred_at_ms: int
    severity: Severity
    code: str


@dataclass(frozen=True)
class IntegritySignal:
    vendor: str
    event_id: str
    session_id: str
    occurred_at_ms: int
    severity: Severity
    code: str
    risk_score: int

    def to_dict(self) -> dict[str, object]:
        return {
            "vendor": self.vendor,
            "event_id": self.event_id,
            "session_id": self.session_id,
            "occurred_at_ms": self.occurred_at_ms,
            "severity": self.severity,
            "code": self.code,
            "risk_score": self.risk_score,
        }


class OfficialSdkBridge(Protocol):
    """Vendor-specific SDK wrapper that authenticates and normalizes events."""

    def verify_event(self, raw_event: object) -> VerifiedSdkEvent:
        """Verify signature/source/freshness, then return a normalized event."""


class VendorAntiCheatAdapter:
    """Normalize official SDK callbacks and reject duplicate/stale identifiers."""

    def __init__(
        self,
        bridge: OfficialSdkBridge,
        *,
        expected_vendor: str,
        max_seen_event_ids: int = 20_000,
    ) -> None:
        _validate_identifier("expected_vendor", expected_vendor, MAX_VENDOR_LENGTH)
        if (
            isinstance(max_seen_event_ids, bool)
            or not isinstance(max_seen_event_ids, int)
            or max_seen_event_ids < 1
        ):
            raise ValueError("max_seen_event_ids must be a positive integer")
        self._bridge = bridge
        self._vendor = expected_vendor
        self._max_seen = max_seen_event_ids
        self._seen: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def ingest(self, raw_event: object) -> IntegritySignal:
        event = self._bridge.verify_event(raw_event)
        if not isinstance(event, VerifiedSdkEvent):
            raise ValueError("official SDK bridge must return VerifiedSdkEvent")
        if event.vendor != self._vendor:
            raise ValueError("verified event vendor does not match configured vendor")
        _validate_identifier("event_id", event.event_id, MAX_EVENT_ID_LENGTH)
        _validate_identifier("session_id", event.session_id, MAX_EVENT_ID_LENGTH)
        _validate_identifier("vendor", event.vendor, MAX_VENDOR_LENGTH)
        _validate_identifier("code", event.code, MAX_SIGNAL_CODE_LENGTH)
        if (
            isinstance(event.occurred_at_ms, bool)
            or not isinstance(event.occurred_at_ms, int)
            or event.occurred_at_ms < 0
        ):
            raise ValueError("occurred_at_ms must be a non-negative integer")
        if not isinstance(event.severity, str) or event.severity not in _SEVERITY_SCORE:
            raise ValueError("unsupported anti-cheat severity")

        identity = (event.session_id, event.event_id)
        with self._lock:
            if identity in self._seen:
                raise ValueError("duplicate anti-cheat event")
            if len(self._seen) >= self._max_seen:
                raise RuntimeError("anti-cheat event deduplication capacity reached")
            self._seen.add(identity)

        return IntegritySignal(
            vendor=event.vendor,
            event_id=event.event_id,
            session_id=event.session_id,
            occurred_at_ms=event.occurred_at_ms,
            severity=event.severity,
            code=event.code,
            risk_score=_SEVERITY_SCORE[event.severity],
        )

    def release(self, signal: IntegritySignal) -> None:
        """Allow safe retry when downstream durable storage fails."""
        with self._lock:
            self._seen.discard((signal.session_id, signal.event_id))

    def close_session(self, session_id: str) -> None:
        _validate_identifier("session_id", session_id, MAX_EVENT_ID_LENGTH)
        with self._lock:
            self._seen = {
                identity for identity in self._seen if identity[0] != session_id
            }


class AntiCheatIngestor:
    """Authenticate via the vendor bridge, normalize, and durably store signals."""

    def __init__(
        self,
        adapter: VendorAntiCheatAdapter,
        store: "IntegritySignalStore",
    ) -> None:
        self._adapter = adapter
        self._store = store

    def ingest(self, raw_event: object) -> IntegritySignal:
        signal = self._adapter.ingest(raw_event)
        try:
            self._store.record(signal)
        except sqlite3.Error:
            self._adapter.release(signal)
            raise
        return signal


def _validate_identifier(name: str, value: object, max_length: int) -> None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= max_length
        or _SAFE_IDENTIFIER.fullmatch(value) is None
    ):
        raise ValueError(f"{name} must be a safe identifier of 1-{max_length} characters")


class IntegritySignalStore:
    """Local SQLite persistence for normalized anti-cheat signals."""

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
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS anticheat_signals (
                id INTEGER PRIMARY KEY,
                vendor TEXT NOT NULL,
                event_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                occurred_at_ms INTEGER NOT NULL,
                severity TEXT NOT NULL,
                code TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                created_at_ms INTEGER NOT NULL,
                UNIQUE(vendor, session_id, event_id)
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_anticheat_session "
            "ON anticheat_signals(session_id, occurred_at_ms)"
        )
        self._connection.commit()

    def record(self, signal: IntegritySignal) -> int:
        if not isinstance(signal, IntegritySignal):
            raise ValueError("signal must be an IntegritySignal")
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO anticheat_signals (
                    vendor, event_id, session_id, occurred_at_ms, severity,
                    code, risk_score, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.vendor,
                    signal.event_id,
                    signal.session_id,
                    signal.occurred_at_ms,
                    signal.severity,
                    signal.code,
                    signal.risk_score,
                    int(time.time() * 1000),
                ),
            )
            self._connection.commit()
            return int(cursor.lastrowid)

    def list_signals(
        self,
        *,
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[IntegritySignal]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer from 1 to 1000")
        with self._lock:
            if session_id is None:
                rows = self._connection.execute(
                    """
                    SELECT vendor, event_id, session_id, occurred_at_ms,
                           severity, code, risk_score
                    FROM anticheat_signals ORDER BY id DESC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = self._connection.execute(
                    """
                    SELECT vendor, event_id, session_id, occurred_at_ms,
                           severity, code, risk_score
                    FROM anticheat_signals WHERE session_id = ?
                    ORDER BY occurred_at_ms DESC LIMIT ?
                    """,
                    (session_id, limit),
                ).fetchall()
        return [IntegritySignal(*row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._connection.close()


@dataclass(frozen=True)
class FusedRiskReport:
    session_id: str
    risk_score: int
    recommendation: Recommendation
    source_count: int
    reasons: tuple[str, ...]
    source_scores: Mapping[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "risk_score": self.risk_score,
            "recommendation": self.recommendation,
            "source_count": self.source_count,
            "reasons": list(self.reasons),
            "source_scores": dict(self.source_scores),
        }


class EvidenceFusion:
    """Combine independent evidence sources without executing sanctions."""

    def __init__(self, *, review_score: int = 40, kick_score: int = 90) -> None:
        for name, value in (("review_score", review_score), ("kick_score", kick_score)):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= 100
            ):
                raise ValueError(f"{name} must be an integer from 1 to 100")
        if review_score > kick_score:
            raise ValueError("review_score must not exceed kick_score")
        self.review_score = review_score
        self.kick_score = kick_score

    def evaluate(
        self,
        *,
        session_id: str,
        telemetry: MonitorResult | None = None,
        frame_evidence: Sequence[Mapping[str, object]] = (),
        integrity_signals: Sequence[IntegritySignal] = (),
    ) -> FusedRiskReport:
        _validate_identifier("session_id", session_id, MAX_EVENT_ID_LENGTH)
        source_scores: dict[str, int] = {}
        reasons: list[str] = []

        if telemetry is not None:
            if (
                isinstance(telemetry.risk_score, bool)
                or not isinstance(telemetry.risk_score, int)
                or not 0 <= telemetry.risk_score <= 100
            ):
                raise ValueError("telemetry risk_score must be an integer from 0 to 100")
            source_scores["server_telemetry"] = telemetry.risk_score
            reasons.extend(f"telemetry:{reason}" for reason in telemetry.reasons)

        if not isinstance(frame_evidence, Sequence) or isinstance(frame_evidence, (str, bytes)):
            raise ValueError("frame_evidence must be a sequence of evidence mappings")
        valid_frame_scores: list[int] = []
        for evidence in frame_evidence:
            if not isinstance(evidence, Mapping):
                raise ValueError("frame evidence entries must be mappings")
            value = evidence.get("risk_score")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                raise ValueError("frame evidence risk_score must be finite and between 0 and 100")
            valid_frame_scores.append(round(value))
            label = evidence.get("label")
            if isinstance(label, str) and label in {"suspicious", "uncertain"}:
                reasons.append(f"visual:{label}")
        if valid_frame_scores:
            source_scores["visual_frames"] = max(valid_frame_scores)

        if not isinstance(integrity_signals, Sequence) or isinstance(
            integrity_signals, (str, bytes)
        ):
            raise ValueError("integrity_signals must be a sequence")
        for signal in integrity_signals:
            if not isinstance(signal, IntegritySignal):
                raise ValueError("integrity_signals must contain IntegritySignal values")
            if signal.session_id != session_id:
                raise ValueError("integrity signal session_id does not match report")
            if (
                not isinstance(signal.vendor, str)
                or not isinstance(signal.code, str)
                or not isinstance(signal.severity, str)
                or isinstance(signal.risk_score, bool)
                or not isinstance(signal.risk_score, int)
                or not 0 <= signal.risk_score <= 100
            ):
                raise ValueError("integrity signal fields are invalid")
            source_scores[f"anticheat:{signal.vendor}"] = max(
                source_scores.get(f"anticheat:{signal.vendor}", 0),
                signal.risk_score,
            )
            reasons.append(f"anticheat:{signal.vendor}:{signal.code}")

        score_values = list(source_scores.values())
        highest = max(score_values, default=0)
        corroborating_sources = sum(score >= self.review_score for score in score_values)
        score = min(100, highest + max(0, corroborating_sources - 1) * 5)
        if score >= self.kick_score:
            recommendation: Recommendation = "kick"
        elif score >= self.review_score:
            recommendation = "review"
        else:
            recommendation = "observe"

        return FusedRiskReport(
            session_id=session_id,
            risk_score=score,
            recommendation=recommendation,
            source_count=len(source_scores),
            reasons=tuple(dict.fromkeys(reasons)),
            source_scores=source_scores,
        )
