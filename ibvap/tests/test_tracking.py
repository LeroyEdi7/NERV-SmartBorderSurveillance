import numpy as np

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.models import Detection
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder
from ibvap.ai.tracking.hybrid import HybridTracker
from ibvap.ai.tracking.lost_tracks import LostTrackBuffer
from ibvap.ai.tracking.bytetrack import ByteTracker


def _box(x):
    return (float(x), 40.0, float(x + 40), 160.0)


def test_bytetrack_keeps_id_across_frames():
    cfg = TrackingConfig(high_thresh=0.5, low_thresh=0.1, match_iou=0.3, max_age=10, min_hits=1)
    bt = ByteTracker(cfg)
    ids = []
    for x in range(10, 80, 5):
        dets = [Detection(bbox=_box(x), score=0.9, class_name="person")]
        active, _, _ = bt.update(dets, camera_id="cam1", now_ts=x / 25.0)
        ids.append(active[0].track_id)
    assert len(set(ids)) == 1


def test_lost_buffer_recovers_then_expires():
    cfg = TrackingConfig(
        fps=1.0,
        occlusion_ttl_sec=5.0,
        reid_cosine_threshold=0.7,
        lost_track_distance_gate_px=500,
        lost_track_iou_gate=0.0,
        embedding_buffer_size=5,
    )
    buf = LostTrackBuffer(cfg)
    emb = np.ones(8, dtype=np.float32)
    from ibvap.ai.tracking.models import Track

    lost = Track(
        track_id=42,
        bbox=_box(10),
        score=0.9,
        class_name="person",
        embeddings=[emb],
        camera_id="cam1",
        last_seen_ts=0.0,
        velocity=(0.0, 0.0),
    )
    buf.ingest([lost], now_ts=0.0)
    det = Detection(bbox=_box(20), score=0.95, class_name="person", embedding=emb)
    recovered = buf.try_recover([det], [0], camera_id="cam1", now_ts=3.0)
    assert recovered[0][0] == 42
    assert recovered[0][1] > 0.99

    buf.ingest([lost], now_ts=0.0)
    assert buf.try_recover([det], [0], camera_id="cam1", now_ts=9.0) == {}


def test_hybrid_occlusion_reuses_id():
    cfg = TrackingConfig(
        fps=5.0,
        high_thresh=0.5,
        max_age=2,
        min_hits=1,
        occlusion_ttl_sec=10.0,
        reid_cosine_threshold=0.5,
        lost_track_distance_gate_px=400,
        lost_track_iou_gate=0.0,
        embedding_buffer_size=5,
        embedder="histogram",
    )
    tracker = HybridTracker(cfg, HistogramEmbedder())
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    def paint(x):
        img = frame.copy()
        img[40:160, int(x) : int(x) + 40] = (0, 200, 40)
        return img

    last_id = None
    for i, x in enumerate(range(20, 80, 8)):
        img = paint(x)
        dets = [Detection(bbox=_box(x), score=0.9, class_name="person")]
        tracks = tracker.update(img, dets, camera_id="cam1", now_ts=i / 5.0)
        last_id = tracks[0].track_id

    gap_start = 20.0
    for j in range(6):
        tracks = tracker.update(frame, [], camera_id="cam1", now_ts=gap_start + j / 5.0)
        assert tracks == []

    img = paint(88)
    tracks = tracker.update(
        img,
        [Detection(bbox=_box(88), score=0.92, class_name="person")],
        camera_id="cam1",
        now_ts=gap_start + 2.0,
    )
    assert tracks[0].track_id == last_id
    assert tracks[0].re_identification_confidence is not None
