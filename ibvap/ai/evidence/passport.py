"""Tamper-evident Evidence Passport: Person 3's judge-facing wow feature."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ai.contracts import FaceTrackResult, PlateTrackResult


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class HumanReview:
    status: str = "PENDING"
    reviewer_id: str | None = None
    reviewed_at: str | None = None
    note: str | None = None


@dataclass(slots=True)
class EvidencePassport:
    passport_id: str
    created_at: str
    entity_id: str
    decision_state: str
    face: dict[str, Any] | None
    plate: dict[str, Any] | None
    person_vehicle_association: dict[str, Any] | None
    decision_trace: list[dict[str, Any]]
    human_review: HumanReview = field(default_factory=HumanReview)
    schema_version: str = "1.0"
    integrity_hash: str = ""

    def unsigned_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("integrity_hash", None)
        return payload

    def seal(self) -> None:
        self.integrity_hash = _canonical_hash(self.unsigned_payload())

    def verify_integrity(self) -> bool:
        return bool(self.integrity_hash) and self.integrity_hash == _canonical_hash(self.unsigned_payload())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def review(self, reviewer_id: str, decision: str, note: str | None = None) -> None:
        normalized = decision.upper()
        if normalized not in {"VERIFIED", "DISMISSED"}:
            raise ValueError("Review decision must be VERIFIED or DISMISSED")
        self.human_review = HumanReview(
            status=normalized,
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            note=note,
        )
        self.decision_state = normalized
        self.seal()


class EvidencePassportBuilder:
    def __init__(self, output_directory: str | Path) -> None:
        self.output_directory = Path(output_directory)

    def build(
        self,
        entity_id: str,
        face: FaceTrackResult | None = None,
        plate: PlateTrackResult | None = None,
        person_vehicle_association: dict[str, Any] | None = None,
    ) -> EvidencePassport:
        if face is None and plate is None:
            raise ValueError("A passport needs face or plate evidence")
        trace: list[dict[str, Any]] = []
        if face:
            trace.extend(
                [
                    {"stage": "face_quality_and_matching", "state": face.status.value, "frames": face.total_frames},
                    {
                        "stage": "face_temporal_consensus",
                        "support": face.supporting_frames,
                        "usable": face.usable_frames,
                        "confidence": face.mean_similarity,
                    },
                ]
            )
        if plate:
            trace.extend(
                [
                    {"stage": "plate_quality_and_ocr", "candidates": list(plate.raw_candidates)},
                    {
                        "stage": "character_consensus",
                        "state": plate.status.value,
                        "text": plate.final_text,
                        "agreement": plate.agreement,
                        "camera_count": len(plate.source_cameras),
                    },
                ]
            )
        if person_vehicle_association:
            trace.append({"stage": "person_vehicle_association", **person_vehicle_association})
        passport = EvidencePassport(
            passport_id=str(uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            entity_id=entity_id,
            decision_state="PENDING_HUMAN_REVIEW",
            face=face.to_dict() if face else None,
            plate=plate.to_dict() if plate else None,
            person_vehicle_association=person_vehicle_association,
            decision_trace=trace,
        )
        passport.seal()
        return passport

    def save(self, passport: EvidencePassport) -> Path:
        if not passport.verify_integrity():
            raise ValueError("Refusing to save a passport with an invalid integrity hash")
        self.output_directory.mkdir(parents=True, exist_ok=True)
        destination = self.output_directory / f"{passport.passport_id}.json"
        destination.write_text(json.dumps(passport.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return destination

    @staticmethod
    def load(path: str | Path) -> EvidencePassport:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        payload["human_review"] = HumanReview(**payload.get("human_review", {}))
        passport = EvidencePassport(**payload)
        if not passport.verify_integrity():
            raise ValueError("Evidence Passport integrity check failed")
        return passport
