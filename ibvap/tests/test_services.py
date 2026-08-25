from datetime import datetime, timezone

import numpy as np

from ai.anpr.service import ANPRService
from ai.common.config import ANPRConfig, FaceConfig
from ai.contracts import BoundingBox, EvidenceState, TrackObservation
from ai.face.service import FaceRecognitionService
from ai.face.watchlist import WatchlistStore
from ai.mocks import SequenceANPRBackend, SequenceFaceBackend


def frame():
    y, x = np.indices((360, 640))
    pattern = (((x // 4 + y // 4) % 2) * 100 + 80).astype(np.uint8)
    return np.stack([pattern, pattern, pattern], axis=-1)


def test_face_service_runs_without_person_one_or_two(tmp_path):
    embedding = np.array([1.0, 0.1, 0.0, 0.0])
    backend = SequenceFaceBackend([embedding] * 3)
    watchlist = WatchlistStore(tmp_path / "watchlist.json", backend.model_name)
    watchlist.enroll("WL-1", "Demo", [embedding], "CONSENT")
    config = FaceConfig(sample_every_n_frames=1, min_supporting_frames=3)
    service = FaceRecognitionService(backend, watchlist, config)
    output = None
    for index in range(3):
        output = service.process(
            TrackObservation(
                "CAM",
                index,
                datetime.now(timezone.utc),
                "person",
                1,
                BoundingBox(30, 10, 300, 340),
                frame(),
            )
        )
    assert output is not None and output.track is not None
    assert output.track.status == EvidenceState.MATCH_CANDIDATE


def test_anpr_service_fuses_global_vehicle_across_cameras():
    backend = SequenceANPRBackend(["MH12AB1234", "MH12A81234", "MH12AB1234"])
    config = ANPRConfig(sample_every_n_frames=1, min_supporting_frames=3)
    service = ANPRService(backend, config)
    output = None
    for index, camera in enumerate(("A", "A", "B")):
        output = service.process(
            TrackObservation(
                camera,
                index,
                datetime.now(timezone.utc),
                "vehicle",
                4 if camera == "A" else 9,
                BoundingBox(20, 30, 620, 340),
                frame(),
                global_entity_id="GLOBAL-CAR",
            )
        )
    assert output is not None and output.track is not None
    assert output.track.final_text == "MH12AB1234"
    assert set(output.track.source_cameras) == {"A", "B"}
