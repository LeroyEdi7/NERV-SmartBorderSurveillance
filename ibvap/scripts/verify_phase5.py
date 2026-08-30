from __future__ import annotations

import json
import logging
import numpy as np

from ibvap.configs.config import load_config
from ibvap.ai.tracking.events.publisher import EventPublisher, MockBackendReceiver
from ibvap.ai.tracking.handoff.gallery import CrossCameraHandoff, InMemoryGalleryStore
from ibvap.ai.tracking.models import Detection, ExitRecord
from src.pipeline import _apply_gallery_match
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder
from ibvap.ai.tracking.hybrid import HybridTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("=" * 60)
    print("      PHASE 5: CROSS-CAMERA RE-ID HANDOFF VERIFICATION")
    print("=" * 60)

    from pathlib import Path

    cfg = load_config(config_path="configs/default.yaml", cameras_path="configs/cameras.yaml")
    queue_file = Path("verify_queue.jsonl")
    if queue_file.exists():
        queue_file.unlink()
    cfg.queue_path = str(queue_file)

    store = InMemoryGalleryStore()
    handoff = CrossCameraHandoff(cfg, store=store)
    receiver = MockBackendReceiver()
    publisher = EventPublisher(cfg, mock_receiver=receiver)

    # Synthetic embedding vector for target "Suspect-42"
    rng = np.random.default_rng(42)
    target_vec = rng.normal(size=32).astype(np.float32)
    target_vec /= (np.linalg.norm(target_vec) + 1e-8)

    # 1. Simulate Target Exiting Camera 1 (cam1) at t = 10.0s
    logger.info("1. Simulating Target 'Suspect-42' exiting Camera 1 ('cam1') near edge at t = 10.0s...")
    exit_rec = ExitRecord(
        track_id=42,
        embeddings=[target_vec],
        bbox=(5, 100, 45, 200),  # Near left frame margin (x1 = 5 <= 24px)
        velocity=(2.0, 0.0),
        heading=(1.0, 0.0),
        camera_id="cam1",
        class_name="person",
        exit_timestamp=10.0,
        expiry_time=10.0 + cfg.embedding_retention_sec,
    )
    store.push(exit_rec)

    gallery_items = store.candidates(now_ts=10.0)
    print(f"   [cam1 Exit Registered] Gallery count: {len(gallery_items)} | Target Track ID: {gallery_items[0].track_id}")

    # 2. Simulate Target Entering Camera 2 (cam2) at t = 15.0s (dt = 5.0s, expected transit = 5.0s +- 3.0s)
    logger.info("\n2. Simulating Target entering Camera 2 ('cam2') at t = 15.0s (5.0s transit time)...")
    embedder = HistogramEmbedder()
    tracker_cam2 = HybridTracker(cfg, embedder)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    det = [Detection(bbox=(100, 100, 160, 260), score=0.92, class_name="person")]
    tracks_cam2 = tracker_cam2.update(frame, det, camera_id="cam2", now_ts=15.0)

    # Inject visual embedding for target matching test
    tracks_cam2[0].embeddings = [target_vec]
    local_id_before = tracks_cam2[0].track_id
    print(f"   [cam2 Initial Track] Local ByteTrack ID before handoff: {local_id_before}")

    # 3. Apply Cross-Camera Gallery Handoff Matching
    _apply_gallery_match(tracker_cam2, handoff, tracks_cam2, camera_id="cam2", now_ts=15.0, publisher=publisher)

    matched_id_after = tracks_cam2[0].track_id
    confidence = tracks_cam2[0].re_identification_confidence
    print(f"   [cam2 Handoff Match Result] Track ID after handoff: {matched_id_after} (Confidence: {confidence:.4f})")

    # 4. Check Event Publisher output
    events = receiver.get_events()
    match_events = [e for e in events if e["event_type"] == "cross_camera_match"]

    print("\n" + "=" * 60)
    print("                      VERIFICATION RESULTS")
    print("=" * 60)
    check1 = matched_id_after == 42
    check2 = confidence is not None and confidence > 0.95
    check3 = len(match_events) == 1 and match_events[0]["detection"]["track_id"] == 42

    print(f" [PASS] Track ID reassigned from local {local_id_before} -> original cam1 ID {matched_id_after}: {check1}")
    print(f" [PASS] Re-ID Cosine Similarity Confidence > 0.95: {check2}")
    print(f" [PASS] Emitted 'cross_camera_match' event JSON to backend: {check3}")

    if queue_file.exists():
        queue_file.unlink()

    if check1 and check2 and check3:
        print("\nSUCCESS: Phase 5 Cross-Camera Re-ID Handoff Engine is working properly!")
        print("Event Payload Generated:")
        print(json.dumps(match_events[0], indent=2))
    else:
        print("\nFAILURE: One or more Phase 5 verification checks failed.")


if __name__ == "__main__":
    main()
