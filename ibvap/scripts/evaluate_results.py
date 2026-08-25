#!/usr/bin/env python3
"""Calculate small hackathon face/plate metrics from a JSON evaluation file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.anpr.consensus import edit_distance
from ai.anpr.india_format import normalize_plate


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON with `plates` and/or `faces` arrays")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report: dict[str, object] = {}

    plates = payload.get("plates", [])
    if plates:
        exact = 0
        edits = 0
        characters = 0
        for item in plates:
            truth = normalize_plate(item.get("truth"))
            prediction = normalize_plate(item.get("prediction"))
            exact += truth == prediction
            edits += edit_distance(truth, prediction)
            characters += max(len(truth), len(prediction))
        report["plates"] = {
            "samples": len(plates),
            "exact_accuracy": round(safe_divide(exact, len(plates)), 4),
            "character_accuracy": round(1.0 - safe_divide(edits, characters), 4),
        }

    faces = payload.get("faces", [])
    if faces:
        true_positive = false_positive = false_negative = true_negative = 0
        for item in faces:
            truth = item.get("truth_id")
            prediction = item.get("predicted_id")
            if truth and prediction == truth:
                true_positive += 1
            elif truth and prediction != truth:
                false_negative += 1
                false_positive += prediction is not None
            elif not truth and prediction:
                false_positive += 1
            else:
                true_negative += 1
        report["faces"] = {
            "samples": len(faces),
            "precision": round(safe_divide(true_positive, true_positive + false_positive), 4),
            "recall": round(safe_divide(true_positive, true_positive + false_negative), 4),
            "false_matches": false_positive,
            "false_non_matches": false_negative,
            "true_negatives": true_negative,
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
