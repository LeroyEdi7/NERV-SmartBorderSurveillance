from __future__ import annotations

import numpy as np


def bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_overlap_ratio(
    person_bbox: tuple[float, float, float, float],
    vehicle_bbox: tuple[float, float, float, float],
) -> float:
    """Fraction of the person box covered by the vehicle box."""
    px1, py1, px2, py2 = person_bbox
    vx1, vy1, vx2, vy2 = vehicle_bbox
    ix1, iy1 = max(px1, vx1), max(py1, vy1)
    ix2, iy2 = min(px2, vx2), min(py2, vy2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    intersection = (ix2 - ix1) * (iy2 - iy1)
    person_area = (px2 - px1) * (py2 - py1)
    if person_area <= 0:
        return 0.0
    return intersection / person_area


def center_distance(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ac = bbox_center(a)
    bc = bbox_center(b)
    return float(np.hypot(ac[0] - bc[0], ac[1] - bc[1]))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    an = float(np.linalg.norm(a)) + 1e-8
    bn = float(np.linalg.norm(b)) + 1e-8
    return float(np.dot(a, b) / (an * bn))


def max_cosine(query: np.ndarray, gallery: list[np.ndarray]) -> float:
    if not gallery:
        return 0.0
    return max(cosine_similarity(query, item) for item in gallery)


def near_frame_edge(
    bbox: tuple[float, float, float, float],
    frame_wh: tuple[int, int],
    margin_px: int,
) -> bool:
    x1, y1, x2, y2 = bbox
    w, h = frame_wh
    return x1 <= margin_px or y1 <= margin_px or x2 >= (w - margin_px) or y2 >= (h - margin_px)


def heading_from_velocity(velocity: tuple[float, float]) -> tuple[float, float]:
    vx, vy = velocity
    mag = float(np.hypot(vx, vy))
    if mag < 1e-6:
        return (0.0, 0.0)
    return (vx / mag, vy / mag)
