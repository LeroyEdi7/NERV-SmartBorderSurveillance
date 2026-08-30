from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.models import Detection


class Detector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Detection]:
        ...


@dataclass
class DummyDetector:
    """Deterministic synthetic boxes for testing Person 2 tracking without YOLO weights."""

    frame_index: int = 0
    person_x: float = 40.0
    scenario: str = "normal"  # "normal", "occlusion", "vehicle_entry"

    def reset(self) -> None:
        """Reset internal frame counter and position for deterministic scenario restarts."""
        self.frame_index = 0
        self.person_x = 40.0

    def detect(self, frame: np.ndarray) -> list[Detection]:
        h, w = frame.shape[:2] if (frame is not None and hasattr(frame, "shape") and len(frame.shape) >= 2) else (720, 1280)
        self.frame_index += 1
        detections: list[Detection] = []

        if self.scenario == "occlusion":
            # Simulate person walking, disappearing for 5 frames (frames 20-25), then re-emerging
            if not (20 <= self.frame_index <= 25):
                px = 40.0 + (self.frame_index * 4.0)
                detections.append(Detection(bbox=(px, h * 0.4, px + 50, h * 0.4 + 120), score=0.9, class_name="person"))
        elif self.scenario == "vehicle_entry":
            # Vehicle parked at (w*0.5, h*0.4, w*0.8, h*0.8)
            vehicle_bbox = (w * 0.5, h * 0.4, w * 0.8, h * 0.8)
            detections.append(Detection(bbox=vehicle_bbox, score=0.88, class_name="vehicle"))
            # Person moves toward vehicle, overlaps for 15 frames, then disappears inside
            if self.frame_index <= 25:
                px = 40.0 + (self.frame_index * 12.0)
                py = h * 0.45
                detections.append(Detection(bbox=(px, py, px + 50, py + 110), score=0.91, class_name="person"))
        else:
            self.person_x = 40.0 + (self.frame_index % 80)
            detections.append(Detection(bbox=(self.person_x, h * 0.4, self.person_x + 50, h * 0.4 + 120), score=0.9, class_name="person"))
            detections.append(Detection(bbox=(w * 0.55, h * 0.45, w * 0.85, h * 0.85), score=0.85, class_name="vehicle"))

        return detections


class YoloDetector:
    """Ultralytics YOLO wrapper. Persons (class 0) and vehicles (1,2,3,5,7)."""

    PERSON = 0
    VEHICLES = {1, 2, 3, 5, 7}  # bicycle, car, motorcycle, bus, truck

    def __init__(self, model_name: str = "yolov8n.pt", device: str = "cpu"):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "ultralytics is required for live detection. Install it or pass --dummy."
            ) from exc
        self.model = YOLO(model_name)
        self.device = device

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(frame, verbose=False, device=self.device)
        detections: list[Detection] = []
        if not results:
            return detections
        boxes = results[0].boxes
        if boxes is None:
            return detections
        for box in boxes:
            cls_id = int(box.cls[0])
            if cls_id == self.PERSON:
                class_name = "person"
            elif cls_id in self.VEHICLES:
                class_name = "vehicle"
            else:
                continue
            xyxy = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                    score=float(box.conf[0]),
                    class_name=class_name,  # type: ignore[arg-type]
                )
            )
        return detections


def build_detector(cfg: TrackingConfig, dummy: bool = False, scenario: str = "normal") -> Detector:
    if dummy:
        return DummyDetector(scenario=scenario)
    return YoloDetector(model_name=cfg.yolo_model, device=cfg.device)

