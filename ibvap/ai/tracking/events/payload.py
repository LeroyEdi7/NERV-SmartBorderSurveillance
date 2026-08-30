from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from ibvap.ai.tracking.models import EventPayload

ALLOWED_EVENT_TYPES = {
    "person_detected",
    "vehicle_detected",
    "intrusion",
    "watchlist_match",
    "plate_detected",
    "vehicle_person_association",
    "cross_camera_match",
    "hostile_activity",
    "suspicious_activity",
}

ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH"}

_evt_counter = 0


def make_event_id() -> str:
    global _evt_counter
    _evt_counter += 1
    return f"EVT-{_evt_counter:06d}"


def make_idempotency_key(track_id, event_type: str, timestamp: str) -> str:
    raw = f"{track_id}|{event_type}|{timestamp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_event_payload(
    event_type: str,
    track_id,
    bbox,
    camera_id: str,
    confidence: float,
    severity: str,
    extra: dict | None = None,
    timestamp: str | None = None,
    entity_id: str | None = None,
    entity_type: str = "person",
    class_name: str = "person",
    event_id: str | None = None,
) -> dict:
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}")
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(f"Invalid severity: {severity}")
    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
        raise ValueError(f"Malformed bbox: {bbox}")

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    evt_id = event_id or make_event_id()
    ent_id = entity_id or (f"G-{track_id:03d}" if isinstance(track_id, int) else str(track_id))

    payload = EventPayload(
        event_id=evt_id,
        event_type=event_type,
        timestamp=ts,
        track_id=track_id,
        camera_id=camera_id,
        bbox=[float(x) for x in bbox],
        confidence=round(float(confidence), 3),
        severity=severity,
        entity_id=ent_id,
        entity_type=entity_type,
        class_name=class_name,
        metadata=extra,
        idempotency_key=make_idempotency_key(track_id, event_type, ts),
    )
    return payload.to_dict()
