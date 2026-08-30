from __future__ import annotations

import numpy as np
import pytest

from ibvap.configs.config import TrackingConfig
from ibvap.ai.detection import DummyDetector, build_detector
from ibvap.ai.tracking.events import EventPublisher, MockBackendReceiver
from ibvap.ai.tracking.handoff.gallery import InMemoryGalleryStore
from ibvap.ai.tracking.models import ExitRecord
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder

from ibvap.ai.tracking.hybrid import HybridTracker, MockIdentityBinder


def test_dummy_detector_scenarios():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Test normal scenario
    detector = DummyDetector(scenario="normal")
    dets_normal = detector.detect(frame)
    assert len(dets_normal) == 2
    assert any(d.class_name == "person" for d in dets_normal)
    assert any(d.class_name == "vehicle" for d in dets_normal)

    # Test reset
    detector.reset()
    assert detector.frame_index == 0

    # Test occlusion scenario
    detector_occ = DummyDetector(scenario="occlusion")
    for _ in range(19):
        dets = detector_occ.detect(frame)
        assert len(dets) == 1
    # Frames 20-25 should yield no detections (simulating occlusion)
    for _ in range(6):
        dets = detector_occ.detect(frame)
        assert len(dets) == 0
    # Frame 26 re-emerges
    dets_26 = detector_occ.detect(frame)
    assert len(dets_26) == 1

    # Test vehicle_entry scenario
    detector_veh = DummyDetector(scenario="vehicle_entry")
    dets_veh_f1 = detector_veh.detect(frame)
    assert len(dets_veh_f1) == 2  # vehicle + person moving toward vehicle

    # Test build_detector factory function
    cfg = TrackingConfig()
    det_built = build_detector(cfg, dummy=True, scenario="occlusion")
    assert isinstance(det_built, DummyDetector)
    assert det_built.scenario == "occlusion"


def test_mock_identity_binder():
    cfg = TrackingConfig()
    embedder = HistogramEmbedder()
    tracker = HybridTracker(cfg, embedder)
    binder = MockIdentityBinder(tracker)


    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dets = [
        {"class": "person", "confidence": 0.95, "bbox": (50, 50, 100, 200)},
    ]
    formatted = tracker.ingest_detections(dets)
    active = tracker.update(frame, formatted, camera_id="cam1", now_ts=100.0)
    assert len(active) == 1
    track_id = active[0].track_id

    # Bind Face ID
    bound = binder.bind_entity(track_id, entity_id="G-017", entity_type="person")
    assert bound is True
    assert binder.get_binding(track_id) == ("G-017", "person")
    assert active[0].entity_id == "G-017"

    # Bind invalid track ID
    bound_invalid = binder.bind_entity(9999, entity_id="UNKNOWN")
    assert bound_invalid is False


def test_mock_backend_receiver_and_publisher(tmp_path):
    queue_file = str(tmp_path / "test_queue.jsonl")
    cfg = TrackingConfig(queue_path=queue_file)
    mock_receiver = MockBackendReceiver()
    publisher = EventPublisher(cfg, mock_receiver=mock_receiver)

    payload = publisher.emit(
        event_type="person_detected",
        track_id=17,
        bbox=(100.0, 100.0, 200.0, 300.0),
        camera_id="BOP-01",
        confidence=0.94,
        extra={"entity_id": "G-017"},
    )

    assert len(mock_receiver.get_events()) == 1
    received = mock_receiver.get_events()[0]
    assert received["event_id"] == payload["event_id"]
    assert received["camera_id"] == "BOP-01"
    assert received["detection"]["track_id"] == 17

    # Test invalid schema rejection
    with pytest.raises(ValueError, match="Payload schema invalid"):
        mock_receiver.receive({"event_id": "EVT-1"})

    mock_receiver.clear()
    assert len(mock_receiver.get_events()) == 0



def test_in_memory_gallery_store():
    store = InMemoryGalleryStore()
    now_ts = 1000.0

    record1 = ExitRecord(
        track_id=1,
        embeddings=[np.ones(512, dtype=np.float32)],
        bbox=(0, 0, 50, 50),
        velocity=(1, 1),
        heading=(0.707, 0.707),
        camera_id="cam1",
        class_name="person",
        exit_timestamp=now_ts,
        expiry_time=now_ts + 10.0,
    )
    record2 = ExitRecord(
        track_id=2,
        embeddings=[np.ones(512, dtype=np.float32)],
        bbox=(10, 10, 60, 60),
        velocity=(0, 1),
        heading=(0, 1),
        camera_id="cam1",
        class_name="person",
        exit_timestamp=now_ts - 15.0,
        expiry_time=now_ts - 5.0,  # Expired
    )

    store.push(record1)
    store.push(record2)

    # Candidate query should expire record2 automatically
    candidates = store.candidates(now_ts)
    assert len(candidates) == 1
    assert candidates[0].track_id == 1

    # Remove record1
    store.remove(track_id=1, camera_id="cam1")
    assert len(store.candidates(now_ts)) == 0
