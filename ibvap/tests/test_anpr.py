from datetime import datetime, timedelta, timezone

from ai.anpr.consensus import PlateConsensus, align_to_reference, text_similarity
from ai.anpr.india_format import assess_indian_format, normalize_plate
from ai.common.config import ANPRConfig
from ai.contracts import (
    BoundingBox,
    EvidenceState,
    PlateFrameResult,
    QualityAssessment,
    QualityState,
)


def good_quality() -> QualityAssessment:
    return QualityAssessment(QualityState.GOOD, 0.95, 130.0, 90.0, 0.0)


def plate(camera: str, frame: int, track: int, text: str) -> PlateFrameResult:
    return PlateFrameResult(
        camera,
        frame,
        datetime.now(timezone.utc) + timedelta(milliseconds=frame),
        track,
        BoundingBox(1, 1, 120, 40),
        text,
        normalize_plate(text),
        tuple(0.9 for _ in text),
        0.94,
        0.91,
        EvidenceState.PARTIAL,
        good_quality(),
        model_name="test/anpr",
    )


def test_india_grammar_is_soft_and_non_destructive():
    exact = assess_indian_format("mh-12-ab-1234")
    assert exact.normalized == "MH12AB1234"
    assert exact.score == 1.0
    assert exact.suggestion is None

    confused = assess_indian_format("MHI2ABI234")
    assert confused.normalized == "MHI2ABI234"
    assert confused.suggestion == "MH12AB1234"


def test_alignment_handles_dropped_character():
    aligned = align_to_reference("MH12AB1234", "MH12A1234")
    assert len(aligned) == 10
    assert aligned[5] is None
    assert text_similarity("MH12AB1234", "MH12A1234") == 0.9


def test_cross_camera_consensus_and_character_provenance():
    config = ANPRConfig(
        min_supporting_frames=3,
        min_character_agreement=0.55,
        min_verified_agreement=0.70,
    )
    consensus = PlateConsensus(config)
    results = [
        consensus.add(plate("CAM-A", 1, 91, "MH12AB1234"), "GLOBAL-CAR"),
        consensus.add(plate("CAM-A", 2, 91, "MH12A81234"), "GLOBAL-CAR"),
        consensus.add(plate("CAM-B", 3, 12, "MH12AB1234"), "GLOBAL-CAR"),
        consensus.add(plate("CAM-B", 4, 12, "MH12AB1234"), "GLOBAL-CAR"),
    ]
    final = results[-1]
    assert final.status == EvidenceState.VERIFIED
    assert final.final_text == "MH12AB1234"
    assert final.source_cameras == ("CAM-A", "CAM-B")
    assert final.track_keys == ("CAM-A:91", "CAM-B:12")
    assert final.provenance[5].character == "B"
    assert set(final.provenance[5].cameras) == {"CAM-A", "CAM-B"}
    assert any(result.event_ready for result in results)
    assert final.event_ready is False  # duplicate alert suppressed during cooldown
