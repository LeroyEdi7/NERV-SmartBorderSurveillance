# Person 3 Implementation — Face Recognition, ANPR, and Evidence Passport

## Status

Team integration requirements for P1, P2, and P4 are maintained separately in
[`P1_P2_P4_INTEGRATION_REQUIREMENTS.md`](P1_P2_P4_INTEGRATION_REQUIREMENTS.md).

Person 3's standalone module is implemented and tested. It can run with mock/manual
track observations today. Final end-to-end operation requires live detection boxes
from Person 1, persistent/cross-camera identities from Person 2, and event storage/API
integration from Person 4.

Verified in the development environment:

- All 11 automated tests pass.
- InsightFace `buffalo_l` loads and performs real face detection/embedding inference.
- FastALPR loads its YOLOv9 plate detector and OCR model and performs real inference.
- Real 4K traffic footage produced repeated OCR evidence for plate candidate `9FIN556`.
- Low-resolution faces and plates are rejected instead of becoming identity alerts.

This is hackathon-demo-ready code. It is not a production biometric system and no
unsupported percentage-accuracy claim should be made without a labelled evaluation set.

## What Person 3 implemented

### 1. Face detection and embeddings

- Ready-made InsightFace `buffalo_l` adapter.
- Face bounding boxes, landmarks, detection score, and normalized 512-D embeddings.
- CPU-provider default suitable for the shared hackathon laptop.
- Lazy optional-model imports so unit tests can run without downloading model weights.

Main files:

- `ai/face/backend.py`
- `ai/face/service.py`

### 2. Face evidence quality controls

- Minimum face-size validation.
- Blur, brightness, clipping, detector-confidence, and pose checks.
- Rejected observations retain explicit rejection reasons.
- Low-quality observations cannot emit a confirmed identity event.

Main file: `ai/face/quality.py`

### 3. Consent-aware watchlist matching

- Enrolment from multiple reference images.
- Required consent/authority reference during enrolment.
- Normalized embeddings are stored; original reference photographs are not persisted.
- Cosine similarity matching.
- Ambiguity protection using best-match versus second-best-match separation.
- Safe result states: `UNRESOLVED`, `POSSIBLE_MATCH`, and `MATCH_CANDIDATE`.
- A model match remains pending human review; it is not a final identity claim.

Main files:

- `ai/face/watchlist.py`
- `scripts/enroll_watchlist.py`

### 4. Multi-frame face consensus

- Fuses usable observations across time instead of trusting one frame.
- Requires configurable multi-frame support before producing a candidate event.
- Preserves source-frame provenance.
- Applies alert cooldown/de-duplication.

Main file: `ai/face/consensus.py`

### 5. License-plate detection and OCR

- Ready-made FastALPR adapter.
- YOLOv9 plate detector: `yolo-v9-s-608-license-plate-end2end`.
- OCR model: `cct-s-v2-global-model`.
- Returns plate bounding box, detector confidence, raw OCR text, OCR confidence, and
  available per-character confidence.
- Raw OCR is never silently overwritten.

Main files:

- `ai/anpr/backend.py`
- `ai/anpr/service.py`

### 6. Plate quality and Indian-format assistance

- Minimum plate-size and detector-confidence checks.
- Blur, brightness, and unresolved-OCR rejection.
- Non-destructive Indian and BH-series format suggestions.
- Grammar hints assist review but never replace the source OCR evidence.

Main files:

- `ai/anpr/quality.py`
- `ai/anpr/india_format.py`

### 7. Multi-frame and cross-camera plate consensus

- Weighted voting across multiple frames.
- Character-by-character resolution when OCR readings disagree.
- Cross-camera fusion when Person 2 supplies the same `global_entity_id`.
- Character provenance records the camera/frame supporting every resolved character.
- Configurable minimum observations and consensus confidence.
- Alert cooldown/de-duplication.

Main file: `ai/anpr/consensus.py`

### 8. Evidence Passport

