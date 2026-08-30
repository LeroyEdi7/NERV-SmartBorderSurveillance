import numpy as np

from ibvap.configs.config import CameraTopology, TrackingConfig, TransitWindow
from ibvap.ai.tracking.handoff.gallery import CrossCameraHandoff, InMemoryGalleryStore
from ibvap.ai.tracking.models import ExitRecord


def _vec(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.normal(size=32).astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-8)


def _cfg():
    topo = CameraTopology(
        cameras={
            "cam1": {"cam2": TransitWindow(expected_transit_sec=5.0, margin_sec=2.0)},
            "cam2": {"cam1": TransitWindow(expected_transit_sec=5.0, margin_sec=2.0)},
        }
    )
    return TrackingConfig(reid_cosine_threshold=0.7, gallery_ambiguity_gap=0.05, topology=topo)


def _exit(track_id: int, camera: str, ts: float, seed: int, expiry: float = 100.0) -> ExitRecord:
    return ExitRecord(
        track_id=track_id,
        embeddings=[_vec(seed)],
        bbox=(0, 0, 10, 20),
        velocity=(1.0, 0.0),
        heading=(1.0, 0.0),
        camera_id=camera,
        class_name="person",
        exit_timestamp=ts,
        expiry_time=expiry,
    )


def test_time_window_and_match():
    handoff = CrossCameraHandoff(_cfg(), store=InMemoryGalleryStore())
    handoff.store.push(_exit(11, "cam1", ts=0.0, seed=1, expiry=50.0))
    query = _vec(1)
    assert handoff.try_match(query, "cam2", "person", now_ts=1.0) is None  # too soon
    assert handoff.try_match(query, "cam2", "person", now_ts=20.0) is None  # too late
    match = handoff.try_match(query, "cam2", "person", now_ts=5.0)
    assert match is not None
    assert match[0] == 11
    assert match[1] > 0.99


def test_stale_gallery_ignored():
    handoff = CrossCameraHandoff(_cfg(), store=InMemoryGalleryStore())
    handoff.store.push(_exit(11, "cam1", ts=0.0, seed=1, expiry=4.0))
    assert handoff.try_match(_vec(1), "cam2", "person", now_ts=10.0) is None


def test_ambiguous_pair_fails_closed():
    handoff = CrossCameraHandoff(_cfg(), store=InMemoryGalleryStore())
    shared = _vec(9)
    a = _exit(1, "cam1", ts=0.0, seed=9, expiry=50.0)
    b = _exit(2, "cam1", ts=0.0, seed=9, expiry=50.0)
    a.embeddings = [shared]
    b.embeddings = [shared * 0.999]
    handoff.store.push(a)
    handoff.store.push(b)
    assert handoff.try_match(shared, "cam2", "person", now_ts=5.0) is None


def test_missing_topology_fails_closed():
    handoff = CrossCameraHandoff(TrackingConfig(topology=CameraTopology()), store=InMemoryGalleryStore())
    handoff.store.push(_exit(11, "cam1", ts=0.0, seed=1, expiry=50.0))
    assert handoff.try_match(_vec(1), "cam2", "person", now_ts=5.0) is None
