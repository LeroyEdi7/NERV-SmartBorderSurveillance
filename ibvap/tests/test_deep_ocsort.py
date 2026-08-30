"""Unit tests for Deep-OC-SORT tracker."""

import numpy as np
from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.models import Detection
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder
from ibvap.ai.tracking.deep_ocsort import DeepOCSORTTracker


def test_deep_ocsort_tracking_update():
    cfg = TrackingConfig(high_thresh=0.5, low_thresh=0.1, max_age=5)
    embedder = HistogramEmbedder()
    tracker = DeepOCSORTTracker(cfg=cfg, embedder=embedder)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dets = [Detection(bbox=(100.0, 100.0, 200.0, 300.0), score=0.9, class_name="person")]

    tracks = tracker.update(dets, frame, camera_id="cam1", now_ts=100.0)
    assert len(tracks) == 1
    assert tracks[0].track_id == 1
    assert tracks[0].time_since_update == 0


def test_deep_ocsort_occlusion_recovery():
    cfg = TrackingConfig(high_thresh=0.5, low_thresh=0.1, max_age=10)
    embedder = HistogramEmbedder()
    tracker = DeepOCSORTTracker(cfg=cfg, embedder=embedder)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Frame 1: person appears
    dets1 = [Detection(bbox=(100.0, 100.0, 200.0, 300.0), score=0.9, class_name="person")]
    tracks1 = tracker.update(dets1, frame, camera_id="cam1", now_ts=100.0)
    assert len(tracks1) == 1
    tid = tracks1[0].track_id

    # Frame 2-3: person disappears (occlusion)
    tracker.update([], frame, camera_id="cam1", now_ts=101.0)
    tracker.update([], frame, camera_id="cam1", now_ts=102.0)

    # Frame 4: person re-appears near predicted location
    dets4 = [Detection(bbox=(105.0, 105.0, 205.0, 305.0), score=0.88, class_name="person")]
    tracks4 = tracker.update(dets4, frame, camera_id="cam1", now_ts=103.0)
    assert len(tracks4) == 1
    assert tracks4[0].track_id == tid  # Track ID preserved across occlusion
