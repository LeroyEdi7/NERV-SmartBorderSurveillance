"""Plate image quality gates."""

from __future__ import annotations

import numpy as np

from ai.common.config import ANPRConfig
from ai.common.image_ops import image_statistics
from ai.contracts import BoundingBox, QualityAssessment, QualityState


def assess_plate_quality(image: np.ndarray, bbox: BoundingBox, config: ANPRConfig) -> QualityAssessment:
    brightness, sharpness, clipped_ratio = image_statistics(image)
    reasons: list[str] = []
    penalties = 0.0
    if bbox.width < config.min_plate_width or bbox.height < config.min_plate_height:
        reasons.append("plate_too_small")
        penalties += 0.50
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
    score = max(0.0, min(1.0, 1.0 - penalties))
    hard_failure = (
        bbox.width < config.min_plate_width * 0.60
        or bbox.height < config.min_plate_height * 0.60
        or sharpness < config.min_sharpness * 0.35
    )
    state = QualityState.UNUSABLE if hard_failure or score < 0.35 else QualityState.DEGRADED if reasons else QualityState.GOOD
    return QualityAssessment(
        state,
        round(score, 4),
        round(brightness, 3),
        round(sharpness, 3),
        round(clipped_ratio, 4),
        tuple(reasons),
    )