- Creates a human-reviewable evidence record for face/plate candidates.
- Preserves accepted and rejected observations.
- Records decision trace, source frames, camera IDs, local/global entity IDs, model
  names, thresholds, confidence, and character provenance.
- SHA-256 integrity hash detects later JSON tampering.
- Supports explicit `VERIFIED` and `DISMISSED` operator decisions.

Main files:

- `ai/evidence/passport.py`
- `ai/evidence/events.py`

### 9. Shared pipeline and contracts

- `TrackObservation` is the stable P1/P2-to-P3 input contract.
- `CommonEvent` is the stable P3-to-P4 output contract.
- `Person3Pipeline.process()` routes person and vehicle observations through the
  correct quality, inference, consensus, passport, and event path.
- Mock backends provide a deterministic no-download team demo.

Main files:

- `ai/contracts.py`
- `ai/pipeline.py`
- `ai/mocks.py`
- `scripts/demo_mock_pipeline.py`

## Ready-made models

| Capability | Model | Training needed for MVP? |
|---|---|---:|
| Face detection and embedding | InsightFace `buffalo_l` | No |
| Plate detection | FastALPR YOLOv9 608 end-to-end | No |
| Plate OCR | FastALPR `cct-s-v2-global-model` | No |
| Face/plate temporal consensus | Repository implementation | No |
| Evidence Passport | Repository implementation | No |

Model binaries are intentionally excluded from Git. They download on first real-model
use. InsightFace pretrained weights are generally restricted to non-commercial research
unless separately licensed; they are suitable for the hackathon prototype, not automatic
commercial deployment.

See `configs/model_manifest.json` for the recorded model configuration and licensing notes.

## Required input from Person 1

Person 1 should produce one observation for every detected person/vehicle with:

- Full BGR NumPy frame.
- `camera_id`.
- `frame_id`.
- UTC timestamp.
- Object type normalized to `person` or `vehicle`.
- Full-frame `x1, y1, x2, y2` bounding box.
- Detector confidence in observation metadata.

Person 3 uses Person 1 boxes to:

- Run face inference inside person regions.
- Run ANPR inside vehicle regions.
- Reject signs and unrelated scene text outside vehicles.
- Associate a detected plate with its parent vehicle.
- Avoid expensive full-frame inference.

Person 3 can run without Person 1 for development, but live-system speed and false-positive
control depend on these detection boxes.

## Required input from Person 2

Person 2 should add:

- A stable camera-local `track_id` while the object remains visible.
- Lost/reacquired track association.
- The same `global_entity_id` for the same object across cameras.
- Person-to-vehicle association metadata when available.

Without `global_entity_id`, Person 3 consensus remains local to one camera track. With it,
multiple camera tracks contribute to a single face/plate Evidence Passport.

## Input example for P1 and P2

```python
from datetime import datetime, timezone

from ai.contracts import BoundingBox, TrackObservation

observation = TrackObservation(
    camera_id="CAM-GATE-A",
    frame_id=135,
    timestamp=datetime.now(timezone.utc),
    object_type="vehicle",
    track_id=91,
    bbox=BoundingBox(40, 60, 600, 330),
    frame=bgr_numpy_frame,
    global_entity_id="VEHICLE-007",  # optional until P2 cross-camera matching is ready
    metadata={"detector_confidence": 0.94},
)

events = person3_pipeline.process(observation)
```

## Output for Person 4

Person 3 returns `CommonEvent` objects and supports append-only JSONL output. Person 4
should persist and expose these events through the backend.

Important output fields:

- Unique `EVT-`-prefixed `event_id`.
- Approved `event_type`: `watchlist_match` or `plate_detected` for P3.
- Timestamp and camera ID.
- Local/global entity identity.
- Detection class, confidence, full-frame box, and local track ID.
- Uppercase severity (`LOW`, `MEDIUM`, or `HIGH`).
- Accepted/rejected evidence, provenance, and `PENDING_HUMAN_REVIEW` inside `metadata`.
- Evidence Passport integrity state.

