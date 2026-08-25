"""Quality gates for face crops before watchlist matching."""

from __future__ import annotations

import numpy as np

from ai.common.config import FaceConfig
from ai.common.image_ops import image_statistics
from ai.contracts import BoundingBox, QualityAssessment, QualityState


def assess_face_quality(
    image: np.ndarray,
    bbox: BoundingBox,
    detection_score: float,
    keypoints: tuple[tuple[float, float], ...],
    config: FaceConfig,
) -> QualityAssessment:
    brightness, sharpness, clipped_ratio = image_statistics(image)
    reasons: list[str] = []
    penalties = 0.0

    if min(bbox.width, bbox.height) < config.min_face_pixels:
        reasons.append("face_too_small")
        penalties += 0.55
    if detection_score < config.min_detection_score:
        reasons.append("low_detection_confidence")
        penalties += 0.30
    if brightness < config.min_brightness:
        reasons.append("too_dark")
        penalties += 0.30
    if brightness > config.max_brightness:
        reasons.append("too_bright")
        penalties += 0.30
    if sharpness < config.min_sharpness:
        reasons.append("blurred")
        penalties += 0.35
    if clipped_ratio > config.max_clipped_ratio:
        reasons.append("high_clipping")
        penalties += 0.25

    if len(keypoints) >= 5:
        left_eye, right_eye, nose = keypoints[0], keypoints[1], keypoints[2]
        eye_midpoint = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)
        eye_distance = max(abs(right_eye[0] - left_eye[0]), 1.0)
        yaw_proxy = abs(nose[0] - eye_midpoint[0]) / eye_distance
        if yaw_proxy > 0.36:
            reasons.append("strong_side_pose")
            penalties += 0.25

    score = max(0.0, min(1.0, 1.0 - penalties))
    hard_failure = (
        min(bbox.width, bbox.height) < config.min_face_pixels * 0.65
        or detection_score < config.min_detection_score * 0.65
        or sharpness < config.min_sharpness * 0.40
    )
    if hard_failure or score < 0.35:
        state = QualityState.UNUSABLE
    elif reasons:
        state = QualityState.DEGRADED
    else:
        state = QualityState.GOOD
    return QualityAssessment(
        state=state,
        score=round(score, 4),
        brightness=round(brightness, 3),
        sharpness=round(sharpness, 3),
        clipped_ratio=round(clipped_ratio, 4),
        reasons=tuple(reasons),
    )
