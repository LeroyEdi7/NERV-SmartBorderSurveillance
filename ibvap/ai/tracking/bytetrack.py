from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.geometry import bbox_iou
from ibvap.ai.tracking.models import Detection, Track
from ibvap.ai.tracking.kalman import KalmanBoxFilter


def _linear_assignment(cost: np.ndarray, max_cost: float) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Greedy IoU assignment (cost is 1 - IoU). Good enough for demo-scale counts."""
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
class _InternalTrack:
    track: Track
    kf: KalmanBoxFilter
    start_id: int = 0


@dataclass
class ByteTracker:
    cfg: TrackingConfig
    _next_id: int = 1
    _tracks: list[_InternalTrack] = field(default_factory=list)

    def peek_next_id(self) -> int:
        return self._next_id

    def set_next_id(self, value: int) -> None:
        self._next_id = max(self._next_id, value)

    def _spawn(self, det: Detection, camera_id: str, now_ts: float, track_id: int | None = None) -> _InternalTrack:
        tid = track_id if track_id is not None else self._next_id
        if track_id is None:
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, track_id + 1)
        kf = KalmanBoxFilter(det.bbox)
        track = Track(
            track_id=tid,
            bbox=det.bbox,
            score=det.score,
            class_name=det.class_name,
            hits=1,
            age=1,
            time_since_update=0,
            velocity=kf.velocity(),
            embeddings=[det.embedding] if det.embedding is not None else [],
            camera_id=camera_id,
            last_seen_ts=now_ts,
            is_confirmed=False,
        )
        return _InternalTrack(track=track, kf=kf)

    def _associate(
        self,
        internals: list[_InternalTrack],
        dets: list[Detection],
        iou_thresh: float,
    ) -> tuple[list[tuple[int, int]], list[int], list[int]]:
        if not internals or not dets:
            return [], list(range(len(internals))), list(range(len(dets)))
        cost = np.ones((len(internals), len(dets)), dtype=float)
        for i, it in enumerate(internals):
            pred = it.kf.as_bbox()
            for j, det in enumerate(dets):
                if it.track.class_name != det.class_name:
                    cost[i, j] = 1e6
                    continue
                cost[i, j] = 1.0 - bbox_iou(pred, det.bbox)
        return _linear_assignment(cost, max_cost=1.0 - iou_thresh)

    def update(
        self,
        detections: list[Detection],
        camera_id: str,
        now_ts: float,
        reuse_ids: dict[int, int] | None = None,
    ) -> tuple[list[Track], list[Track], list[Detection]]:
        """
        ByteTrack two-stage matching.

        Detection.proposed_track_id (or reuse_ids[id(det)]) reuses an ID on spawn.

        Returns (active_tracks, newly_lost_tracks, unmatched_high_dets_that_spawned).
        """
        reuse_ids = reuse_ids or {}
        for it in self._tracks:
            it.kf.predict()
            it.track.age += 1
            it.track.time_since_update += 1
            it.track.bbox = it.kf.as_bbox()
            it.track.velocity = it.kf.velocity()

        high = [d for d in detections if d.score >= self.cfg.high_thresh]
        low = [d for d in detections if self.cfg.low_thresh <= d.score < self.cfg.high_thresh]

        matches_h, unmatched_t, unmatched_h = self._associate(self._tracks, high, self.cfg.match_iou)
        remaining_tracks = [self._tracks[i] for i in unmatched_t]
        matches_l, unmatched_t2, _unmatched_l = self._associate(remaining_tracks, low, self.cfg.match_iou)

        matched_internal: set[int] = set()
        for ti, di in matches_h:
            self._apply_detection(self._tracks[ti], high[di], now_ts)
            matched_internal.add(ti)

        rem_index = {id(remaining_tracks[i]): unmatched_t[i] for i in range(len(remaining_tracks))}
        for local_i, di in matches_l:
            global_i = rem_index[id(remaining_tracks[local_i])]
            self._apply_detection(self._tracks[global_i], low[di], now_ts)
            matched_internal.add(global_i)

        newly_lost: list[Track] = []
        still_alive: list[_InternalTrack] = []
        for i, it in enumerate(self._tracks):
            if i in matched_internal:
                still_alive.append(it)
                continue
            if it.track.time_since_update > self.cfg.max_age:
                newly_lost.append(it.track)
            else:
                still_alive.append(it)

        spawned_dets: list[Detection] = []
        for di in unmatched_h:
            det = high[di]
            reuse = det.proposed_track_id if det.proposed_track_id is not None else reuse_ids.get(id(det))
            spawned = self._spawn(det, camera_id, now_ts, track_id=reuse)
            if det.re_identification_confidence is not None:
                spawned.track.re_identification_confidence = det.re_identification_confidence
            still_alive.append(spawned)
            spawned_dets.append(det)

        self._tracks = still_alive
        active: list[Track] = []
        for it in self._tracks:
            it.track.is_confirmed = it.track.hits >= self.cfg.min_hits
            if it.track.time_since_update == 0:
                active.append(it.track)
        return active, newly_lost, spawned_dets

    def _apply_detection(self, it: _InternalTrack, det: Detection, now_ts: float) -> None:
        it.kf.update(det.bbox)
        it.track.bbox = it.kf.as_bbox()
        it.track.score = det.score
        it.track.velocity = it.kf.velocity()
        it.track.time_since_update = 0
        it.track.hits += 1
        it.track.last_seen_ts = now_ts
        if det.embedding is not None:
            it.track.embeddings.append(det.embedding)
            if len(it.track.embeddings) > 32:
                it.track.embeddings = it.track.embeddings[-32:]

    def active_tracks(self) -> list[Track]:
        return [it.track for it in self._tracks if it.track.time_since_update == 0]
