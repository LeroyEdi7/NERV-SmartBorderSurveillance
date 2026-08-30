from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

ClassName = Literal["person", "vehicle"]


@dataclass(slots=True)
class Detection:
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2
    score: float
    class_name: ClassName
    embedding: np.ndarray | None = None
    proposed_track_id: int | None = None
    re_identification_confidence: float | None = None


@dataclass(slots=True)
class Track:
    track_id: int
    bbox: tuple[float, float, float, float]
    score: float
    class_name: ClassName
    hits: int = 1
    age: int = 0
    time_since_update: int = 0
    velocity: tuple[float, float] = (0.0, 0.0)  # px / frame, cx/cy
    embeddings: list[np.ndarray] = field(default_factory=list)
    re_identification_confidence: float | None = None
    overlap_streak: int = 0
    is_confirmed: bool = False
    camera_id: str = ""
    last_seen_ts: float = 0.0
    entity_id: str | None = None
    entity_type: str | None = None

    @property
    def effective_entity_id(self) -> str:
        if self.entity_id:
            return self.entity_id
        return f"G-{self.track_id:03d}"

    @property
    def cxcy(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def mean_embedding(self) -> np.ndarray | None:
        if not self.embeddings:
            return None
        stacked = np.stack(self.embeddings, axis=0)
        vec = stacked.mean(axis=0)
        norm = float(np.linalg.norm(vec)) + 1e-8
        return vec / norm


@dataclass(slots=True)
class LostTrack:
    track_id: int
    embeddings: list[np.ndarray]
    bbox: tuple[float, float, float, float]
    velocity: tuple[float, float]
    camera_id: str
    class_name: ClassName
    last_seen_ts: float
    expiry_time: float
    last_score: float = 0.0
    entity_id: str | None = None
    entity_type: str | None = None


    def predicted_bbox(self, now_ts: float, fps: float) -> tuple[float, float, float, float]:
        dt_frames = max(0.0, (now_ts - self.last_seen_ts) * fps)
        x1, y1, x2, y2 = self.bbox
        dx, dy = self.velocity
        return (x1 + dx * dt_frames, y1 + dy * dt_frames, x2 + dx * dt_frames, y2 + dy * dt_frames)


@dataclass(slots=True)
class ExitRecord:
    track_id: int
    embeddings: list[np.ndarray]
    bbox: tuple[float, float, float, float]
    velocity: tuple[float, float]
    heading: tuple[float, float]
    camera_id: str
    class_name: ClassName
    exit_timestamp: float
    expiry_time: float


@dataclass(slots=True)
class EventPayload:
    event_type: str
    timestamp: str
    track_id: int | str
    camera_id: str
    bbox: list[float]
    confidence: float
    severity: str
    event_id: str = ""
    entity_id: str = ""
    entity_type: str = "person"
    class_name: str = "person"
    metadata: dict | None = None
    idempotency_key: str = ""

    def to_dict(self) -> dict:
        meta = dict(self.metadata) if self.metadata else {}
        ent_id = self.entity_id or (f"G-{self.track_id:03d}" if isinstance(self.track_id, int) else str(self.track_id))
        payload = {
            "event_id": self.event_id or "EVT-000001",
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "camera_id": self.camera_id,
            "entity": {
                "entity_id": ent_id,
                "entity_type": self.entity_type,
            },
            "detection": {
                "class": self.class_name,
                "confidence": round(float(self.confidence), 3),
                "bbox": [float(x) for x in self.bbox],
                "track_id": self.track_id,
            },
            "severity": self.severity,
            "metadata": meta,
            # Backwards compatibility flat aliases
            "track_id": self.track_id,
            "bbox": [float(x) for x in self.bbox],
            "confidence": round(float(self.confidence), 3),
            "idempotency_key": self.idempotency_key,
        }
        return payload
