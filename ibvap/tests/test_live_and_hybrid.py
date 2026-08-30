from __future__ import annotations

import numpy as np
import pytest

from ibvap.configs.config import TrackingConfig
from ibvap.ai.detection import DummyDetector, YoloDetector, build_detector
from ibvap.ai.tracking.models import Detection
from src.pipeline import SyntheticVideoCapture, _open_source
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder
from ibvap.ai.tracking.hybrid import HybridTracker, MockIdentityBinder


def test_synthetic_video_capture():
    cap = SyntheticVideoCapture(width=320, height=240, max_frames=5)
    assert cap.isOpened() is True
    frames_read = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        assert frame.shape == (240, 320, 3)
        frames_read += 1
    assert frames_read == 5
    assert cap.isOpened() is False


def test_open_source_synthetic_fallback():
    cap = _open_source(source="synthetic", dummy=True)
    assert isinstance(cap, SyntheticVideoCapture)


def test_hybrid_bytetrack_deepsort_pipeline():
    cfg = TrackingConfig(high_thresh=0.5, low_thresh=0.1)
    embedder = HistogramEmbedder()
    tracker = HybridTracker(cfg, embedder)
    binder = MockIdentityBinder(tracker)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Frame 1: Detections (high confidence ByteTrack match + DeepSORT visual embedding generation)
    dets_f1 = [
        Detection(bbox=(100, 100, 200, 300), score=0.9, class_name="person"),
    ]
    active_f1 = tracker.update(frame, dets_f1, camera_id="CAM-01", now_ts=1.0)
    assert len(active_f1) == 1
    tid = active_f1[0].track_id

    # Bind mock biometric Face ID
    binder.bind_entity(tid, entity_id="PERSON-42", entity_type="person")
    assert active_f1[0].entity_id == "PERSON-42"

    # Frame 2: Person moves slightly, ByteTrack matches via Kalman/IoU
    dets_f2 = [
        Detection(bbox=(105, 102, 205, 302), score=0.88, class_name="person"),
    ]
    active_f2 = tracker.update(frame, dets_f2, camera_id="CAM-01", now_ts=2.0)
    assert len(active_f2) == 1
    assert active_f2[0].track_id == tid

    # Verify embeddings history stored for DeepSORT occlusion recovery branch
    assert len(active_f2[0].embeddings) > 0


def test_build_detector_yolo_fallback():
    cfg = TrackingConfig(yolo_model="yolov8n.pt")
    # If ultralytics is installed, YoloDetector should build; otherwise build_detector gracefully falls back or raises expected exception
    try:
        det = build_detector(cfg, dummy=False)
        assert isinstance(det, YoloDetector)
    except ImportError:
        # Expected if ultralytics is not installed in local python environment
        pass
