from __future__ import annotations


def determine_severity(event_type: str, confidence: float, context: dict | None = None) -> str:
    if event_type == "vehicle_person_association":
        if confidence >= 0.85:
            return "HIGH"
        if confidence >= 0.6:
            return "MEDIUM"
        return "LOW"
    if event_type == "cross_camera_match":
        if confidence >= 0.9:
            return "MEDIUM"
        return "LOW"
    return "LOW"
