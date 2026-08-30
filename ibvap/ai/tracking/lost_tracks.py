from __future__ import annotations

import logging

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.geometry import bbox_iou, center_distance, max_cosine
from ibvap.ai.tracking.models import Detection, LostTrack, Track

logger = logging.getLogger(__name__)


class LostTrackBuffer:
    """Short-lived appearance+motion memory for occlusion recovery."""

    def __init__(self, cfg: TrackingConfig):
        self.cfg = cfg
        self._items: list[LostTrack] = []

    def ingest(self, tracks: list[Track], now_ts: float) -> None:
        ttl = self.cfg.occlusion_ttl_sec
        for track in tracks:
            embeddings = track.embeddings[-self.cfg.embedding_buffer_size :]
            if not embeddings:
                continue
            self._items.append(
                LostTrack(
                    track_id=track.track_id,
                    embeddings=list(embeddings),
                    bbox=track.bbox,
                    velocity=track.velocity,
                    camera_id=track.camera_id,
                    class_name=track.class_name,
                    last_seen_ts=track.last_seen_ts,
                    expiry_time=now_ts + ttl,
                    last_score=track.score,
                    entity_id=track.entity_id,
                    entity_type=track.entity_type,
                )
            )

    def expire(self, now_ts: float) -> None:
        self._items = [item for item in self._items if item.expiry_time >= now_ts]

    def try_recover(
        self,
        detections: list[Detection],
        unmatched_high_indices: list[int],
        camera_id: str,
        now_ts: float,
    ) -> dict[int, tuple[int, float]]:
        """
        Map unmatched high-conf detection index -> (track_id, confidence).
        Uses predicted position gate, then cosine vs last-N embeddings.
        """
        self.expire(now_ts)
        assigned: dict[int, tuple[int, float]] = {}
        used_lost: set[int] = set()

        for di in unmatched_high_indices:
            det = detections[di]
            if det.embedding is None:
                continue
            best_id: int | None = None
            best_sim = -1.0
            best_idx: int | None = None
            
            # Count candidates for this class
            class_candidates = [lost for lost in self._items if lost.camera_id == camera_id and lost.class_name == det.class_name]
            is_single_candidate = len(class_candidates) == 1

            for li, lost in enumerate(self._items):
                if li in used_lost:
                    continue
                if lost.camera_id != camera_id or lost.class_name != det.class_name:
                    continue
                predicted = lost.predicted_bbox(now_ts, self.cfg.fps)
                iou = bbox_iou(predicted, det.bbox)
                dist = center_distance(predicted, det.bbox)

                sim = max_cosine(det.embedding, lost.embeddings)
                spatial_match = (iou >= self.cfg.lost_track_iou_gate) or (dist <= self.cfg.lost_track_distance_gate_px)
                
                if spatial_match:
                    effective_thresh = self.cfg.reid_cosine_threshold
                elif is_single_candidate:
                    effective_thresh = max(0.20, self.cfg.reid_cosine_threshold - 0.45)
                else:
                    effective_thresh = max(0.40, self.cfg.reid_cosine_threshold - 0.20)


                if sim >= effective_thresh and sim > best_sim:
                    best_sim = sim
                    best_id = lost.track_id
                    best_idx = li

            if best_id is not None and best_idx is not None:
                assigned[di] = (best_id, float(best_sim))
                used_lost.add(best_idx)
                logger.info(
                    "re_identification track_id=%s confidence=%.3f camera_id=%s",
                    best_id,
                    best_sim,
                    camera_id,
                )
        self._items = [item for i, item in enumerate(self._items) if i not in used_lost]
        return assigned



    def __len__(self) -> int:
        return len(self._items)
