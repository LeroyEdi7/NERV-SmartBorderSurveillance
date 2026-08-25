from datetime import datetime, timedelta, timezone

import numpy as np

from ai.common.config import FaceConfig
from ai.contracts import (
    BoundingBox,
    EvidenceState,
    FaceFrameResult,
    QualityAssessment,
    QualityState,
)
from ai.face.consensus import FaceConsensus
from ai.face.watchlist import WatchlistStore


def good_quality() -> QualityAssessment:
    return QualityAssessment(QualityState.GOOD, 1.0, 120.0, 100.0, 0.0)


def test_watchlist_matches_and_rejects_ambiguous(tmp_path):
    store = WatchlistStore(tmp_path / "watchlist.json", "test/model")
    store.enroll("A", "Alpha", [np.array([1.0, 0.0, 0.0])], "CONSENT-A")
    store.enroll("B", "Beta", [np.array([0.0, 1.0, 0.0])], "CONSENT-B")

    match = store.match(np.array([0.99, 0.01, 0.0]), 0.4, 0.5, 0.04)
    assert match.status == EvidenceState.MATCH_CANDIDATE
    assert match.person_id == "A"

    ambiguous = store.match(np.array([0.7, 0.7, 0.0]), 0.4, 0.5, 0.04)
    assert ambiguous.status == EvidenceState.POSSIBLE_MATCH
    assert ambiguous.person_id is None
    assert "ambiguous_top_matches" in ambiguous.reasons


def test_face_consensus_requires_multiple_frames():
    config = FaceConfig(min_supporting_frames=3, min_support_ratio=0.6, event_cooldown_seconds=10)
    consensus = FaceConsensus(config)
    start = datetime.now(timezone.utc)
    outputs = []
    for frame_id in range(3):
        outputs.append(
            consensus.add(
                FaceFrameResult(
                    "CAM-1",
                    frame_id,
                    start + timedelta(milliseconds=frame_id),
                    4,
                    BoundingBox(1, 1, 100, 100),
                    EvidenceState.MATCH_CANDIDATE,
                    good_quality(),
                    "WATCH-1",
                    "Demo",
                    0.72,
                    0.22,
                    model_name="test/model",
                )
            )
        )
    assert outputs[1].status == EvidenceState.POSSIBLE_MATCH
    assert outputs[2].status == EvidenceState.MATCH_CANDIDATE
    assert outputs[2].event_ready is True

    duplicate = consensus.add(
        FaceFrameResult(
            "CAM-1",
            3,
            start + timedelta(seconds=1),
            4,
            BoundingBox(1, 1, 100, 100),
            EvidenceState.MATCH_CANDIDATE,
            good_quality(),
            "WATCH-1",
            "Demo",
            0.75,
            0.20,
            model_name="test/model",
        )
    )
    assert duplicate.event_ready is False
