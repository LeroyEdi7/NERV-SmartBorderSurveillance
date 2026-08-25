"""Deterministic demo backends. Never selected by production configuration."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from ai.anpr.backend import DetectedPlate
from ai.contracts import BoundingBox
from ai.face.backend import DetectedFace


class SequenceFaceBackend:
    model_name = "mock/face-embedding-v1"

    def __init__(self, embeddings: Iterable[Iterable[float]]) -> None:
        self._embeddings = [tuple(float(value) for value in item) for item in embeddings]
        self._index = 0

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        embedding = self._embeddings[min(self._index, len(self._embeddings) - 1)]
        self._index += 1
        height, width = image.shape[:2]
        return [
            DetectedFace(
                BoundingBox(width * 0.20, height * 0.10, width * 0.80, height * 0.78),
                embedding,
                0.96,
                (
                    (width * 0.40, height * 0.32),
                    (width * 0.60, height * 0.32),
                    (width * 0.50, height * 0.46),
                    (width * 0.42, height * 0.60),
                    (width * 0.58, height * 0.60),
                ),
            )
        ]


class SequenceANPRBackend:
    model_name = "mock/anpr-detector+ocr-v1"

    def __init__(self, readings: Iterable[str]) -> None:
        self._readings = list(readings)
        self._index = 0

    def predict(self, image: np.ndarray) -> list[DetectedPlate]:
        reading = self._readings[min(self._index, len(self._readings) - 1)]
        self._index += 1
        height, width = image.shape[:2]
        return [
            DetectedPlate(
                BoundingBox(width * 0.24, height * 0.58, width * 0.76, height * 0.82),
                detector_confidence=0.94,
                text=reading,
                ocr_confidence=0.91,
                character_confidences=tuple(0.92 for _ in reading),
                region="in",
            )
        ]
