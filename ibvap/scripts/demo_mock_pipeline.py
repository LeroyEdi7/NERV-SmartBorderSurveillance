#!/usr/bin/env python3
"""Run Person 3 end to end without Person 1/2 or downloading model weights."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.anpr.service import ANPRService
from ai.common.config import load_config
from ai.contracts import BoundingBox, TrackObservation
from ai.evidence.events import JsonlEventSink
from ai.evidence.passport import EvidencePassportBuilder
from ai.face.service import FaceRecognitionService
from ai.face.watchlist import WatchlistStore
from ai.mocks import SequenceANPRBackend, SequenceFaceBackend
from ai.pipeline import Person3Pipeline


def textured_frame(height: int = 360, width: int = 640) -> np.ndarray:
    y, x = np.indices((height, width))
    pattern = (((x // 4 + y // 4) % 2) * 100 + 80).astype(np.uint8)
    return np.stack((pattern, np.roll(pattern, 2, axis=1), np.roll(pattern, 2, axis=0)), axis=-1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/person3.yaml")
    parser.add_argument("--output", default="demo/output")
    args = parser.parse_args()
    config = load_config(args.config)
    config.face.sample_every_n_frames = 1
    config.anpr.sample_every_n_frames = 1
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    target = np.asarray([1.0, 0.1, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0], dtype=np.float32)
    face_backend = SequenceFaceBackend([target, target + 0.01, target - 0.01, target])
    watchlist = WatchlistStore(output / "demo-watchlist.json", face_backend.model_name)
    watchlist.enroll("WL-DEMO-001", "Demo Subject", [target], "HACKATHON-DEMO-CONSENT")
    face_service = FaceRecognitionService(face_backend, watchlist, config.face)

    plate_backend = SequenceANPRBackend(["MH12AB1234", "MH12A81234", "MH12AB1234", "MH12AB1234"])
    anpr_service = ANPRService(plate_backend, config.anpr)
    sink = JsonlEventSink(output / "person3-events.jsonl")
    pipeline = Person3Pipeline(face_service, anpr_service, sink)

    frame = textured_frame()
    start = datetime.now(timezone.utc)
    face_track = None
    for index in range(4):
        result = pipeline.process(
            TrackObservation(
                camera_id="CAM-ENTRY",
                frame_id=index,
                timestamp=start + timedelta(milliseconds=index * 100),
                object_type="person",
                track_id=41,
                bbox=BoundingBox(80, 20, 300, 330),
                frame=frame,
                global_entity_id="PERSON-GLOBAL-41",
            )
        )
        if result.face and result.face.track:
            face_track = result.face.track

    plate_track = None
    camera_sequence = [("CAM-GATE-A", 91), ("CAM-GATE-A", 91), ("CAM-GATE-B", 12), ("CAM-GATE-B", 12)]
    for index, (camera_id, track_id) in enumerate(camera_sequence):
        result = pipeline.process(
            TrackObservation(
                camera_id=camera_id,
                frame_id=index,
                timestamp=start + timedelta(seconds=1, milliseconds=index * 100),
                object_type="vehicle",
                track_id=track_id,
                bbox=BoundingBox(40, 60, 600, 330),
                frame=frame,
                global_entity_id="VEHICLE-GLOBAL-007",
            )
        )
        if result.anpr and result.anpr.track:
            plate_track = result.anpr.track

    if face_track is None or plate_track is None:
        raise RuntimeError("Demo failed to produce track evidence")
    builder = EvidencePassportBuilder(output / "passports")
    passport = builder.build(
        entity_id="INCIDENT-DEMO-001",
        face=face_track,
        plate=plate_track,
        person_vehicle_association={
            "person_entity_id": "PERSON-GLOBAL-41",
            "vehicle_entity_id": "VEHICLE-GLOBAL-007",
            "method": "P2_TEMPORAL_PROXIMITY",
            "confidence": 0.87,
            "state": "CANDIDATE",
        },
    )
    passport_path = builder.save(passport)
    summary = {
        "face": face_track.to_dict(),
        "plate": plate_track.to_dict(),
        "passport": str(passport_path),
        "integrity_verified": passport.verify_integrity(),
        "event_log": str(sink.path),
    }
    summary_path = output / "demo-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
