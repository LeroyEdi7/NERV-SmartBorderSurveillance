# P1, P2, and P4 Requirements for Person 3 Integration

## Purpose

This document tells Person 1, Person 2, and Person 4 exactly what Person 3 needs
for end-to-end face recognition, ANPR, cross-camera consensus, Evidence Passport,
and human-review events.

Person 3 implementation branch:

- Branch: `face-anpr`
- Input contract: `ibvap/ai/contracts.py::TrackObservation`
- Output contract: `ibvap/ai/contracts.py::CommonEvent`
- Pipeline entry point: `ibvap/ai/pipeline.py::Person3Pipeline.process`

Person 3 owns crops, face/ANPR model inference, evidence quality checks, watchlist
matching, temporal consensus, Evidence Passports, and candidate identity events.
P1/P2/P4 should integrate through the contracts instead of modifying those internals.

## End-to-end flow

```text
P1 detection
  -> full frame + person/vehicle box
P2 tracking
  -> stable local track_id + optional global_entity_id
P3 face/ANPR pipeline
  -> CommonEvent + Evidence Passport
P4 backend
  -> database + review APIs + event stream for P5
```

## Shared Person 3 input contract

P1 and P2 together must construct this object for every tracked observation:

```python
from datetime import datetime, timezone

from ai.contracts import BoundingBox, TrackObservation

observation = TrackObservation(
    camera_id="CAM-GATE-A",
    frame_id=135,
    timestamp=datetime.now(timezone.utc),
    object_type="vehicle",              # exactly "person" or "vehicle"
    track_id=91,                         # P2 camera-local ID
    bbox=BoundingBox(40, 60, 600, 330), # P1 full-frame pixel box
    frame=bgr_numpy_frame,               # P1 full BGR OpenCV frame
    global_entity_id="VEHICLE-007",     # P2 cross-camera ID; optional initially
    metadata={
        "detector_confidence": 0.94,
        "detector_class": "car",
    },
)

events = person3_pipeline.process(observation)
```

Required validation rules:

- `camera_id` must be non-empty and stable for one physical camera.
- `frame_id` and `track_id` must be non-negative integers.
- `timestamp` must be timezone-aware; UTC is preferred.
- `object_type` must be normalized to `person` or `vehicle`.
- `bbox` must be `x1, y1, x2, y2` in full-frame pixel coordinates.
- `x2 > x1`, `y2 > y1`, and the box should lie inside the frame.
- `frame` must be a grayscale or BGR NumPy array; BGR `uint8` is preferred.
- Do not serialize the NumPy frame into JSON when running in-process. For a queue/API,
  use an agreed image reference or encoded-image transport outside this dataclass.

## Person 1 — Detection requirements

### P1 must provide

- Full BGR OpenCV frame for every processed frame.
- Stable `camera_id`.
- Increasing `frame_id` within each camera stream.
- UTC timestamp for the captured frame.
- Person and vehicle bounding boxes.
- Normalized object type: `person` or `vehicle`.
- Detector confidence in `metadata["detector_confidence"]`.
- Original detector class in `metadata["detector_class"]` when useful.
- Vehicle class where available: car, motorcycle, bus, truck, or other vehicle.

### P1 must not do

- Do not run face recognition or ANPR; those belong to P3.
- Do not send only cropped images. P3 needs the full frame plus the full-frame box.
- Do not convert all YOLO classes into arbitrary names. Normalize the P3-facing type
  to `person` or `vehicle` and preserve the original class in metadata.
- Do not pass boxes in normalized 0–1 coordinates unless converted to pixels first.

### Why P3 needs P1 boxes

- Person boxes restrict face inference to the correct region.
- Vehicle boxes restrict ANPR inference to vehicles.
- Vehicle ROIs prevent signboards and unrelated text from becoming plate candidates.
- Cropped ROI inference is faster than repeatedly scanning the entire frame.
- A plate candidate can be associated with its parent vehicle observation.

### P1 minimum acceptance test

