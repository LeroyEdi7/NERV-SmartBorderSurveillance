"""Face detector/embedding backends.

The production adapter imports InsightFace lazily so unit tests and the mock demo
do not require the heavyweight runtime or model download.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ai.contracts import BoundingBox


@dataclass(frozen=True, slots=True)
class DetectedFace:
    bbox: BoundingBox
    embedding: tuple[float, ...]
    detection_score: float
    keypoints: tuple[tuple[float, float], ...] = ()


class FaceBackend(Protocol):
    model_name: str

    def detect(self, image: np.ndarray) -> list[DetectedFace]: ...


class InsightFaceBackend:
    """InsightFace ``FaceAnalysis`` adapter using a pretrained model pack."""

    def __init__(
        self,
        model_pack: str = "buffalo_l",
        providers: list[str] | None = None,
        detection_size: tuple[int, int] = (640, 640),
        model_root: str = "models/insightface",
    ) -> None:
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:  # pragma: no cover - depends on optional runtime
            raise RuntimeError(
                "InsightFace is not installed. Run `pip install -e '.[models]'`."
            ) from exc

        selected_providers = providers or ["CPUExecutionProvider"]
        self.model_name = f"insightface/{model_pack}"
        self._app = FaceAnalysis(name=model_pack, root=model_root, providers=selected_providers)
        ctx_id = 0 if any("CUDA" in provider or "CoreML" in provider for provider in selected_providers) else -1
        self._app.prepare(ctx_id=ctx_id, det_size=detection_size)

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        detected: list[DetectedFace] = []
        for face in self._app.get(image):
            embedding = getattr(face, "normed_embedding", None)
            if embedding is None:
                embedding = getattr(face, "embedding", None)
            if embedding is None:
                continue
            keypoints = getattr(face, "kps", None)
            detected.append(
                DetectedFace(
                    bbox=BoundingBox.from_sequence(face.bbox.tolist()),
                    embedding=tuple(float(value) for value in embedding),
                    detection_score=float(getattr(face, "det_score", 0.0)),
                    keypoints=tuple(tuple(float(value) for value in point) for point in keypoints)
                    if keypoints is not None
                    else (),
                )
            )
        return detected
