"""Person 3 YAML configuration loader with validated defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class FaceConfig:
    model_pack: str = "buffalo_l"
    model_root: str = "models/insightface"
    providers: list[str] = field(default_factory=lambda: ["CPUExecutionProvider"])
    detection_size: tuple[int, int] = (640, 640)
    min_detection_score: float = 0.65
    min_face_pixels: int = 64
    min_brightness: float = 35.0
    max_brightness: float = 225.0
    min_sharpness: float = 35.0
    max_clipped_ratio: float = 0.45
    possible_threshold: float = 0.40
    match_threshold: float = 0.50
    ambiguity_margin: float = 0.04
    consensus_window: int = 7
    min_supporting_frames: int = 3
    min_support_ratio: float = 0.60
    sample_every_n_frames: int = 3
    event_cooldown_seconds: float = 15.0


@dataclass(slots=True)
class ANPRConfig:
    detector_model: str = "yolo-v9-s-608-license-plate-end2end"
    ocr_model: str = "cct-s-v2-global-model"
    providers: list[str] = field(default_factory=lambda: ["CPUExecutionProvider"])
    detector_confidence: float = 0.40
    min_plate_height: int = 18
    min_plate_width: int = 55
    min_brightness: float = 25.0
    max_brightness: float = 235.0
    min_sharpness: float = 25.0
    max_clipped_ratio: float = 0.55
    consensus_window: int = 8
    min_supporting_frames: int = 3
    min_character_agreement: float = 0.58
    min_verified_agreement: float = 0.72
    sample_every_n_frames: int = 3
    event_cooldown_seconds: float = 15.0


@dataclass(slots=True)
class EvidenceConfig:
    directory: str = "demo/evidence"
    event_log: str = "demo/events/person3-events.jsonl"
    hash_algorithm: str = "sha256"
    require_human_verification: bool = True


@dataclass(slots=True)
class Person3Config:
    face: FaceConfig = field(default_factory=FaceConfig)
    anpr: ANPRConfig = field(default_factory=ANPRConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    watchlist_path: str = "demo/watchlist/watchlist.json"


def _merge_dataclass(instance: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        if not hasattr(instance, key):
            raise ValueError(f"Unknown configuration field: {type(instance).__name__}.{key}")
        current = getattr(instance, key)
        if isinstance(current, tuple) and isinstance(value, list):
            value = tuple(value)
        setattr(instance, key, value)
    return instance


def load_config(path: str | Path | None = None) -> Person3Config:
    config = Person3Config()
    if path is None:
        return config
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    payload = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    allowed = {"face", "anpr", "evidence", "watchlist_path"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Unknown top-level configuration fields: {sorted(unknown)}")
    if "face" in payload:
        _merge_dataclass(config.face, payload["face"])
    if "anpr" in payload:
        _merge_dataclass(config.anpr, payload["anpr"])
    if "evidence" in payload:
        _merge_dataclass(config.evidence, payload["evidence"])
    if "watchlist_path" in payload:
        config.watchlist_path = str(payload["watchlist_path"])
    return config
