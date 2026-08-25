from datetime import datetime, timezone

import pytest

from ai.contracts import EvidenceState, FaceTrackResult, PlateTrackResult
from ai.evidence.events import JsonlEventSink, face_event
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
    event = face_event(face_result(), datetime.now(timezone.utc), "GLOBAL-PERSON")
    assert event.to_dict()["entity"]["entity_id"] == "GLOBAL-PERSON"
    assert event.status == "PENDING_HUMAN_REVIEW"
    sink = JsonlEventSink(tmp_path / "events.jsonl")
    sink.publish(event)
    assert event.event_id in sink.path.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        face_event(face_result(event_ready=False), datetime.now(timezone.utc))
