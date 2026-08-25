"""Tracked-person face recognition service owned by Person 3."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ai.common.config import FaceConfig
from ai.common.image_ops import crop_image, image_sha256
from ai.contracts import (
    BoundingBox,
    EvidenceState,
    FaceFrameResult,
    FaceTrackResult,
    QualityAssessment,
    QualityState,
    TrackObservation,
)
from ai.face.backend import DetectedFace, FaceBackend
from ai.face.consensus import FaceConsensus
from ai.face.quality import assess_face_quality
from ai.face.watchlist import WatchlistStore


@dataclass(frozen=True, slots=True)
class FaceServiceOutput:
    frame: FaceFrameResult | None
    track: FaceTrackResult | None
    skipped_reason: str | None = None


class FaceRecognitionService:
    def __init__(self, backend: FaceBackend, watchlist: WatchlistStore, config: FaceConfig) -> None:
        self.backend = backend
        self.watchlist = watchlist
        self.config = config
        self.consensus = FaceConsensus(config)

    def process(self, observation: TrackObservation) -> FaceServiceOutput:
        if observation.object_type.lower() not in {"person", "human"}:
            return FaceServiceOutput(None, None, "not_a_person_track")
        if observation.frame_id % max(self.config.sample_every_n_frames, 1) != 0:
            return FaceServiceOutput(None, None, "sampling_interval")
        person_crop, person_bbox = crop_image(observation.frame, observation.bbox)
        if person_crop is None or person_bbox is None:
            return FaceServiceOutput(None, None, "empty_person_crop")
        detections = self.backend.detect(person_crop)
        selected = self._select_face(detections)
        if selected is None:
            quality = QualityAssessment(QualityState.UNUSABLE, 0.0, 0.0, 0.0, 0.0, ("face_not_detected",))
            frame_result = FaceFrameResult(
                camera_id=observation.camera_id,
                frame_id=observation.frame_id,
                timestamp=observation.timestamp,
                track_id=observation.track_id,
                face_bbox=None,
                status=EvidenceState.NO_EVIDENCE,
                quality=quality,
                model_name=self.backend.model_name,
                reasons=("face_not_detected",),
            )
            return FaceServiceOutput(frame_result, self.consensus.add(frame_result))

        face_crop, _ = crop_image(person_crop, selected.bbox)
        if face_crop is None:
            return FaceServiceOutput(None, None, "empty_face_crop")
        quality = assess_face_quality(
            face_crop, selected.bbox, selected.detection_score, selected.keypoints, self.config
        )
        absolute_bbox = selected.bbox.translated(person_bbox.x1, person_bbox.y1)
        if quality.state == QualityState.UNUSABLE:
            frame_result = FaceFrameResult(
                camera_id=observation.camera_id,
                frame_id=observation.frame_id,
                timestamp=observation.timestamp,
                track_id=observation.track_id,
                face_bbox=absolute_bbox,
                status=EvidenceState.UNRESOLVED,
                quality=quality,
                embedding=selected.embedding,
                model_name=self.backend.model_name,
                evidence_hash=image_sha256(face_crop),
                reasons=("quality_gate_rejected",),
            )
        else:
            match = self.watchlist.match(
                selected.embedding,
                self.config.possible_threshold,
                self.config.match_threshold,
                self.config.ambiguity_margin,
            )
            frame_result = FaceFrameResult(
                camera_id=observation.camera_id,
                frame_id=observation.frame_id,
                timestamp=observation.timestamp,
                track_id=observation.track_id,
                face_bbox=absolute_bbox,
                status=match.status,
                quality=quality,
                watchlist_id=match.person_id,
                display_name=match.display_name,
                similarity=match.similarity,
                second_best_similarity=match.second_best_similarity,
                embedding=selected.embedding,
                model_name=self.backend.model_name,
                evidence_hash=image_sha256(face_crop),
                reasons=match.reasons,
            )
        return FaceServiceOutput(frame_result, self.consensus.add(frame_result))

    @staticmethod
    def _select_face(detections: list[DetectedFace]) -> DetectedFace | None:
        if not detections:
            return None
        return max(detections, key=lambda item: item.detection_score * max(item.bbox.area, 1.0))
