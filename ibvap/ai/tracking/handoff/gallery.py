from __future__ import annotations

from typing import Protocol

import numpy as np

from ibvap.configs.config import CameraTopology, TrackingConfig
from ibvap.ai.tracking.geometry import heading_from_velocity, max_cosine, near_frame_edge
from ibvap.ai.tracking.models import ExitRecord, Track


class GalleryStore(Protocol):
    def push(self, record: ExitRecord) -> None: ...
    def candidates(self, now_ts: float) -> list[ExitRecord]: ...
    def remove(self, track_id: int, camera_id: str) -> None: ...
    def expire(self, now_ts: float) -> None: ...


class InMemoryGalleryStore:
    def __init__(self) -> None:
        self._records: list[ExitRecord] = []

    def push(self, record: ExitRecord) -> None:
        self._records.append(record)

    def candidates(self, now_ts: float) -> list[ExitRecord]:
        self.expire(now_ts)
        return list(self._records)

    def remove(self, track_id: int, camera_id: str) -> None:
        self._records = [
            r for r in self._records if not (r.track_id == track_id and r.camera_id == camera_id)
        ]

    def expire(self, now_ts: float) -> None:
        self._records = [r for r in self._records if r.expiry_time >= now_ts]


class RedisGalleryStore:
    """Shared recent-exits gallery for multi-process cameras. Fail closed if Redis is down or package missing."""

    def __init__(self, url: str = "redis://localhost:6379/0", key: str = "tracking:exits"):
        import json

        self._json = json
        self._key = key
        try:
            import redis
            self._r = redis.Redis.from_url(url, decode_responses=True)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("RedisGalleryStore initialization failed: %s", exc)
            self._r = None

    def push(self, record: ExitRecord) -> None:
        if self._r is None:
            return
        payload = {
            "track_id": record.track_id,
            "embeddings": [e.tolist() for e in record.embeddings],
            "bbox": list(record.bbox),
            "velocity": list(record.velocity),
            "heading": list(record.heading),
            "camera_id": record.camera_id,
            "class_name": record.class_name,
            "exit_timestamp": record.exit_timestamp,
            "expiry_time": record.expiry_time,
        }
        try:
            self._r.rpush(self._key, self._json.dumps(payload))
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("RedisGalleryStore.push failed: %s", exc)

    def _parse_all(self) -> list[tuple[str, ExitRecord]]:
        try:
            raw = self._r.lrange(self._key, 0, -1)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("RedisGalleryStore._parse_all failed: %s", exc)
            return []
        parsed: list[tuple[str, ExitRecord]] = []
        for item in raw:
            try:
                data = self._json.loads(item)
                rec = ExitRecord(
                    track_id=int(data["track_id"]),
                    embeddings=[np.asarray(e, dtype=np.float32) for e in data["embeddings"]],
                    bbox=tuple(data["bbox"]),
                    velocity=tuple(data["velocity"]),
                    heading=tuple(data["heading"]),
                    camera_id=data["camera_id"],
                    class_name=data["class_name"],
                    exit_timestamp=float(data["exit_timestamp"]),
                    expiry_time=float(data["expiry_time"]),
                )
                parsed.append((item, rec))
            except Exception:
                continue
        return parsed

    def candidates(self, now_ts: float) -> list[ExitRecord]:
        try:
            parsed = self._parse_all()
            keep: list[str] = []
            records: list[ExitRecord] = []
            for item, rec in parsed:
                if rec.expiry_time < now_ts:
                    continue
                keep.append(item)
                records.append(rec)
            pipe = self._r.pipeline()
            pipe.delete(self._key)
            if keep:
                pipe.rpush(self._key, *keep)
            pipe.execute()
            return records
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("RedisGalleryStore.candidates failed: %s", exc)
            return []

    def remove(self, track_id: int, camera_id: str) -> None:
        try:
            keep = [
                item
                for item, rec in self._parse_all()
                if not (rec.track_id == track_id and rec.camera_id == camera_id)
            ]
            pipe = self._r.pipeline()
            pipe.delete(self._key)
            if keep:
                pipe.rpush(self._key, *keep)
            pipe.execute()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("RedisGalleryStore.remove failed: %s", exc)

    def expire(self, now_ts: float) -> None:
        self.candidates(now_ts)


class CrossCameraHandoff:
    def __init__(self, cfg: TrackingConfig, store: GalleryStore | None = None):
        self.cfg = cfg
        self.store = store or InMemoryGalleryStore()
        self._seen_ids: set[int] = set()
        self._exited: set[int] = set()

    def observe_exits(
        self,
        tracks: list[Track],
        camera_id: str,
        now_ts: float,
        frame_wh: tuple[int, int],
    ) -> None:
        for track in tracks:
            self._seen_ids.add(track.track_id)
            if track.track_id in self._exited:
                continue
            if not near_frame_edge(track.bbox, frame_wh, self.cfg.exit_margin_px):
                continue
            if not track.embeddings:
                continue
            record = ExitRecord(
                track_id=track.track_id,
                embeddings=list(track.embeddings[-self.cfg.embedding_buffer_size :]),
                bbox=track.bbox,
                velocity=track.velocity,
                heading=heading_from_velocity(track.velocity),
                camera_id=camera_id,
                class_name=track.class_name,
                exit_timestamp=now_ts,
                expiry_time=now_ts + self.cfg.embedding_retention_sec,
            )
            self.store.push(record)
            self._exited.add(track.track_id)

    def try_match(
        self,
        embedding: np.ndarray,
        camera_id: str,
        class_name: str,
        now_ts: float,
        topology: CameraTopology | None = None,
    ) -> tuple[int, float] | None:
        """Return (track_id, confidence) or None. Ambiguous pairs fail closed (new ID)."""
        topology = topology or self.cfg.topology
        if not topology.cameras:
            return None
        gallery = self.store.candidates(now_ts)
        scored: list[tuple[float, ExitRecord]] = []
        for rec in gallery:
            if rec.class_name != class_name:
                continue
            if rec.camera_id == camera_id:
                continue
            window = topology.window(rec.camera_id, camera_id)
            if window is None:
                continue
            dt = now_ts - rec.exit_timestamp
            if dt < window.min_sec or dt > window.max_sec:
                continue
            sim = max_cosine(embedding, rec.embeddings)
            scored.append((sim, rec))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        best_sim, best = scored[0]
        if best_sim < self.cfg.reid_cosine_threshold:
            return None
        if len(scored) > 1:
            second = scored[1][0]
            if (best_sim - second) < self.cfg.gallery_ambiguity_gap:
                return None
        self.store.remove(best.track_id, best.camera_id)
        return best.track_id, float(best_sim)
