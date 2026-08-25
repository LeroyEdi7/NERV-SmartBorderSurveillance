from datetime import datetime, timezone

import pytest

from ai.contracts import (
    BoundingBox,
    CommonEvent,
    EventDetection,
    EvidenceState,
    FaceTrackResult,
    PlateTrackResult,
)
from ai.evidence.events import JsonlEventSink, face_event, plate_event
from ai.evidence.passport import EvidencePassportBuilder


def face_result(event_ready=True):
    return FaceTrackResult(
        "CAM-A",
        8,
        EvidenceState.MATCH_CANDIDATE,
        "WL-1",
        "Demo",
        3,
        3,
        4,
        0.71,
        (1, 2, 3),
        "test/face",
        event_ready,
    )


def plate_result():
    return PlateTrackResult(
        ("CAM-A:4",),
        EvidenceState.VERIFIED,
        "MH12AB1234",
        ("MH12AB1234",) * 3,
        3,
        3,
        3,
        0.91,
        (),
        ("CAM-A",),
        (1, 2, 3),
        "test/anpr",
        True,
    )


def test_passport_is_tamper_evident_and_reviewable(tmp_path):
    builder = EvidencePassportBuilder(tmp_path / "passports")
    passport = builder.build("INCIDENT-1", face_result(), plate_result())
    assert passport.verify_integrity()
    destination = builder.save(passport)
    loaded = builder.load(destination)
    assert loaded.verify_integrity()
    loaded.decision_state = "ALTERED"
    assert not loaded.verify_integrity()
    passport.review("JUDGE-1", "VERIFIED", "Confirmed in demo")
    assert passport.verify_integrity()
    assert passport.human_review.status == "VERIFIED"


def test_common_event_and_jsonl_sink(tmp_path):
    event = face_event(
        face_result(),
        datetime(2026, 8, 25, 16, 30, tzinfo=timezone.utc),
        BoundingBox(120, 80, 250, 400),
        "GLOBAL-PERSON",
    )
    payload = event.to_dict()
    assert set(payload) == {
        "event_id",
        "event_type",
        "timestamp",
        "camera_id",
        "entity",
        "detection",
        "severity",
        "metadata",
    }
    assert payload["event_id"].startswith("EVT-")
    assert payload["event_type"] == "watchlist_match"
    assert payload["timestamp"] == "2026-08-25T16:30:00Z"
    assert payload["entity"] == {"entity_id": "GLOBAL-PERSON", "entity_type": "person"}
    assert payload["detection"] == {
        "class": "person",
        "confidence": 0.71,
        "bbox": [120, 80, 250, 400],
        "track_id": 8,
    }
    assert payload["severity"] == "HIGH"
    assert payload["metadata"]["review_status"] == "PENDING_HUMAN_REVIEW"
    assert "face_consensus" in payload["metadata"]["evidence"]
    sink = JsonlEventSink(tmp_path / "events.jsonl")
    sink.publish(event)
    assert event.event_id in sink.path.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        face_event(face_result(event_ready=False), datetime.now(timezone.utc), BoundingBox(1, 1, 2, 2))


def test_plate_event_uses_shared_backend_schema():
    payload = plate_event(
        plate_result(),
        datetime.now(timezone.utc),
        "CAM-B",
        BoundingBox(40, 60, 600, 330),
        91,
        "VEHICLE-007",
    ).to_dict()
    assert payload["event_type"] == "plate_detected"
    assert payload["camera_id"] == "CAM-B"
    assert payload["entity"] == {"entity_id": "VEHICLE-007", "entity_type": "vehicle"}
    assert payload["detection"]["class"] == "vehicle"
    assert payload["detection"]["track_id"] == 91
    assert payload["severity"] == "MEDIUM"
    assert payload["metadata"]["plate_text"] == "MH12AB1234"


def test_common_event_rejects_unapproved_backend_values():
    kwargs = dict(
        event_id="EVT-TEST",
        event_type="watchlist_match",
        timestamp=datetime.now(timezone.utc),
        camera_id="CAM-A",
        entity_id="G-1",
        entity_type="person",
        detection=EventDetection("person", 0.9, BoundingBox(1, 1, 2, 2), 1),
        severity="HIGH",
    )
    with pytest.raises(ValueError, match="Unsupported event_type"):
        CommonEvent(**(kwargs | {"event_type": "WATCHLIST_MATCH_CANDIDATE"}))
    with pytest.raises(ValueError, match="Unsupported severity"):
        CommonEvent(**(kwargs | {"severity": "high"}))
