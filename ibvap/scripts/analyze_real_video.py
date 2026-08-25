#!/usr/bin/env python3
"""Run real InsightFace/FastALPR inference on a video without P1/P2.

The frame is tiled so distant faces and plates keep more pixels than they would
under a single full-frame resize. This is a standalone validation tool, not a
replacement for P1 vehicle/person crops or P2 tracking.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.anpr.backend import FastALPRBackend
from ai.anpr.india_format import normalize_plate
from ai.common.config import load_config
from ai.contracts import BoundingBox
from ai.face.backend import InsightFaceBackend


def tile_boxes(width: int, height: int, columns: int, rows: int, overlap: float) -> list[BoundingBox]:
    tile_width = int(np.ceil(width / (columns - overlap * (columns - 1))))
    tile_height = int(np.ceil(height / (rows - overlap * (rows - 1))))
    step_x = max(1, int(tile_width * (1.0 - overlap)))
    step_y = max(1, int(tile_height * (1.0 - overlap)))
    x_values = sorted({min(index * step_x, width - tile_width) for index in range(columns)})
    y_values = sorted({min(index * step_y, height - tile_height) for index in range(rows)})
    return [
        BoundingBox(x, y, min(x + tile_width, width), min(y + tile_height, height))
        for y in y_values
        for x in x_values
    ]


def intersection_over_union(left: BoundingBox, right: BoundingBox) -> float:
    x1, y1 = max(left.x1, right.x1), max(left.y1, right.y1)
    x2, y2 = min(left.x2, right.x2), min(left.y2, right.y2)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = left.area + right.area - intersection
    return intersection / union if union else 0.0


def deduplicate(items: list[dict], score_key: str, threshold: float = 0.35) -> list[dict]:
    kept: list[dict] = []
    for item in sorted(items, key=lambda value: value[score_key], reverse=True):
        box = BoundingBox.from_sequence(item["bbox"])
        if all(intersection_over_union(box, BoundingBox.from_sequence(other["bbox"])) < threshold for other in kept):
            kept.append(item)
    return kept


def draw_result(frame: np.ndarray, faces: list[dict], plates: list[dict], frame_id: int) -> np.ndarray:
    output = frame.copy()
    for face in faces:
        x1, y1, x2, y2 = (int(value) for value in face["bbox"])
        cv2.rectangle(output, (x1, y1), (x2, y2), (50, 220, 50), 3)
        state = "ACCEPTED" if face["accepted"] else "RAW-REJECTED"
        cv2.putText(output, f"FACE {face['score']:.2f} {state}", (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (50, 220, 50), 2)
    for plate in plates:
        x1, y1, x2, y2 = (int(value) for value in plate["bbox"])
        label = plate.get("text") or "PLATE"
        cv2.rectangle(output, (x1, y1), (x2, y2), (40, 180, 255), 3)
        state = "ACCEPTED" if plate["accepted"] else "RAW-REJECTED"
        cv2.putText(output, f"{label} {plate['detector_confidence']:.2f} {state}", (x1, max(30, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (40, 180, 255), 2)
    status = f"REAL MODELS | frame {frame_id} | faces {len(faces)} | plates {len(plates)}"
    cv2.rectangle(output, (20, 20), (940, 75), (0, 0, 0), -1)
    cv2.putText(output, status, (35, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 2)
    if not faces and not plates:
        cv2.putText(output, "No reliable biometric/plate pixels in this sampled frame", (35, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 230), 2)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output", default="demo/real-video")
    parser.add_argument("--sample-every", type=int, default=30, help="Process every Nth source frame")
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--overlap", type=float, default=0.12)
    parser.add_argument("--plate-confidence", type=float, default=0.15)
    parser.add_argument("--config", default="configs/person3.yaml")
    args = parser.parse_args()

    output_directory = Path(args.output)
    output_directory.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    face_backend = InsightFaceBackend(
        config.face.model_pack,
        config.face.providers,
        config.face.detection_size,
        config.face.model_root,
    )
    plate_backend = FastALPRBackend(
        config.anpr.detector_model,
        config.anpr.ocr_model,
        args.plate_confidence,
        config.anpr.providers,
    )

    capture = cv2.VideoCapture(args.input)
    if not capture.isOpened():
        raise ValueError(f"Unable to open video: {args.input}")
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tiles = tile_boxes(width, height, args.columns, args.rows, args.overlap)
    started = time.perf_counter()
    results: list[dict] = []
    preview_candidates: list[tuple[int, int, np.ndarray]] = []
    frame_id = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_id % max(args.sample_every, 1) != 0:
            frame_id += 1
            continue
        faces: list[dict] = []
        plates: list[dict] = []
        for tile in tiles:
            crop = frame[int(tile.y1) : int(tile.y2), int(tile.x1) : int(tile.x2)]
            for face in face_backend.detect(crop):
                absolute_box = face.bbox.translated(tile.x1, tile.y1)
                rejection_reasons = []
                if min(absolute_box.width, absolute_box.height) < config.face.min_face_pixels:
                    rejection_reasons.append("face_too_small")
                if face.detection_score < config.face.min_detection_score:
                    rejection_reasons.append("low_detection_confidence")
                faces.append(
                    {
                        "bbox": absolute_box.as_list(),
                        "score": round(face.detection_score, 4),
                        "accepted": not rejection_reasons,
                        "rejection_reasons": rejection_reasons,
                        "model": face_backend.model_name,
                    }
                )
            for plate in plate_backend.predict(crop):
                absolute_box = plate.bbox.translated(tile.x1, tile.y1)
                normalized_text = normalize_plate(plate.text)
                rejection_reasons = []
                if absolute_box.width < config.anpr.min_plate_width or absolute_box.height < config.anpr.min_plate_height:
                    rejection_reasons.append("plate_too_small")
                if plate.detector_confidence < config.anpr.detector_confidence:
                    rejection_reasons.append("below_production_detector_threshold")
                if len(normalized_text) < 4:
                    rejection_reasons.append("ocr_unresolved")
                plates.append(
                    {
                        "bbox": absolute_box.as_list(),
                        "detector_confidence": round(plate.detector_confidence, 4),
                        "text": plate.text,
                        "ocr_confidence": round(plate.ocr_confidence, 4),
                        "accepted": not rejection_reasons,
                        "rejection_reasons": rejection_reasons,
                        "model": plate_backend.model_name,
                    }
                )
        faces = deduplicate(faces, "score")
        plates = deduplicate(plates, "detector_confidence")
        results.append(
            {
                "frame_id": frame_id,
                "timestamp_seconds": round(frame_id / fps, 3) if fps else None,
                "faces": faces,
                "plates": plates,
            }
        )
        annotated = draw_result(frame, faces, plates, frame_id)
        preview_candidates.append((len(faces) + len(plates), frame_id, annotated))
        frame_id += 1
    capture.release()

    preview_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    saved_previews: list[str] = []
    for rank, (_, source_frame, image) in enumerate(preview_candidates[:3], 1):
        destination = output_directory / f"preview-{rank}-frame-{source_frame}.jpg"
        cv2.imwrite(str(destination), image)
        saved_previews.append(str(destination))
    report = {
        "input": str(Path(args.input).resolve()),
        "video": {
            "width": width,
            "height": height,
            "fps": fps,
            "total_frames": total_frames,
            "duration_seconds": total_frames / fps if fps else None,
        },
        "sampling": {
            "sample_every": args.sample_every,
            "sampled_frames": len(results),
            "tiles_per_frame": len(tiles),
            "plate_detector_threshold": args.plate_confidence,
        },
        "summary": {
            "face_detections": sum(len(item["faces"]) for item in results),
            "plate_detections": sum(len(item["plates"]) for item in results),
            "accepted_face_evidence": sum(face["accepted"] for item in results for face in item["faces"]),
            "accepted_plate_evidence": sum(plate["accepted"] for item in results for plate in item["plates"]),
            "events_emitted": 0,
            "ocr_readings": [plate["text"] for item in results for plate in item["plates"] if plate.get("text")],
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "interpretation": "No detection means the source lacks sufficient face/plate pixels at this camera distance; it is not converted into synthetic evidence.",
        },
        "previews": saved_previews,
        "frames": results,
    }
    report_path = output_directory / "real-video-report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({**report["summary"], "report": str(report_path), "previews": saved_previews}, indent=2))


if __name__ == "__main__":
    main()
