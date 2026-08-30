from __future__ import annotations

import numpy as np

from ibvap.configs.config import TrackingConfig
from ibvap.ai.detection import DummyDetector
from ibvap.ai.tracking.models import Detection
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder
from ibvap.ai.tracking.hybrid import HybridTracker
from ibvap.ai.tracking.lost_tracks import LostTrackBuffer


def test_phase3_prolonged_occlusion_recovery():
    cfg = TrackingConfig(high_thresh=0.5, occlusion_ttl_sec=8.0, reid_cosine_threshold=0.50)
    embedder = HistogramEmbedder()
    tracker = HybridTracker(cfg, embedder)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Color crop for consistent feature extraction
    frame[100:300, 100:200] = [120, 200, 50]

    # 1. Initial track setup
    dets1 = [Detection(bbox=(100, 100, 200, 300), score=0.92, class_name="person")]
    active1 = tracker.update(frame, dets1, camera_id="CAM-01", now_ts=1.0)
    assert len(active1) == 1
    orig_id = active1[0].track_id

    # 2. Simulate 4 seconds of occlusion (no detections)
    # Track expires from ByteTrack active list after max_age frames and enters LostTrackBuffer
    for step in range(35):
        tracker.update(frame, [], camera_id="CAM-01", now_ts=1.0 + step * 0.1)

    assert len(tracker.byte.active_tracks()) == 0
    assert len(tracker.lost) >= 1

    # 3. Target re-emerges 4 seconds later at new position
    frame[100:300, 300:400] = [120, 200, 50]
    dets_reemerge = [Detection(bbox=(300, 100, 400, 300), score=0.90, class_name="person")]
    active_reemerged = tracker.update(frame, dets_reemerge, camera_id="CAM-01", now_ts=5.5)

    # Verify original track_id was recovered via DeepSORT appearance branch
    assert len(active_reemerged) == 1
    assert active_reemerged[0].track_id == orig_id
    assert active_reemerged[0].re_identification_confidence is not None


def test_phase3_lost_track_ttl_expiration():
    cfg = TrackingConfig(occlusion_ttl_sec=5.0)
    buffer = LostTrackBuffer(cfg)

    # Ingest a track at t=10.0
    from ibvap.ai.tracking.models import Track
    t = Track(
        track_id=1,
        bbox=(10, 10, 50, 100),
        score=0.9,
        class_name="person",
        embeddings=[np.ones(512, dtype=np.float32)],
        camera_id="CAM-01",
        last_seen_ts=10.0,
    )
    buffer.ingest([t], now_ts=10.0)
    assert len(buffer) == 1

    # At t=14.0 (within 5.0s TTL), lost track is still buffered
    buffer.expire(now_ts=14.0)
    assert len(buffer) == 1

    # At t=16.0 (past 5.0s TTL), lost track expires
    buffer.expire(now_ts=16.0)
    assert len(buffer) == 0
