from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "ibvap" / "configs" / "default.yaml"
DEFAULT_CAMERAS_PATH = ROOT / "ibvap" / "configs" / "cameras.yaml"


@dataclass(slots=True)
class TransitWindow:
    expected_transit_sec: float
    margin_sec: float

    @property
    def min_sec(self) -> float:
        return max(0.0, self.expected_transit_sec - self.margin_sec)

    @property
    def max_sec(self) -> float:
        return self.expected_transit_sec + self.margin_sec


@dataclass(slots=True)
class CameraTopology:
    cameras: dict[str, dict[str, TransitWindow]] = field(default_factory=dict)

    def window(self, from_cam: str, to_cam: str) -> TransitWindow | None:
        return self.cameras.get(from_cam, {}).get(to_cam)

    def is_adjacent(self, from_cam: str, to_cam: str) -> bool:
        return self.window(from_cam, to_cam) is not None


@dataclass(slots=True)
class TrackingConfig:
    fps: float = 25.0
    high_thresh: float = 0.6
    low_thresh: float = 0.1
    match_iou: float = 0.5
    max_age: int = 30
    min_hits: int = 3
    occlusion_ttl_sec: float = 8.0
    reid_cosine_threshold: float = 0.7
    embedding_buffer_size: int = 5
    lost_track_distance_gate_px: float = 180.0
    lost_track_iou_gate: float = 0.1
    overlap_threshold: float = 0.6
    min_duration_sec: float = 1.5
    confirm_on_disappear: bool = True
    disappear_confirm_sec: float = 2.0
    spatial_grid_cell_px: int = 160
    exit_margin_px: int = 24
    gallery_ambiguity_gap: float = 0.05
    embedding_retention_sec: float = 30.0
    embedder: str = "auto"
    osnet_name: str = "osnet_x1_0"
    transreid_weights_path: str = "ibvap/models/transreid_vit_base.onnx"
    tracker_type: str = "bytetrack"  # "bytetrack" or "deep_ocsort"
    device: str = "cpu"
    backend_url: str = ""
    backend_timeout_sec: float = 3.0
    retry_backoff_sec: float = 0.5
    max_retries: int = 5
    queue_path: str = "event_queue.jsonl"
    yolo_model: str = "yolov8n.pt"
    draw: bool = True
    topology: CameraTopology = field(default_factory=CameraTopology)

    @property
    def sustained_frames(self) -> int:
        return max(1, int(round(self.min_duration_sec * self.fps)))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} must be a mapping")
    return data


def load_topology(path: Path | str | None = None) -> CameraTopology:
    raw = _load_yaml(Path(path) if path else DEFAULT_CAMERAS_PATH)
    cameras_raw = raw.get("cameras", {})
    cameras: dict[str, dict[str, TransitWindow]] = {}
    for cam_id, spec in cameras_raw.items():
        adjacent = spec.get("adjacent", {}) if isinstance(spec, dict) else {}
        cameras[str(cam_id)] = {
            str(other): TransitWindow(
                expected_transit_sec=float(win.get("expected_transit_sec", 5.0)),
                margin_sec=float(win.get("margin_sec", 3.0)),
            )
            for other, win in adjacent.items()
        }
    return CameraTopology(cameras=cameras)


def load_config(
    config_path: Path | str | None = None,
    cameras_path: Path | str | None = None,
) -> TrackingConfig:
    raw = _load_yaml(Path(config_path) if config_path else DEFAULT_CONFIG_PATH)
    known = {f.name for f in TrackingConfig.__dataclass_fields__.values()}
    kwargs = {k: v for k, v in raw.items() if k in known}
    cfg = TrackingConfig(**kwargs)
    cfg.topology = load_topology(cameras_path)
    return cfg