- [ ] A sample video produces both person and vehicle observations.
- [ ] Each observation validates as a `TrackObservation` after P2 adds `track_id`.
- [ ] All boxes use full-frame pixel coordinates and stay inside the image.
- [ ] Detector confidence is present in metadata.
- [ ] The original full frame is still available to P3.
- [ ] At least one clear/near vehicle ROI is supplied for ANPR testing.
- [ ] At least one sufficiently large frontal face is supplied for face testing.

### Suggested P1 adapter function

```python
def normalize_object_type(yolo_class: str) -> str | None:
    if yolo_class == "person":
        return "person"
    if yolo_class in {"car", "motorcycle", "bus", "truck"}:
        return "vehicle"
    return None
```

## Person 2 — Tracking and cross-camera requirements

### P2 must provide

- A stable camera-local `track_id` while an entity is continuously visible.
- Correct handling of temporarily lost and reacquired tracks.
- An optional `global_entity_id` that is shared by the same entity across cameras.
- Person-to-vehicle association metadata when available.
- Old/new track association details in metadata when a track is reacquired.

Suggested metadata:

```python
metadata={
    "tracking_state": "REACQUIRED",       # ACTIVE, LOST, or REACQUIRED
    "reacquired_from_track_id": 91,
    "associated_person_global_id": "PERSON-041",
    "associated_vehicle_global_id": "VEHICLE-007",
}
```

### ID rules

- `track_id` is local to one camera.
- Two different cameras may use different local IDs for the same entity.
- `global_entity_id` links those different local tracks across cameras.
- The same physical entity must not receive different global IDs without an explicit
  split/correction event.
- Different physical entities must not share a global ID.

Example for one vehicle:

```text
CAM-GATE-A local track 91 -> global_entity_id VEHICLE-007
CAM-GATE-B local track 12 -> global_entity_id VEHICLE-007
```

P3 groups these as one vehicle and fuses their OCR observations. Without a
`global_entity_id`, P3 still works, but consensus remains local to one camera track.

### Lost/reacquired expectations

- A short occlusion should preserve or explicitly reconnect the old identity.
- P2 should not generate a new unrelated identity for every brief missed frame.
- Reacquisition metadata should explain the old/new local-track relationship.
- P3 should receive only observations associated with the selected active/reacquired
  identity, not duplicated competing tracks for the same box.

### Person-to-vehicle association

P2 should expose associations such as:

- Person entered/exited the vehicle ROI.
- Person and vehicle remained within a configured spatial/temporal window.
- Association confidence and supporting time range.
- Associated person and vehicle global IDs.

P3 records this as Evidence Passport metadata; it must not be described as proven
ownership or identity without human review.

### P2 minimum acceptance test

- [ ] One vehicle is tracked continuously in Camera A.
- [ ] A short occlusion is reported as lost/reacquired without an unrelated identity.
- [ ] The same vehicle appears in Camera B with a different local `track_id`.
- [ ] Both camera tracks receive the same `global_entity_id`.
- [ ] P3 plate consensus contains source cameras A and B.
- [ ] A person-to-vehicle relationship contains IDs, confidence, and timing metadata.

## Person 4 — Backend and event requirements

### P3 output contract

P3 returns `CommonEvent` objects. The JSON representation is produced through
`CommonEvent.to_dict()`:

```json
{
  "event_id": "EVT-9FBE6354A1604DB795B279F1D50C62B3",
  "event_type": "plate_detected",
  "timestamp": "2026-08-25T12:00:00Z",
  "camera_id": "CAM-GATE-A",
  "entity": {
    "entity_id": "VEHICLE-007",
    "entity_type": "vehicle"
  },
  "detection": {
    "class": "vehicle",
    "confidence": 0.93,
    "bbox": [40, 60, 600, 330],
    "track_id": 91
  },
  "severity": "MEDIUM",
  "metadata": {
    "producer": "person3-anpr",
    "review_status": "PENDING_HUMAN_REVIEW",
    "evidence": {"plate_consensus": {}}
  }
}
```

Current event types:

- `watchlist_match`
- `plate_detected`

