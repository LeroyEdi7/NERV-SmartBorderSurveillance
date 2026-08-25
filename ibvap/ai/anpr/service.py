"""Tracked-vehicle ANPR service owned by Person 3."""

from __future__ import annotations

from dataclasses import dataclass

from ai.anpr.backend import ANPRBackend, DetectedPlate
from ai.anpr.consensus import PlateConsensus
from ai.anpr.india_format import assess_indian_format
from ai.anpr.quality import assess_plate_quality
from ai.common.config import ANPRConfig
from ai.common.image_ops import crop_image, image_sha256
from ai.contracts import (
    EvidenceState,
    PlateFrameResult,
    PlateTrackResult,
    QualityAssessment,
    QualityState,
    TrackObservation,
)


@dataclass(frozen=True, slots=True)
class ANPRServiceOutput:
    frame: PlateFrameResult | None
    track: PlateTrackResult | None
    skipped_reason: str | None = None


class ANPRService:
    def __init__(self, backend: ANPRBackend, config: ANPRConfig) -> None:
        self.backend = backend
        self.config = config
        self.consensus = PlateConsensus(config)

    def process(self, observation: TrackObservation) -> ANPRServiceOutput:
        if observation.object_type.lower() not in {"vehicle", "car", "truck", "bus", "motorcycle"}:
            return ANPRServiceOutput(None, None, "not_a_vehicle_track")
        if observation.frame_id % max(self.config.sample_every_n_frames, 1) != 0:
            return ANPRServiceOutput(None, None, "sampling_interval")
        vehicle_crop, vehicle_bbox = crop_image(observation.frame, observation.bbox)
        if vehicle_crop is None or vehicle_bbox is None:
            return ANPRServiceOutput(None, None, "empty_vehicle_crop")
        detections = self.backend.predict(vehicle_crop)
        selected = self._select_plate(detections)
        group_id = observation.global_entity_id or observation.track_key
        if selected is None:
            quality = QualityAssessment(QualityState.UNUSABLE, 0.0, 0.0, 0.0, 0.0, ("plate_not_detected",))
            frame_result = PlateFrameResult(
                camera_id=observation.camera_id,
                frame_id=observation.frame_id,
                timestamp=observation.timestamp,
                track_id=observation.track_id,
                plate_bbox=None,
                raw_text=None,
                normalized_text=None,
                character_confidences=(),
                detector_confidence=0.0,
                ocr_confidence=0.0,
                status=EvidenceState.NO_EVIDENCE,
                quality=quality,
                model_name=self.backend.model_name,
                reasons=("plate_not_detected",),
            )
            return ANPRServiceOutput(frame_result, self.consensus.add(frame_result, group_id))

        plate_crop, _ = crop_image(vehicle_crop, selected.bbox)
        if plate_crop is None:
            return ANPRServiceOutput(None, None, "empty_plate_crop")
        quality = assess_plate_quality(plate_crop, selected.bbox, self.config)
        grammar = assess_indian_format(selected.text)
        absolute_bbox = selected.bbox.translated(vehicle_bbox.x1, vehicle_bbox.y1)
        status = (
            EvidenceState.UNRESOLVED
            if quality.state == QualityState.UNUSABLE or not grammar.normalized
            else EvidenceState.PARTIAL
        )
        reasons = list(quality.reasons)
        if not grammar.normalized:
            reasons.append("ocr_text_empty")
        frame_result = PlateFrameResult(
            camera_id=observation.camera_id,
            frame_id=observation.frame_id,
            timestamp=observation.timestamp,
            track_id=observation.track_id,
            plate_bbox=absolute_bbox,
            raw_text=selected.text,
            normalized_text=grammar.normalized or None,
            character_confidences=selected.character_confidences,
            detector_confidence=selected.detector_confidence,
            ocr_confidence=selected.ocr_confidence,
            status=status,
            quality=quality,
            grammar_score=grammar.score,
            grammar_suggestion=grammar.suggestion,
            model_name=self.backend.model_name,
            evidence_hash=image_sha256(plate_crop),
            reasons=tuple(reasons),
        )
        return ANPRServiceOutput(frame_result, self.consensus.add(frame_result, group_id))

    @staticmethod
    def _select_plate(detections: list[DetectedPlate]) -> DetectedPlate | None:
        if not detections:
            return None
        return max(
            detections,
            key=lambda item: item.detector_confidence * max(item.ocr_confidence, 0.1) * max(item.bbox.area, 1.0),
        )
