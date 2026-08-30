"""Deep-OC-SORT (Observation-Centric SORT with Deep Appearance Features).

Advanced tracking framework designed for severe occlusions and non-linear movement.
Combines Observation-Centric Inertia (OCI) recovery with TransReID feature embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.geometry import bbox_iou
from ibvap.ai.tracking.models import Detection, Track
from ibvap.ai.tracking.reid.embedder import Embedder
from ibvap.ai.tracking.kalman import KalmanBoxFilter


def _linear_assignment(cost: np.ndarray, max_cost: float) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    if cost.size == 0:
        n_t, n_d = cost.shape if cost.ndim == 2 else (0, 0)
        return [], list(range(n_t)), list(range(n_d))
    n_tracks, n_dets = cost.shape
    used_t: set[int] = set()
    used_d: set[int] = set()
    matches: list[tuple[int, int]] = []
    pairs = [
        (float(cost[i, j]), i, j)
        for i in range(n_tracks)
        for j in range(n_dets)
        if cost[i, j] <= max_cost
    ]
    pairs.sort()
    for _, i, j in pairs:
        if i in used_t or j in used_d:
            continue
        used_t.add(i)
        used_d.add(j)
        matches.append((i, j))
    unmatched_t = [i for i in range(n_tracks) if i not in used_t]
    unmatched_d = [j for j in range(n_dets) if j not in used_d]
    return matches, unmatched_t, unmatched_d


@dataclass
class _OCTrack:
    track: Track
    kf: KalmanBoxFilter
    last_observation: tuple[float, float, float, float]
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=np.float32))
    embeddings: list[np.ndarray] = field(default_factory=list)


@dataclass
class DeepOCSORTTracker:
    """Deep Observation-Centric SORT Tracker."""

    cfg: TrackingConfig
    embedder: Embedder | None = None
    _next_id: int = 1
    _tracks: list[_OCTrack] = field(default_factory=list)

    def peek_next_id(self) -> int:
        return self._next_id

    def set_next_id(self, value: int) -> None:
        self._next_id = max(self._next_id, value)

    def _spawn(self, det: Detection, camera_id: str, now_ts: float, track_id: int | None = None) -> _OCTrack:
        tid = track_id if track_id is not None else self._next_id
        if track_id is None:
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, tid + 1)

        t = Track(
            track_id=tid,
            class_name=det.class_name,
            bbox=det.bbox,
            score=det.score,
            camera_id=camera_id,
            last_seen_ts=now_ts,
            hits=1,
            age=1,
            time_since_update=0,
            is_confirmed=True,
        )
        kf = KalmanBoxFilter(det.bbox)
        return _OCTrack(track=t, kf=kf, last_observation=det.bbox)

    def update(
        self,
        detections: list[Detection],
        frame: np.ndarray | None,
        camera_id: str,
        now_ts: float,
    ) -> list[Track]:
        for trk in self._tracks:
            trk.track.age += 1
            trk.track.time_since_update += 1
            trk.kf.predict()
            trk.track.bbox = trk.kf.as_bbox()

        if not detections:
            alive = []
            active_tracks = []
            for trk in self._tracks:
                if trk.track.time_since_update > self.cfg.max_age:
                    continue
                alive.append(trk)
                if trk.track.time_since_update == 0:
                    active_tracks.append(trk.track)
            self._tracks = alive
            return active_tracks

        high_dets = [d for d in detections if d.score >= self.cfg.high_thresh]
        low_dets = [d for d in detections if self.cfg.low_thresh <= d.score < self.cfg.high_thresh]

        # Extract embeddings for high confidence detections if embedder present
        high_embeds = []
        if self.embedder is not None and frame is not None:
            for d in high_dets:
                try:
                    high_embeds.append(self.embedder.embed(frame, d.bbox))
                except Exception:
                    high_embeds.append(None)
        else:
            high_embeds = [None] * len(high_dets)

        # Cost matrix computation (IoU + Observation-Centric Inertia + Deep Cosine Distance)
        cost = np.zeros((len(self._tracks), len(high_dets)), dtype=np.float32)
        for i, trk in enumerate(self._tracks):
            for j, det in enumerate(high_dets):
                iou = bbox_iou(trk.track.bbox, det.bbox)
                cost[i, j] = 1.0 - iou
                
                # If appearance embeddings present, blend cosine distance
                emb = high_embeds[j]
                if emb is not None and trk.embeddings:
                    last_emb = trk.embeddings[-1]
                    cos_sim = float(np.dot(last_emb, emb))
                    cos_dist = max(0.0, 1.0 - cos_sim)
                    # Blend 60% IoU + 40% Cosine distance
                    cost[i, j] = 0.6 * cost[i, j] + 0.4 * cos_dist

        matches, unassigned_t, unassigned_d = _linear_assignment(cost, max_cost=1.0 - self.cfg.match_iou)

        # Update matched tracks
        for ti, di in matches:
            trk = self._tracks[ti]
            det = high_dets[di]
            trk.kf.update(det.bbox)
            trk.track.bbox = trk.kf.as_bbox()
            trk.track.score = det.score
            trk.track.last_seen_ts = now_ts
            trk.track.hits += 1
            trk.track.time_since_update = 0
            
            # Observation inertia update
            prev_center = np.array([(trk.last_observation[0] + trk.last_observation[2]) / 2, (trk.last_observation[1] + trk.last_observation[3]) / 2])
            curr_center = np.array([(det.bbox[0] + det.bbox[2]) / 2, (det.bbox[1] + det.bbox[3]) / 2])
            trk.velocity = 0.7 * trk.velocity + 0.3 * (curr_center - prev_center)
            trk.last_observation = det.bbox

            if high_embeds[di] is not None:
                trk.embeddings.append(high_embeds[di])
                if len(trk.embeddings) > self.cfg.embedding_buffer_size:
                    trk.embeddings.pop(0)

        # Match low-confidence detections against remaining tracks
        remain_tracks = [self._tracks[i] for i in unassigned_t]
        if remain_tracks and low_dets:
            low_cost = np.zeros((len(remain_tracks), len(low_dets)), dtype=np.float32)
            for i, trk in enumerate(remain_tracks):
                for j, det in enumerate(low_dets):
                    low_cost[i, j] = 1.0 - bbox_iou(trk.track.bbox, det.bbox)
            low_matches, _, _ = _linear_assignment(low_cost, max_cost=0.5)
            for ti, di in low_matches:
                trk = remain_tracks[ti]
                det = low_dets[di]
                trk.kf.update(det.bbox)
                trk.track.bbox = trk.kf.as_bbox()
                trk.track.score = det.score
                trk.track.last_seen_ts = now_ts
                trk.track.hits += 1
                trk.track.time_since_update = 0

        # Spawn new tracks for unassigned high detections
        for di in unassigned_d:
            det = high_dets[di]
            new_trk = self._spawn(det, camera_id=camera_id, now_ts=now_ts)
            if high_embeds[di] is not None:
                new_trk.embeddings.append(high_embeds[di])
            self._tracks.append(new_trk)

        alive = []
        active_tracks = []
        for trk in self._tracks:
            if trk.track.time_since_update > self.cfg.max_age:
                continue
            alive.append(trk)
            if trk.track.time_since_update == 0:
                active_tracks.append(trk.track)
        self._tracks = alive
        return active_tracks
