# Shared AI-to-backend event format

P1, P2, and P3 must convert every event-ready AI result into this envelope before
sending it to P4. The machine-readable contract is
`configs/backend_event_schema.json`; P4 should validate incoming payloads against it.

```json
{
  "event_id": "EVT-000001",
  "event_type": "person_detected",
  "timestamp": "2026-08-25T16:30:00Z",
  "camera_id": "BOP-01",
  "entity": {
    "entity_id": "G-017",
    "entity_type": "person"
  },
  "detection": {
    "class": "person",
    "confidence": 0.94,
    "bbox": [120, 80, 250, 400],
    "track_id": 17
  },
  "severity": "LOW",
  "metadata": {}
}
```

## Allowed values

`event_type` must be one of:

- `person_detected`
- `vehicle_detected`
- `intrusion`
- `watchlist_match`
- `plate_detected`
- `vehicle_person_association`
- `cross_camera_match`
- `hostile_activity`
- `suspicious_activity`

`severity` must be `LOW`, `MEDIUM`, or `HIGH` in uppercase.

## Ownership mapping

| Producer | Typical event type | Detection class | Entity type |
|---|---|---|---|
| P1 detection | `person_detected`, `vehicle_detected`, `intrusion`, `hostile_activity`, `suspicious_activity` | model class | `person`, `vehicle`, or `object` |
| P2 tracking | `vehicle_person_association`, `cross_camera_match` | tracked class | `person`, `vehicle`, or `association` |
| P3 face | `watchlist_match` | `person` | `person` |
| P3 ANPR | `plate_detected` | `vehicle` | `vehicle` |

## Field rules

- `event_id`: unique and prefixed with `EVT-`; P4 deduplicates on this value.
- `timestamp`: ISO-8601 UTC, ending in `Z`.
- `bbox`: full-frame `[x1, y1, x2, y2]` coordinates, not crop-relative values.
- `track_id`: P2's camera-local persistent track ID.
- `entity.entity_id`: P2 global ID when available; otherwise a stable producer fallback.
- `confidence`: confidence for the detection/event that triggered this message, from 0 to 1.
- `metadata`: module-specific details only. Do not add new top-level fields.

P3 stores consensus evidence and `PENDING_HUMAN_REVIEW` inside `metadata`. It does
not send embeddings. The P3 pipeline already emits the required shape through
`CommonEvent.to_dict()` and the JSONL sink.

P1 and P2 can use the same adapter instead of manually assembling dictionaries:

```python
from ai.evidence.events import build_event

event = build_event(
    event_type="person_detected",
    timestamp=observation.timestamp,
    camera_id=observation.camera_id,
    entity_id=observation.global_entity_id or f"person:{observation.track_id}",
    entity_type="person",
    class_name="person",
    confidence=detector_confidence,
    bbox=observation.bbox,
    track_id=observation.track_id,
    severity="LOW",
    metadata={"producer": "person1-detection"},
)
payload = event.to_dict()
```

## P4 acceptance behavior

- Reject unknown top-level fields, unknown event types, lowercase severities, invalid
  boxes, and confidence outside 0 to 1.
- Return a clear 4xx validation response; do not silently reshape malformed events.
- Make ingestion idempotent on `event_id`.
- Store `metadata` as JSON so module-specific evidence remains available.
