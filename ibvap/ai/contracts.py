"""Stable integration contracts between detection, tracking, Person 3, and backend.

The contracts intentionally use dataclasses instead of web-framework models so the
AI worker can run in-process, in a queue worker, or behind an API without coupling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import numpy as np


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceState(StrEnum):
    NO_EVIDENCE = "NO_EVIDENCE"
    UNRESOLVED = "UNRESOLVED"
    PARTIAL = "PARTIAL"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    MATCH_CANDIDATE = "MATCH_CANDIDATE"
    VERIFIED = "VERIFIED"
    DISMISSED = "DISMISSED"


class QualityState(StrEnum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    UNUSABLE = "UNUSABLE"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError(f"Invalid bounding box: {self}")

    @classmethod
    def from_sequence(cls, values: list[float] | tuple[float, float, float, float]) -> "BoundingBox":
        if len(values) != 4:
            raise ValueError("Bounding box must contain exactly four values")
        return cls(*(float(value) for value in values))

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def as_list(self) -> list[float]:
        return [self.x1, self.y1, self.x2, self.y2]

    def translated(self, dx: float, dy: float) -> "BoundingBox":
        return BoundingBox(self.x1 + dx, self.y1 + dy, self.x2 + dx, self.y2 + dy)


@dataclass(slots=True)
class TrackObservation:
    camera_id: str
    frame_id: int
    timestamp: datetime
    object_type: str
    track_id: int
    bbox: BoundingBox
    frame: np.ndarray
    global_entity_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.camera_id:
            raise ValueError("camera_id is required")
        if self.frame_id < 0 or self.track_id < 0:
            raise ValueError("frame_id and track_id must be non-negative")
        if self.frame.ndim not in (2, 3):
            raise ValueError("frame must be a grayscale or color NumPy array")
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

    @property
    def track_key(self) -> str:
        return f"{self.camera_id}:{self.track_id}"

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp.isoformat(),
            "object_type": self.object_type,
            "track_id": self.track_id,
            "bbox": self.bbox.as_list(),
            "global_entity_id": self.global_entity_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    state: QualityState
    score: float
    brightness: float
    sharpness: float
    clipped_ratio: float
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["reasons"] = list(self.reasons)
        return payload


@dataclass(frozen=True, slots=True)
class FaceFrameResult:
    camera_id: str
    frame_id: int
    timestamp: datetime
    track_id: int
    face_bbox: BoundingBox | None
    status: EvidenceState
    quality: QualityAssessment
    watchlist_id: str | None = None
    display_name: str | None = None
    similarity: float | None = None
    second_best_similarity: float | None = None
    embedding: tuple[float, ...] | None = field(default=None, repr=False)
    model_name: str = "unknown"
    evidence_hash: str | None = None
    reasons: tuple[str, ...] = ()

    def to_dict(self, include_embedding: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["status"] = self.status.value
        payload["quality"] = self.quality.to_dict()
        payload["face_bbox"] = self.face_bbox.as_list() if self.face_bbox else None
        payload["reasons"] = list(self.reasons)
        if not include_embedding:
            payload.pop("embedding", None)
        return payload


@dataclass(frozen=True, slots=True)
class FaceTrackResult:
    camera_id: str
    track_id: int
    status: EvidenceState
    watchlist_id: str | None
    display_name: str | None
    supporting_frames: int
    usable_frames: int
    total_frames: int
    mean_similarity: float | None
    source_frame_ids: tuple[int, ...]
    model_name: str
    event_ready: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["source_frame_ids"] = list(self.source_frame_ids)
        payload["reasons"] = list(self.reasons)
        return payload


@dataclass(frozen=True, slots=True)
class PlateFrameResult:
    camera_id: str
    frame_id: int
    timestamp: datetime
    track_id: int
    plate_bbox: BoundingBox | None
    raw_text: str | None
    normalized_text: str | None
    character_confidences: tuple[float, ...]
    detector_confidence: float
    ocr_confidence: float
    status: EvidenceState
    quality: QualityAssessment
    grammar_score: float = 0.0
    grammar_suggestion: str | None = None
    model_name: str = "unknown"
    evidence_hash: str | None = None
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat()
        payload["status"] = self.status.value
        payload["quality"] = self.quality.to_dict()
        payload["plate_bbox"] = self.plate_bbox.as_list() if self.plate_bbox else None
        payload["character_confidences"] = list(self.character_confidences)
        payload["reasons"] = list(self.reasons)
        return payload


@dataclass(frozen=True, slots=True)
class CharacterProvenance:
    index: int
    character: str
    support_weight: float
    total_weight: float
    cameras: tuple[str, ...]
    frame_ids: tuple[int, ...]

    @property
    def agreement(self) -> float:
        return self.support_weight / self.total_weight if self.total_weight else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "character": self.character,
            "support_weight": round(self.support_weight, 4),
            "total_weight": round(self.total_weight, 4),
            "agreement": round(self.agreement, 4),
            "cameras": list(self.cameras),
            "frame_ids": list(self.frame_ids),
        }


@dataclass(frozen=True, slots=True)
class PlateTrackResult:
    track_keys: tuple[str, ...]
    status: EvidenceState
    final_text: str | None
    raw_candidates: tuple[str, ...]
    supporting_frames: int
    usable_frames: int
    total_frames: int
    agreement: float
    provenance: tuple[CharacterProvenance, ...]
    source_cameras: tuple[str, ...]
    source_frame_ids: tuple[int, ...]
    model_name: str
    event_ready: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["track_keys"] = list(self.track_keys)
        payload["raw_candidates"] = list(self.raw_candidates)
        payload["provenance"] = [item.to_dict() for item in self.provenance]
        payload["source_cameras"] = list(self.source_cameras)
        payload["source_frame_ids"] = list(self.source_frame_ids)
        payload["reasons"] = list(self.reasons)
        return payload


@dataclass(frozen=True, slots=True)
class CommonEvent:
    event_id: str
    event_type: str
    timestamp: datetime
    camera_id: str
    entity_id: str
    entity_type: str
    severity: str
    status: str
    confidence: float | None
    evidence: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "camera_id": self.camera_id,
            "entity": {"entity_id": self.entity_id, "entity_type": self.entity_type},
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "status": self.status,
            "metadata": self.metadata,
        }
