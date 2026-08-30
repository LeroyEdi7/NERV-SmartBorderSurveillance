from src.association.person_vehicle import evaluate_entry_event
from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.geometry import bbox_overlap_ratio
from ibvap.ai.tracking.models import Track


def test_no_overlap():
    assert bbox_overlap_ratio((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_identical_boxes():
    assert bbox_overlap_ratio((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0


def test_partial_overlap():
    ratio = bbox_overlap_ratio((0, 0, 10, 10), (5, 0, 15, 10))
    assert abs(ratio - 0.5) < 1e-6


def test_person_fully_inside_vehicle():
    assert bbox_overlap_ratio((10, 10, 20, 30), (0, 0, 100, 80)) == 1.0


def test_zero_area_person():
    assert bbox_overlap_ratio((5, 5, 5, 10), (0, 0, 20, 20)) == 0.0


def _track(tid, bbox, name="person", streak=0):
    t = Track(track_id=tid, bbox=bbox, score=0.9, class_name=name)
    t.overlap_streak = streak
    return t


def test_evaluate_entry_event_resets_and_requires_streak():
    cfg = TrackingConfig(fps=10, min_duration_sec=0.3, overlap_threshold=0.6)
    person = _track(1, (0, 0, 10, 10))
    vehicle = _track(2, (50, 50, 80, 80), "vehicle")
    assert evaluate_entry_event(person, vehicle, cfg) is None
    assert person.overlap_streak == 0

    person = _track(1, (10, 10, 20, 30))
    vehicle = _track(2, (0, 0, 100, 80), "vehicle")
    for i in range(cfg.sustained_frames - 1):
        assert evaluate_entry_event(person, vehicle, cfg) is None
    event = evaluate_entry_event(person, vehicle, cfg)
    assert event is not None
    assert event["event_candidate"] == "vehicle_person_association"
    assert event["streak_frames"] == cfg.sustained_frames
