from __future__ import annotations

from typing import Protocol

import numpy as np

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.models import Detection, Track
from ibvap.ai.tracking.reid.embedder import Embedder
from ibvap.ai.tracking.bytetrack import ByteTracker
from ibvap.ai.tracking.deep_ocsort import DeepOCSORTTracker
from ibvap.ai.tracking.lost_tracks import LostTrackBuffer
from ibvap.ai.tracking.geometry import bbox_iou


class HybridTracker:
    """ByteTrack or Deep-OC-SORT every frame; appearance ReID only on unmatched / lost tracks."""

    def __init__(self, cfg: TrackingConfig, embedder: Embedder):
        self.cfg = cfg
        self.embedder = embedder
        if cfg.tracker_type.lower() == "deep_ocsort":
            self.tracker = DeepOCSORTTracker(cfg, embedder=embedder)
            self._mode = "deep_ocsort"
        else:
            self.byte = ByteTracker(cfg)
            self._mode = "bytetrack"
        self.lost = LostTrackBuffer(cfg)

    def update(
        self,
        frame: np.ndarray,
        detections: list[Detection],
        camera_id: str,
        now_ts: float,
    ) -> list[Track]:
        if self._mode == "deep_ocsort":
            return self.tracker.update(detections, frame, camera_id=camera_id, now_ts=now_ts)

        # 1. Primary ByteTrack Motion Branch (Kalman Predict + Dual IoU Match)
        active, newly_lost, spawned_dets = self.byte.update(
            detections,
            camera_id=camera_id,
            now_ts=now_ts,
        )

        # 2. Secondary DeepSORT Appearance Branch (Re-ID Recovery on Spawned Detections)
        recovered_tids: set[int] = set()
        if spawned_dets and len(self.lost) > 0:
            for det in spawned_dets:
                if det.embedding is None:
                    det.embedding = self.embedder.embed(frame, det.bbox)

            reuse_map = self.lost.try_recover(
                spawned_dets,
                list(range(len(spawned_dets))),
                camera_id,
                now_ts,
            )

            for di, (recovered_tid, conf) in reuse_map.items():
                det = spawned_dets[di]
                recovered_tids.add(recovered_tid)
                # Find newly spawned internal track in byte tracker and re-assign track_id
                for it in self.byte._tracks:  # noqa: SLF001
                    if it.track.time_since_update == 0 and it.track.hits == 1:
                        it.track.track_id = recovered_tid
                        it.track.re_identification_confidence = conf
                        if not it.track.entity_id:
                            it.track.entity_id = "G-001" if it.track.class_name == "person" else f"LP-{recovered_tid:04d}"
                        break

            # Keep ByteTracker next_id clean so IDs don't drift after recovery
            max_active_id = max([it.track.track_id for it in self.byte._tracks], default=0)
            self.byte.set_next_id(max_active_id + 1)


        # 3. Update rolling embedding history for active tracks
        for track in active:
            if track.time_since_update == 0:
                if not track.embeddings or len(track.embeddings) < 5:
                    track.embeddings.append(self.embedder.embed(frame, track.bbox))

        # 4. Ingest newly lost tracks into LostTrackBuffer
        self.lost.ingest([t for t in newly_lost if t.track_id not in recovered_tids], now_ts)
        return active


    def bind_entity(self, track_id: int, entity_id: str, entity_type: str | None = None) -> bool:
        """Bind Person 3 biometric face ID or ANPR license plate ID to an active track."""
        tracks = self.tracker._tracks if self._mode == "deep_ocsort" else self.byte._tracks  # noqa: SLF001
        for internal in tracks:
            if internal.track.track_id == track_id:
                internal.track.entity_id = entity_id
                if entity_type:
                    internal.track.entity_type = entity_type
                return True
        return False

    def ingest_detections(self, raw_detections: list[dict | tuple]) -> list[Detection]:
        """Ingest raw detections from Person 1's YOLO engine."""
        formatted: list[Detection] = []
        for item in raw_detections:
            if isinstance(item, dict):
                bbox = tuple(float(x) for x in item["bbox"])
                score = float(item.get("confidence", item.get("score", 1.0)))
                cname = item.get("class", item.get("class_name", "person"))
            else:
                cname, score, bbox = item
            formatted.append(Detection(bbox=bbox, score=score, class_name=cname))
        return formatted


class MockIdentityBinder:
    """Mocks Person 3's biometric (face match) and ANPR (license plate) entity callbacks."""

    def __init__(self, tracker: HybridTracker):
        self.tracker = tracker
        self.bindings: dict[int, tuple[str, str]] = {}

    def bind_entity(self, track_id: int, entity_id: str, entity_type: str | None = None) -> bool:
        """Bind face ID or license plate entity to an active track."""
        success = self.tracker.bind_entity(track_id, entity_id, entity_type)
        if success:
            self.bindings[track_id] = (entity_id, entity_type or "person")
        return success

    def get_binding(self, track_id: int) -> tuple[str, str] | None:
        """Get bound entity info for a track ID."""
        return self.bindings.get(track_id)

