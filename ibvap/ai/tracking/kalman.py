from __future__ import annotations

import numpy as np

from ibvap.ai.tracking.geometry import bbox_center


class KalmanBoxFilter:
    """Constant-velocity Kalman filter on (cx, cy, w, h, vx, vy)."""

    def __init__(self, bbox: tuple[float, float, float, float]):
        cx, cy = bbox_center(bbox)
        x1, y1, x2, y2 = bbox
        w, h = max(1.0, x2 - x1), max(1.0, y2 - y1)
        self.x = np.array([cx, cy, w, h, 0.0, 0.0], dtype=float)
        self.P = np.eye(6, dtype=float)
        self.P[4:, 4:] *= 100.0
        self.F = np.eye(6, dtype=float)
        self.F[0, 4] = 1.0
        self.F[1, 5] = 1.0
        self.H = np.zeros((4, 6), dtype=float)
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        self.H[2, 2] = 1.0
        self.H[3, 3] = 1.0
        self.R = np.eye(4, dtype=float) * 1.5
        self.Q = np.eye(6, dtype=float) * 0.1
        self.Q[4:, 4:] *= 0.5

    def predict(self) -> tuple[float, float, float, float]:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.as_bbox()

    def update(self, bbox: tuple[float, float, float, float]) -> None:
        cx, cy = bbox_center(bbox)
        x1, y1, x2, y2 = bbox
        z = np.array([cx, cy, max(1.0, x2 - x1), max(1.0, y2 - y1)], dtype=float)
        y = z - self.H @ self.x
        s = self.H @ self.P @ self.H.T + self.R
        k = self.P @ self.H.T @ np.linalg.inv(s)
        self.x = self.x + k @ y
        self.P = (np.eye(6) - k @ self.H) @ self.P

    def as_bbox(self) -> tuple[float, float, float, float]:
        cx, cy, w, h = self.x[0], self.x[1], max(1.0, self.x[2]), max(1.0, self.x[3])
        return (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)

    def velocity(self) -> tuple[float, float]:
        return (float(self.x[4]), float(self.x[5]))
