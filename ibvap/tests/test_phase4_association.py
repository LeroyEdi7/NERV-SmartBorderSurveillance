from __future__ import annotations

from src.association.person_vehicle import PersonVehicleAssociator
from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.events.publisher import EventPublisher
from src.events.severity import determine_severity
from ibvap.ai.tracking.models import Track


def test_phase4_person_vehicle_association_confirmed_entry():
    cfg = TrackingConfig(overlap_threshold=0.5, fps=10.0, min_duration_sec=0.3, confirm_on_disappear=True)
    associator = PersonVehicleAssociator(cfg)

    v_track = Track(track_id=2, bbox=(100, 100, 400, 300), score=0.9, class_name="vehicle")
    p_track = Track(track_id=1, bbox=(150, 150, 250, 250), score=0.88, class_name="person")

    # 3 frames of sustained overlap
    for step in range(3):
        events = associator.update([v_track, p_track], now_ts=1.0 + step * 0.1)
        assert len(events) == 0  # confirm_on_disappear is True, waiting for disappearance

    # Person disappears inside vehicle bbox
    events_disappear = associator.update([v_track], now_ts=1.5)
    assert len(events_disappear) == 1
    evt = events_disappear[0]
    assert evt["event_type"] == "vehicle_person_association"
    assert evt["track_id"] == 1
    assert evt["metadata"]["vehicle_track_id"] == 2
    assert evt["metadata"]["confirmed_enter"] is True


def test_phase4_person_vehicle_association_walk_past_suppression():
    cfg = TrackingConfig(overlap_threshold=0.5, fps=10.0, min_duration_sec=0.2, confirm_on_disappear=True)
    associator = PersonVehicleAssociator(cfg)


    v_track = Track(track_id=2, bbox=(100, 100, 400, 300), score=0.9, class_name="vehicle")
    p_track = Track(track_id=1, bbox=(150, 150, 250, 250), score=0.88, class_name="person")

    # Person overlaps vehicle briefly
    associator.update([v_track, p_track], now_ts=1.0)
    associator.update([v_track, p_track], now_ts=1.1)

    # Person walks past and moves away from vehicle (overlap ends while person is still visible)
    p_track_far = Track(track_id=1, bbox=(500, 500, 550, 600), score=0.88, class_name="person")
    events_walk_past = associator.update([v_track, p_track_far], now_ts=1.2)

    # No false-positive vehicle_person_association event emitted
    assert len(events_walk_past) == 0


def test_phase4_severity_mapping():
    assert determine_severity("vehicle_person_association", confidence=0.90) == "HIGH"
    assert determine_severity("vehicle_person_association", confidence=0.70) == "MEDIUM"
    assert determine_severity("vehicle_person_association", confidence=0.40) == "LOW"
    assert determine_severity("person_detected", confidence=0.95) == "LOW"