See `docs/BACKEND_EVENT_FORMAT.md` for the shared P1/P2/P3-to-P4 contract.

Person 4 must not expose biometric embeddings through frontend APIs.

## Configuration

All tunable thresholds are centralized in `configs/person3.yaml`, including:

- Model names and execution providers.
- Face/plate quality thresholds.
- Watchlist similarity and ambiguity thresholds.
- Minimum consensus observations.
- Event cooldown.
- Evidence and watchlist paths.

Do not hard-code thresholds in integration code.

## Installation

Use Python 3.11 or 3.12 from the `ibvap` directory:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[models,test]'
```

The first real-model run requires internet access to download model weights.

## Verification commands

```bash
PYTHONPATH=. python -m compileall -q ai scripts
pytest
python scripts/demo_mock_pipeline.py
```

Expected automated-test result: 11 passing tests.

For real-video analysis:

```bash
python scripts/analyze_real_video.py INPUT_VIDEO.mp4 --output demo/real-video
```

## Test coverage

The tests cover:

- Plate normalization and India/BH suggestions.
- Weighted multi-frame character consensus.
- Face quality and ambiguous watchlist matching.
- Plate and face service behavior.
- Evidence Passport hashing and tamper detection.
- Human review decisions.
- Event cooldown/de-duplication.
- P1/P2 observation contracts and pipeline routing.

Test files are in `ibvap/tests/`.

## Accuracy statement

The models have passed functional and real-video smoke tests. Formal accuracy is not yet
measured because the team repository does not contain a sufficiently large labelled face
and plate validation set.

Before presenting a numeric accuracy claim, evaluate:

- Plate full-string exact accuracy.
- Plate character accuracy.
- Face precision/recall at the configured threshold.
- False matches and false non-matches.
- Quality-rejection percentage.
- Median and p95 latency on the demo laptop.
- Single-frame OCR versus multi-frame consensus accuracy.

Use `scripts/evaluate_results.py` with labelled predictions. Do not present the tiny
`demo/evaluation.example.json` file as a real benchmark.

## Known limitations and remaining integration

- Distant faces with too few pixels are deliberately rejected.
- Plate detection over an entire scene may detect sign-like text; P1 vehicle ROIs are the
  primary integration control for this.
- Cross-camera fusion needs P2 `global_entity_id` values.
- Person-to-vehicle association needs P2 metadata.
- Final backend persistence and alert delivery need P4 integration.
- Watchlist matches always require accountable human review.
- Thresholds must be tuned on the final cameras and demo laptop.

## Files that must not be committed

- `.venv/`
- `models/` downloaded weights
- Original face/watchlist photographs
- Biometric embedding databases containing real people
- Input test videos
- Generated evidence/events and real-video output folders
- `.pytest_cache/`, `.coverage`, and `__pycache__/`

## Team integration checklist

- [ ] P1 emits valid BGR frames and full-frame person/vehicle boxes.
- [ ] P1 adds detector confidence to metadata.
- [ ] P2 supplies stable local `track_id` values.
- [ ] P2 supplies `global_entity_id` for cross-camera matches.
- [ ] P2 supplies person-to-vehicle associations.
- [ ] P4 persists `CommonEvent.to_dict()` output.
- [ ] P4 keeps identity results pending until human review.
- [ ] P5 displays raw evidence, rejected evidence, provenance, and integrity state.
- [ ] Final demo-camera thresholds are validated.
- [ ] All tests pass on the final demo laptop.

## Person 3 ownership boundary

Person 3 owns everything after a valid tracked person/vehicle observation enters
`Person3Pipeline`: crops, face/ANPR inference, quality gates, watchlist matching, temporal
consensus, Evidence Passport creation, and identity-candidate events.

Person 3 does not own P1 object detection, P2 tracking/ReID, P4 persistence/alert APIs, or
P5 dashboard implementation.
