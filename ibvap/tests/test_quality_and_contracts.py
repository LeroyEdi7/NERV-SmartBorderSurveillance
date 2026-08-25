from datetime import datetime, timezone

import numpy as np
import pytest

from ai.anpr.quality import assess_plate_quality
from ai.common.config import ANPRConfig, FaceConfig
from ai.contracts import BoundingBox, QualityState, TrackObservation
from ai.face.quality import assess_face_quality


def textured_image(height=120, width=180):
    y, x = np.indices((height, width))
    pattern = (((x // 3 + y // 3) % 2) * 100 + 80).astype(np.uint8)
    return np.stack([pattern, pattern, pattern], axis=-1)


def test_bbox_and_track_contract():
    frame = textured_image()
    observation = TrackObservation(
        "CAM-1",
        0,
        datetime.now(timezone.utc),
        "person",
        7,
        BoundingBox(1, 2, 100, 110),
        frame,
    )
    assert observation.track_key == "CAM-1:7"
    with pytest.raises(ValueError):
        BoundingBox(10, 10, 5, 20)


def test_quality_gates_accept_clear_and_reject_flat_images():
    clear = textured_image()
    face_box = BoundingBox(0, 0, 100, 100)
    clear_face = assess_face_quality(clear, face_box, 0.95, (), FaceConfig())
    assert clear_face.state == QualityState.GOOD

    flat = np.zeros((30, 40, 3), dtype=np.uint8)
    rejected_plate = assess_plate_quality(flat, BoundingBox(0, 0, 40, 30), ANPRConfig())
    assert rejected_plate.state == QualityState.UNUSABLE
    assert "plate_too_small" in rejected_plate.reasons
