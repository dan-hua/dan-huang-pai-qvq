"""Explainable risk scoring for trusted, game-generated telemetry.

This module does not inspect a player's computer, game process, or ACE. A game
server can pass validated events here and, with an authorized integration,
include an ACE integrity status as an additional signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Sequence


AceStatus = Literal["healthy", "unavailable", "tampered"]
EventKind = Literal["aim", "shot"]
Recommendation = Literal["observe", "review", "kick"]

MAX_EVENTS_PER_EVALUATION = 10_000


@dataclass(frozen=True)
class TelemetryEvent:
    """A normalized event produced by the game server, not trusted client input."""

    timestamp_ms: int
    kind: EventKind
    data: Mapping[str, Any]


@dataclass(frozen=True)
class MonitorConfig:
    """Thresholds for transparent baseline scoring; tune against game data."""

    extreme_aim_delta_deg: float = 30.0
    fast_reaction_ms: int = 100
    repeated_aim_anomalies: int = 3
    repeated_occluded_alignments: int = 3
    review_score: int = 20
    confirmed_blocked_hits_for_kick: int = 2

    def __post_init__(self) -> None:
        if (
            isinstance(self.extreme_aim_delta_deg, bool)
            or not isinstance(self.extreme_aim_delta_deg, (int, float))
            or not 0 < self.extreme_aim_delta_deg <= 180
        ):
            raise ValueError("extreme_aim_delta_deg must be between 0 and 180")
        if (
            isinstance(self.fast_reaction_ms, bool)
            or not isinstance(self.fast_reaction_ms, int)
            or self.fast_reaction_ms < 0
        ):
            raise ValueError("fast_reaction_ms must not be negative")
        if (
            isinstance(self.repeated_aim_anomalies, bool)
            or not isinstance(self.repeated_aim_anomalies, int)
            or self.repeated_aim_anomalies < 1
        ):
            raise ValueError("repeated_aim_anomalies must be positive")
        if (
            isinstance(self.repeated_occluded_alignments, bool)
            or not isinstance(self.repeated_occluded_alignments, int)
            or self.repeated_occluded_alignments < 1
        ):
            raise ValueError("repeated_occluded_alignments must be positive")
        if (
            isinstance(self.review_score, bool)
            or not isinstance(self.review_score, int)
            or not 1 <= self.review_score <= 100
        ):
            raise ValueError("review_score must be between 1 and 100")
        if (
            isinstance(self.confirmed_blocked_hits_for_kick, bool)
            or not isinstance(self.confirmed_blocked_hits_for_kick, int)
            or self.confirmed_blocked_hits_for_kick < 1
        ):
            raise ValueError("confirmed_blocked_hits_for_kick must be positive")


@dataclass(frozen=True)
class MonitorResult:
    risk_score: int
    recommendation: Recommendation
    reasons: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "recommendation": self.recommendation,
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
        }


def _require_bool(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _validate_event(event: TelemetryEvent, previous_timestamp: int) -> None:
    if not isinstance(event, TelemetryEvent):
        raise ValueError("events must contain TelemetryEvent values")
    if isinstance(event.timestamp_ms, bool) or not isinstance(event.timestamp_ms, int):
        raise ValueError("timestamp_ms must be an integer")
    if event.timestamp_ms < 0 or event.timestamp_ms < previous_timestamp:
        raise ValueError("events must be ordered by timestamp_ms")
    if not isinstance(event.data, Mapping):
        raise ValueError("event data must be a mapping")

    if event.kind == "shot":
        _require_bool(event.data, "hit")
        _require_bool(event.data, "target_visible")
        blocked = _require_bool(event.data, "line_of_sight_blocked")
        if event.data["hit"] and blocked and event.data["target_visible"]:
            raise ValueError("a visible target cannot also be line-of-sight blocked")
    elif event.kind == "aim":
        delta = event.data.get("angular_delta_deg")
        if isinstance(delta, bool) or not isinstance(delta, (int, float)):
            raise ValueError("angular_delta_deg must be a number")
        if not 0 <= delta <= 180:
            raise ValueError("angular_delta_deg must be between 0 and 180")
        reaction = event.data.get("reaction_ms")
        if isinstance(reaction, bool) or not isinstance(reaction, int) or reaction < 0:
            raise ValueError("reaction_ms must be a non-negative integer")
        target_visible = _require_bool(event.data, "target_visible")
        if "occluded_target_alignment" in event.data:
            alignment = _require_bool(event.data, "occluded_target_alignment")
            if alignment and target_visible:
                raise ValueError("an occluded target alignment cannot be visible")
    else:
        raise ValueError("event kind must be 'aim' or 'shot'")


class GameMonitor:
    """Scores suspicious behavior and returns an explainable response suggestion."""

    def __init__(self, config: MonitorConfig | None = None) -> None:
        self.config = config or MonitorConfig()

    def evaluate(
        self,
        events: Sequence[TelemetryEvent],
        *,
        ace_status: AceStatus = "unavailable",
    ) -> MonitorResult:
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            raise ValueError("events must be a sequence")
        if len(events) > MAX_EVENTS_PER_EVALUATION:
            raise ValueError(f"at most {MAX_EVENTS_PER_EVALUATION} events may be evaluated")
        if not isinstance(ace_status, str) or ace_status not in {
            "healthy",
            "unavailable",
            "tampered",
        }:
            raise ValueError("ace_status must be healthy, unavailable, or tampered")

        previous_timestamp = -1
        blocked_hits = 0
        aim_anomalies = 0
        occluded_alignments = 0
        for event in events:
            _validate_event(event, previous_timestamp)
            previous_timestamp = event.timestamp_ms
            if event.kind == "shot":
                if (
                    event.data["hit"]
                    and not event.data["target_visible"]
                    and event.data["line_of_sight_blocked"]
                ):
                    blocked_hits += 1
            elif (
                event.kind == "aim"
            ):
                if (
                    event.data["target_visible"]
                    and event.data["angular_delta_deg"] >= self.config.extreme_aim_delta_deg
                    and event.data["reaction_ms"] <= self.config.fast_reaction_ms
                ):
                    aim_anomalies += 1
                if event.data.get("occluded_target_alignment", False):
                    occluded_alignments += 1

        repeated_aim_pattern = aim_anomalies >= self.config.repeated_aim_anomalies
        repeated_occluded_alignment = (
            occluded_alignments >= self.config.repeated_occluded_alignments
        )
        score = min(
            100,
            blocked_hits * 50
            + (20 if repeated_aim_pattern else 0)
            + (20 if repeated_occluded_alignment else 0)
            + (20 if ace_status == "tampered" else 0),
        )
        reasons: list[str] = []
        if blocked_hits:
            reasons.append("server_confirmed_hit_through_blocked_line_of_sight")
        if repeated_aim_pattern:
            reasons.append("repeated_extreme_aim_changes_with_fast_reaction")
        if repeated_occluded_alignment:
            reasons.append("repeated_server_confirmed_alignment_with_occluded_targets")
        if ace_status == "tampered":
            reasons.append("authorized_anti_cheat_integrity_signal")

        if blocked_hits >= self.config.confirmed_blocked_hits_for_kick:
            recommendation: Recommendation = "kick"
        elif score >= self.config.review_score:
            recommendation = "review"
        else:
            recommendation = "observe"

        return MonitorResult(
            risk_score=score,
            recommendation=recommendation,
            reasons=tuple(reasons),
            evidence={
                "server_confirmed_blocked_hits": blocked_hits,
                "extreme_aim_fast_reaction_events": aim_anomalies,
                "server_confirmed_occluded_target_alignments": occluded_alignments,
            },
        )
