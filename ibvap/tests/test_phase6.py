from __future__ import annotations

import json
import numpy as np
import pytest

from ibvap.configs.config import load_config
from src.events.payload import build_event_payload
from ibvap.ai.tracking.events.publisher import EventPublisher, MockBackendReceiver
from src.pipeline import run_loop, build_parser, main as pipeline_main


def test_phase6_json_payload_schema_compliance(tmp_path):
    cfg = load_config()
    cfg.queue_path = str(tmp_path / "test_queue.jsonl")
    receiver = MockBackendReceiver()
    publisher = EventPublisher(cfg, mock_receiver=receiver)

    payload = publisher.emit(
        event_type="person_detected",
        track_id=17,
        bbox=(120.0, 80.0, 250.0, 400.0),
        camera_id="WEBCAM-01",
        confidence=0.94,
        extra={"entity_id": "G-017"},
    )

    # Check top-level required fields
    required_keys = {
        "event_id",
        "event_type",
        "timestamp",
        "camera_id",
        "entity",
        "detection",
        "severity",
        "metadata",
        "track_id",
        "bbox",
        "confidence",
        "idempotency_key",
    }
    assert required_keys.issubset(set(payload.keys()))

    # Check sub-objects format
    assert payload["event_type"] == "person_detected"
    assert payload["camera_id"] == "WEBCAM-01"
    assert payload["entity"]["entity_id"] == "G-017"
    assert payload["entity"]["entity_type"] == "person"
    assert payload["detection"]["track_id"] == 17
    assert payload["detection"]["confidence"] == 0.94
    assert payload["detection"]["class"] == "person"
    assert payload["detection"]["bbox"] == [120.0, 80.0, 250.0, 400.0]
    assert payload["severity"] in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(payload["idempotency_key"], str) and len(payload["idempotency_key"]) == 64


def test_phase6_cli_argument_parser():
    parser = build_parser()
    args = parser.parse_args([
        "--dummy",
        "--scenario", "occlusion",
        "--camera-id", "BOP-01",
        "--no-display",
        "--max-frames", "50",
    ])
    assert args.dummy is True
    assert args.scenario == "occlusion"
    assert args.camera_id == "BOP-01"
    assert args.no_display is True
    assert args.max_frames == 50


def test_phase6_synthetic_dummy_simulation_run(tmp_path):
    cfg = load_config()
    cfg.queue_path = str(tmp_path / "synthetic_queue.jsonl")

    # Run synthetic dummy loop for 20 frames without error
    run_loop(
        cfg=cfg,
        source="synthetic",
        camera_id="BOP-01",
        dummy=True,
        display=False,
        redis_url=None,
        max_frames=20,
        scenario="occlusion",
    )

    # Verify queue file created and populated with JSON line events
    queue_file = tmp_path / "synthetic_queue.jsonl"
    assert queue_file.exists()
    lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0

    first_event = json.loads(lines[0])
    assert first_event["camera_id"] == "BOP-01"
    assert "event_id" in first_event
