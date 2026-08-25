# Person 3 integration checklist

## Person 1 handoff

- Frames are BGR NumPy arrays (`uint8` preferred).
- Boxes use full-frame pixel coordinates in `x1,y1,x2,y2` order.
- `object_type` is normalized to `person` or `vehicle` when possible.
- Detector confidence may be added to `TrackObservation.metadata` for later analysis.

## Person 2 handoff

- `track_id` remains stable while the object is visible in one camera.
- A re-acquired local track gets the correct old/new association where possible.
- Cross-camera matches share `global_entity_id`; this activates cross-camera ANPR fusion.
- Person–vehicle links are passed to `EvidencePassportBuilder` as association metadata.

## Person 4 handoff

- Consume `CommonEvent.to_dict()` or tail the configured JSONL sink.
- Validate against `configs/backend_event_schema.json`.
- Deduplicate on `event_id`; Person 3 already suppresses repeated inference alerts.
- Persist `metadata.review_status=PENDING_HUMAN_REVIEW` until an operator decides.
- Expose Evidence Passport character provenance and integrity state in the UI.
- Do not expose biometric embeddings through the frontend/API.

## Demo acceptance gates

- Three usable frames are required for confirmed face/plate output.
- A bad blur/dark/small crop appears as rejected evidence, not a false alert.
- Two camera-local vehicle tracks merge when their `global_entity_id` matches.
- The intentionally wrong plate character is corrected by consensus.
- Only one event is emitted during the cooldown window.
- A modified Evidence Passport fails integrity verification.
- All tests pass on the final demo laptop.
