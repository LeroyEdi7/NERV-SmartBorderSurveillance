"""Common event-schema adapters and append-only JSONL sink for Person 4."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ai.contracts import CommonEvent, FaceTrackResult, PlateTrackResult


def face_event(result: FaceTrackResult, timestamp: datetime, entity_id: str | None = None) -> CommonEvent:
    if not result.event_ready:
        raise ValueError("Face result has not reached event-ready consensus")
    return CommonEvent(
        event_id=str(uuid4()),
        event_type="WATCHLIST_MATCH_CANDIDATE",
        timestamp=timestamp,
        camera_id=result.camera_id,
        entity_id=entity_id or f"person:{result.camera_id}:{result.track_id}",
        entity_type="person",
        severity="high",
        status="PENDING_HUMAN_REVIEW",
        confidence=result.mean_similarity,
        evidence={"face_consensus": result.to_dict()},
        metadata={
            "producer": "person3-face",
            "watchlist_id": result.watchlist_id,
            "display_name": result.display_name,
            "privacy": "biometric_candidate_not_identity_claim",
        },
    )


def plate_event(result: PlateTrackResult, timestamp: datetime, entity_id: str | None = None) -> CommonEvent:
    if not result.event_ready:
        raise ValueError("Plate result has not reached event-ready consensus")
    camera_id = result.source_cameras[0] if result.source_cameras else "unknown"
    return CommonEvent(
        event_id=str(uuid4()),
        event_type="VEHICLE_IDENTITY_RESOLVED",
        timestamp=timestamp,
        camera_id=camera_id,
        entity_id=entity_id or f"vehicle:{result.final_text}",
        entity_type="vehicle",
        severity="medium",
        status="PENDING_HUMAN_REVIEW",
        confidence=result.agreement,
        evidence={"plate_consensus": result.to_dict()},
        metadata={
            "producer": "person3-anpr",
            "plate_text": result.final_text,
            "cross_camera": len(result.source_cameras) > 1,
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
