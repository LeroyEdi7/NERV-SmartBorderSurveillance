from __future__ import annotations

import numpy as np
import pytest

from ibvap.configs.config import CameraTopology, TrackingConfig, TransitWindow
from ibvap.ai.tracking.events.publisher import EventPublisher, MockBackendReceiver
from ibvap.ai.tracking.handoff.gallery import CrossCameraHandoff, InMemoryGalleryStore, RedisGalleryStore
from ibvap.ai.tracking.models import Detection, ExitRecord, Track
from src.pipeline import _apply_gallery_match
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder
from ibvap.ai.tracking.hybrid import HybridTracker


def _unit_vec(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=32).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-8)


def _get_config():
    topo = CameraTopology(
        cameras={
            "CAM-01": {"CAM-02": TransitWindow(expected_transit_sec=5.0, margin_sec=3.0)},
            "CAM-02": {"CAM-01": TransitWindow(expected_transit_sec=5.0, margin_sec=3.0)},
        }
    )
    return TrackingConfig(
        exit_margin_px=24,
        reid_cosine_threshold=0.70,
        gallery_ambiguity_gap=0.05,
        topology=topo,
    )


def test_phase5_exit_zone_registration():
    cfg = _get_config()
    store = InMemoryGalleryStore()
    handoff = CrossCameraHandoff(cfg, store=store)

    emb = _unit_vec(10)
    # Track near frame edge (x1 = 10 <= 24px)
    exit_track = Track(
        track_id=101,
        bbox=(10, 100, 50, 200),
        score=0.9,
        class_name="person",
        embeddings=[emb],
    )
    # Track inside frame (x1 = 100 > 24px)
    center_track = Track(
        track_id=102,
        bbox=(100, 100, 200, 300),
        score=0.9,
        class_name="person",
        embeddings=[emb],
    )

    handoff.observe_exits([exit_track, center_track], camera_id="CAM-01", now_ts=10.0, frame_wh=(640, 480))

    candidates = store.candidates(now_ts=10.0)
    assert len(candidates) == 1
    assert candidates[0].track_id == 101
    assert candidates[0].camera_id == "CAM-01"


def test_phase5_transit_time_window_filtering():
    cfg = _get_config()
    store = InMemoryGalleryStore()
    handoff = CrossCameraHandoff(cfg, store=store)

    emb = _unit_vec(20)
    record = ExitRecord(
        track_id=42,
        embeddings=[emb],
        bbox=(0, 0, 20, 50),
        velocity=(0.0, 0.0),
        heading=(0.0, 0.0),
        camera_id="CAM-01",
        class_name="person",
        exit_timestamp=100.0,
        expiry_time=200.0,
    )
    store.push(record)

    # Window is 5.0 ± 3.0 -> [2.0, 8.0] seconds dt
    # Query at dt = 1.0s (now_ts = 101.0) -> Too early
    assert handoff.try_match(emb, camera_id="CAM-02", class_name="person", now_ts=101.0) is None

    # Query at dt = 10.0s (now_ts = 110.0) -> Too late
    assert handoff.try_match(emb, camera_id="CAM-02", class_name="person", now_ts=110.0) is None

    # Query at dt = 5.0s (now_ts = 105.0) -> Valid match
    match = handoff.try_match(emb, camera_id="CAM-02", class_name="person", now_ts=105.0)
    assert match is not None
    assert match[0] == 42
    assert match[1] > 0.99


def test_phase5_ambiguity_gap_rejection():
    cfg = _get_config()
    store = InMemoryGalleryStore()
    handoff = CrossCameraHandoff(cfg, store=store)

    shared_vec = _unit_vec(30)
    # Two candidates in gallery with near-identical embeddings
    rec1 = ExitRecord(
        track_id=1,
        embeddings=[shared_vec],
        bbox=(0, 0, 20, 50),
        velocity=(0.0, 0.0),
        heading=(0.0, 0.0),
        camera_id="CAM-01",
        class_name="person",
        exit_timestamp=100.0,
        expiry_time=200.0,
    )
    rec2 = ExitRecord(
        track_id=2,
        embeddings=[shared_vec * 0.999],  # Cosine diff < 0.05
        bbox=(0, 0, 20, 50),
        velocity=(0.0, 0.0),
        heading=(0.0, 0.0),
        camera_id="CAM-01",
        class_name="person",
        exit_timestamp=100.0,
        expiry_time=200.0,
    )
    store.push(rec1)
    store.push(rec2)

    # Should fail closed and return None due to ambiguity gap filter (< 0.05 margin)
    assert handoff.try_match(shared_vec, camera_id="CAM-02", class_name="person", now_ts=105.0) is None


def test_phase5_dual_camera_handoff_and_event_generation(tmp_path):
    cfg = _get_config()
    cfg.queue_path = str(tmp_path / "test_queue.jsonl")
    store = InMemoryGalleryStore()
    handoff = CrossCameraHandoff(cfg, store=store)

    receiver = MockBackendReceiver()
    publisher = EventPublisher(cfg, mock_receiver=receiver)
    embedder = HistogramEmbedder()
    tracker_cam2 = HybridTracker(cfg, embedder)

    target_emb = _unit_vec(50)
    record = ExitRecord(
        track_id=77,
        embeddings=[target_emb],
        bbox=(5, 100, 45, 200),
        velocity=(1.0, 0.0),
        heading=(1.0, 0.0),
        camera_id="CAM-01",
        class_name="person",
        exit_timestamp=10.0,
        expiry_time=50.0,
    )
    store.push(record)

    # Target appears on CAM-02 at now_ts = 15.0s (5.0s dt)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    det = [Detection(bbox=(100, 100, 150, 250), score=0.9, class_name="person")]
    tracks = tracker_cam2.update(frame, det, camera_id="CAM-02", now_ts=15.0)

    # Force track embedding to match target_emb for deterministic Re-ID match test
    tracks[0].embeddings = [target_emb]

    # Apply gallery matching
    _apply_gallery_match(tracker_cam2, handoff, tracks, camera_id="CAM-02", now_ts=15.0, publisher=publisher)

    # Verify track ID reassigned from local ByteTrack ID to target's original ID (77)
    assert tracks[0].track_id == 77
    assert tracks[0].re_identification_confidence is not None
    assert tracks[0].re_identification_confidence > 0.95

    # Verify cross_camera_match event emitted
    events = receiver.get_events()
    match_events = [e for e in events if e["event_type"] == "cross_camera_match"]
    assert len(match_events) == 1
    assert match_events[0]["detection"]["track_id"] == 77
    assert match_events[0]["camera_id"] == "CAM-02"


def test_phase5_redis_store_fail_closed():
    # Attempting to initialize Redis store with non-existent server should fail gracefully when pushed or queried
    store = RedisGalleryStore(url="redis://127.0.0.1:9999/0")
    record = ExitRecord(
        track_id=99,
        embeddings=[_unit_vec(1)],
        bbox=(0, 0, 10, 10),
        velocity=(0, 0),
        heading=(0, 0),
        camera_id="CAM-01",
        class_name="person",
        exit_timestamp=1.0,
        expiry_time=10.0,
    )

    # Must not raise an unhandled exception
    store.push(record)
    candidates = store.candidates(now_ts=5.0)
    assert candidates == []
