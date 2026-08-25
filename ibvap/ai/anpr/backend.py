"""License-plate detector/OCR backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ai.contracts import BoundingBox


@dataclass(frozen=True, slots=True)
class DetectedPlate:
    bbox: BoundingBox
    detector_confidence: float
    text: str | None
    ocr_confidence: float
    character_confidences: tuple[float, ...] = ()
    region: str | None = None


class ANPRBackend(Protocol):
    model_name: str

    def predict(self, image: np.ndarray) -> list[DetectedPlate]: ...


class FastALPRBackend:
    """Adapter for the pretrained FastALPR detector + OCR model pair."""

    def __init__(
        self,
        detector_model: str = "yolo-v9-s-608-license-plate-end2end",
        ocr_model: str = "cct-s-v2-global-model",
        detector_confidence: float = 0.40,
        providers: list[str] | None = None,
    ) -> None:
        try:
            from fast_alpr import ALPR
        except ImportError as exc:  # pragma: no cover - optional runtime
            raise RuntimeError("FastALPR is not installed. Run `pip install -e '.[models]'`.") from exc
        self.model_name = f"fast-alpr/{detector_model}+{ocr_model}"
        self._alpr = ALPR(
            detector_model=detector_model,
            detector_conf_thresh=detector_confidence,
            detector_providers=providers,
            ocr_model=ocr_model,
            ocr_providers=providers,
        )

    def predict(self, image: np.ndarray) -> list[DetectedPlate]:
        detected: list[DetectedPlate] = []
        for result in self._alpr.predict(image):
            box = result.detection.bounding_box
            ocr = result.ocr
            raw_confidence = getattr(ocr, "confidence", 0.0) if ocr is not None else 0.0
            if isinstance(raw_confidence, (list, tuple, np.ndarray)):
                character_confidences = tuple(float(value) for value in raw_confidence)
                ocr_confidence = (
                    sum(character_confidences) / len(character_confidences) if character_confidences else 0.0
                )
            else:
                ocr_confidence = float(raw_confidence or 0.0)
                character_confidences = ()
            detected.append(
                DetectedPlate(
                    bbox=BoundingBox(float(box.x1), float(box.y1), float(box.x2), float(box.y2)),
                    detector_confidence=float(getattr(result.detection, "confidence", 0.0)),
                    text=str(ocr.text) if ocr is not None and getattr(ocr, "text", None) else None,
                    ocr_confidence=ocr_confidence,
                    character_confidences=character_confidences,
                    region=str(getattr(ocr, "region", "")) or None if ocr is not None else None,
                )
            )
        return detected
