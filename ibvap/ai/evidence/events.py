"""Common event-schema adapters and append-only JSONL sink for Person 4."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ai.contracts import BoundingBox, CommonEvent, EventDetection, FaceTrackResult, PlateTrackResult


def _event_id() -> str:
    """Generate a backend-safe, globally unique ID with the required prefix."""

    return f"EVT-{uuid4().hex.upper()}"


def build_event(
    *,
    event_type: str,
    timestamp: datetime,
    camera_id: str,
    entity_id: str,
    entity_type: str,
    class_name: str,
    confidence: float,
    bbox: BoundingBox,
    track_id: int,
    severity: str,
    metadata: dict | None = None,
) -> CommonEvent:
    """Convert any P1/P2/P3 event-ready result to the shared backend envelope."""

    return CommonEvent(
        event_id=_event_id(),
        event_type=event_type,
        timestamp=timestamp,
        camera_id=camera_id,
        entity_id=entity_id,
        entity_type=entity_type,
        detection=EventDetection(
            class_name=class_name,
            confidence=confidence,
            bbox=bbox,
            track_id=track_id,
        ),
        severity=severity,
        metadata=metadata or {},
    )


def face_event(
    result: FaceTrackResult,
    timestamp: datetime,
    bbox: BoundingBox,
    entity_id: str | None = None,
) -> CommonEvent:
    if not result.event_ready:
        raise ValueError("Face result has not reached event-ready consensus")
    return build_event(
        event_type="watchlist_match",
        timestamp=timestamp,
        camera_id=result.camera_id,
        entity_id=entity_id or f"person:{result.camera_id}:{result.track_id}",
        entity_type="person",
        class_name="person",
        confidence=float(result.mean_similarity or 0.0),
        bbox=bbox,
        track_id=result.track_id,
        severity="HIGH",
        metadata={
            "schema_version": "1.0",
            "producer": "person3-face",
            "review_status": "PENDING_HUMAN_REVIEW",
            "watchlist_id": result.watchlist_id,
            "display_name": result.display_name,
            "privacy": "biometric_candidate_not_identity_claim",
            "evidence": {"face_consensus": result.to_dict()},
        },
    )


def plate_event(
    result: PlateTrackResult,
    timestamp: datetime,
    camera_id: str,
    bbox: BoundingBox,
    track_id: int,
    entity_id: str | None = None,
) -> CommonEvent:
    if not result.event_ready:
        raise ValueError("Plate result has not reached event-ready consensus")
    return build_event(
        event_type="plate_detected",
        timestamp=timestamp,
        camera_id=camera_id,
        entity_id=entity_id or f"vehicle:{result.final_text}",
        entity_type="vehicle",
        class_name="vehicle",
        confidence=result.agreement,
        bbox=bbox,
        track_id=track_id,
        severity="MEDIUM",
        metadata={
            "schema_version": "1.0",
            "producer": "person3-anpr",
            "review_status": "PENDING_HUMAN_REVIEW",
            "plate_text": result.final_text,
            "cross_camera": len(result.source_cameras) > 1,
            "evidence": {"plate_consensus": result.to_dict()},
        },
    )


class JsonlEventSink:
    """Tiny local adapter; Person 4 can replace it with Kafka/HTTP without AI changes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def publish(self, event: CommonEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event.to_dict(), separators=(",", ":"), sort_keys=True) + "\n")


def parse_timestamp(value: str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
