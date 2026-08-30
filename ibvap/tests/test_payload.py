import pytest

from src.events.payload import build_event_payload, make_idempotency_key
from src.events.severity import determine_severity


def test_payload_validation_and_rounding():
    payload = build_event_payload(
        event_type="vehicle_person_association",
        track_id=7,
        bbox=(1, 2, 3, 4),
        camera_id="cam1",
        confidence=0.8766,
        severity="HIGH",
        extra={"vehicle_track_id": 2},
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert payload["confidence"] == 0.877
    assert payload["metadata"]["vehicle_track_id"] == 2
    assert payload["idempotency_key"] == make_idempotency_key(7, "vehicle_person_association", payload["timestamp"])


def test_retries_share_idempotency_key():
    ts = "2026-01-01T00:00:00+00:00"
    a = build_event_payload("cross_camera_match", 3, [0, 0, 1, 1], "cam2", 0.91, "MEDIUM", timestamp=ts)
    b = build_event_payload("cross_camera_match", 3, [0, 0, 1, 1], "cam2", 0.91, "MEDIUM", timestamp=ts)
    assert a["idempotency_key"] == b["idempotency_key"]


def test_invalid_event_type_and_bbox():
    with pytest.raises(ValueError, match="Invalid event_type"):
        build_event_payload("nope", 1, [0, 0, 1, 1], "cam1", 0.5, "LOW")
    with pytest.raises(ValueError, match="Malformed bbox"):
        build_event_payload("cross_camera_match", 1, [0, 0, 1], "cam1", 0.5, "LOW")
    with pytest.raises(ValueError, match="Invalid severity"):
        build_event_payload("cross_camera_match", 1, [0, 0, 1, 1], "cam1", 0.5, "CRITICAL")


def test_severity_mapping():
    assert determine_severity("vehicle_person_association", 0.9) == "HIGH"
    assert determine_severity("vehicle_person_association", 0.7) == "MEDIUM"
    assert determine_severity("vehicle_person_association", 0.4) == "LOW"
    assert determine_severity("cross_camera_match", 0.95) == "MEDIUM"
    assert determine_severity("cross_camera_match", 0.7) == "LOW"
    assert determine_severity("unknown", 1.0) == "LOW"


def test_official_screenshot_schema():
    payload = build_event_payload(
        event_type="person_detected",
        track_id=17,
        bbox=[120, 80, 250, 400],
        camera_id="BOP-01",
        confidence=0.94,
        severity="LOW",
        entity_id="G-017",
        entity_type="person",
        event_id="EVT-000001",
        timestamp="2026-08-25T16:30:00Z",
    )
    assert payload["event_id"] == "EVT-000001"
    assert payload["event_type"] == "person_detected"
    assert payload["timestamp"] == "2026-08-25T16:30:00Z"
    assert payload["camera_id"] == "BOP-01"
    assert payload["entity"] == {"entity_id": "G-017", "entity_type": "person"}
    assert payload["detection"] == {
        "class": "person",
        "confidence": 0.94,
        "bbox": [120.0, 80.0, 250.0, 400.0],
        "track_id": 17,
    }
    assert payload["severity"] == "LOW"