These are review candidates, not automatic final identity claims.
The complete cross-team enum and JSON Schema are in `docs/BACKEND_EVENT_FORMAT.md`
and `configs/backend_event_schema.json`.

### P4 must implement

- Event ingestion from `CommonEvent.to_dict()` or the JSONL sink.
- Idempotency/deduplication using unique `event_id`.
- Database persistence for events and Evidence Passports.
- Retrieval of events by ID, camera, entity, time, type, severity, and status.
- Evidence Passport retrieval.
- Human `VERIFY` and `DISMISS` actions.
- Operator identity, decision time, optional reason, and audit history.
- Evidence Passport integrity verification before and after review.
- WebSocket/SSE or polling endpoint for P5 live alerts.
- Safe error responses for missing/invalid events and passports.

### Required API surface

Exact route names may change if documented, but P5/P3 need equivalent behavior:

```text
POST /api/events
GET  /api/events
GET  /api/events/{event_id}
GET  /api/passports/{passport_id}
POST /api/passports/{passport_id}/verify
POST /api/passports/{passport_id}/dismiss
GET  /api/stream/events                 # WebSocket/SSE equivalent is acceptable
```

Suggested review request:

```json
{
  "operator_id": "DEMO-COMMANDER",
  "reason": "Source frames and character provenance reviewed"
}
```

### P4 security/privacy requirements

- Never expose face embeddings through frontend APIs.
- Do not expose a real biometric watchlist in the hackathon demo.
- Keep identity results `PENDING_HUMAN_REVIEW` until an operator acts.
- Preserve rejected evidence and reasons for auditability.
- Do not silently modify raw OCR values.
- Validate all incoming event fields and reject unknown/oversized payloads.
- Protect review endpoints with authentication in any shared deployment.
- Record every review-state change in an append-only audit history.

### P4 database minimum fields

Event storage:

- `event_id` unique primary identifier.
- `event_type`, timestamp, camera ID.
- Entity ID/type.
- Detection JSON and uppercase severity.
- Metadata JSON, including evidence and review status.
- Created/updated timestamps.

Passport storage:

- Passport ID and event/entity link.
- Original Passport JSON.
- Integrity hash and integrity status.
- Current review status.
- Operator ID, decision time, and decision reason.
- Append-only review/audit records.

### P4 minimum acceptance test

- [ ] A P3 event is accepted and stored.
- [ ] Re-sending the same `event_id` does not create a duplicate.
- [ ] P5 can retrieve the event and linked Evidence Passport.
- [ ] Verify/Dismiss updates the status and creates an audit entry.
- [ ] A modified Passport fails integrity verification.
- [ ] Biometric embeddings never appear in API responses.
- [ ] A live event update reaches P5 through the selected streaming mechanism.

## Integration test owned by the team

The final team test should demonstrate:

1. P1 detects a vehicle in Camera A and emits a full-frame vehicle observation.
2. P2 assigns local track 91 and global ID `VEHICLE-007`.
3. P3 collects multiple usable plate observations.
4. The vehicle appears in Camera B as local track 12 with the same global ID.
5. P3 fuses both tracks, resolves OCR disagreement, and creates an Evidence Passport.
6. P3 emits one deduplicated `plate_detected` event.
7. P4 persists and streams the event to P5.
8. P5 displays raw candidates, provenance, rejected evidence, and pending-review state.
9. An operator verifies or dismisses the candidate.
10. P4 stores the audit decision and P5 shows the updated state.

## Definition of done

P1 is done for P3 integration when valid person/vehicle `TrackObservation` inputs can be
created from a real stream without P3 altering P1 detection internals.

P2 is done for P3 integration when local tracking, reacquisition, cross-camera global IDs,
and person-to-vehicle association metadata work on the integration scenario.

P4 is done for P3 integration when P3 events and passports are stored, reviewable,
auditable, integrity-checked, and available to P5 without exposing embeddings.

## Questions and change control

If a contract field must change, update `ai/contracts.py`, this document, tests, and all
affected producer/consumer adapters in the same pull request. Do not make undocumented
payload changes independently on P1, P2, P3, or P4 branches.
