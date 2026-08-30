from src.association.person_vehicle import PersonVehicleAssociator
from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.models import Track


def _cfg(**kwargs):
    base = dict(fps=10.0, min_duration_sec=0.3, overlap_threshold=0.6, confirm_on_disappear=True)
    base.update(kwargs)
    return TrackingConfig(**base)


def _tracks(person_bbox, vehicle_bbox, person_id=1, vehicle_id=2):
    return [
        Track(track_id=person_id, bbox=person_bbox, score=0.9, class_name="person"),
        Track(track_id=vehicle_id, bbox=vehicle_bbox, score=0.9, class_name="vehicle"),
    ]


def test_single_frame_brush_does_not_fire():
    assoc = PersonVehicleAssociator(_cfg())
    person_inside = (12, 12, 22, 32)
    vehicle = (0, 0, 80, 80)
    events = assoc.update(_tracks(person_inside, vehicle), now_ts=0.0)
    assert events == []


def test_dwell_then_disappear_emits_association():
    assoc = PersonVehicleAssociator(_cfg())
    person_inside = (12, 12, 22, 32)
    vehicle = (0, 0, 80, 80)
    needed = _cfg().sustained_frames
    for i in range(needed):
        events = assoc.update(_tracks(person_inside, vehicle), now_ts=float(i))
        assert events == []
    # person gone, vehicle remains
    vehicle_only = [Track(track_id=2, bbox=vehicle, score=0.9, class_name="vehicle")]
    events = assoc.update(vehicle_only, now_ts=float(needed))
    assert len(events) == 1
    assert events[0]["event_type"] == "vehicle_person_association"
    assert events[0]["metadata"]["confirmed_enter"] is True


def test_walk_past_does_not_emit():
    assoc = PersonVehicleAssociator(_cfg())
    vehicle = (0, 0, 80, 80)
    inside = (12, 12, 22, 32)
    needed = _cfg().sustained_frames
    for i in range(needed):
        assoc.update(_tracks(inside, vehicle), now_ts=float(i))
    outside = (200, 12, 210, 32)
    events = assoc.update(_tracks(outside, vehicle), now_ts=float(needed + 1))
    assert events == []


def test_emit_on_streak_when_confirm_disabled():
    assoc = PersonVehicleAssociator(_cfg(confirm_on_disappear=False))
    person_inside = (12, 12, 22, 32)
    vehicle = (0, 0, 80, 80)
    needed = _cfg().sustained_frames
    events = []
    for i in range(needed):
        events = assoc.update(_tracks(person_inside, vehicle), now_ts=float(i))
    assert len(events) == 1
