from __future__ import annotations

import argparse
import logging
import time

import numpy as np

from src.association.person_vehicle import PersonVehicleAssociator
from ibvap.configs.config import TrackingConfig, load_config
from ibvap.ai.detection import DummyDetector, build_detector
from ibvap.ai.tracking.events.publisher import EventPublisher
from ibvap.ai.tracking.handoff.gallery import CrossCameraHandoff, InMemoryGalleryStore, RedisGalleryStore
from ibvap.ai.tracking.reid.embedder import build_embedder
from ibvap.ai.tracking.hybrid import HybridTracker, MockIdentityBinder


logger = logging.getLogger(__name__)


class ImageVideoCapture:
    def __init__(self, image_path: str, repeat_count: int = 1):
        import cv2
        from pathlib import Path

        self.image_path = image_path
        self.frame = cv2.imread(image_path)
        if self.frame is None:
            logger.error("Could not read image from path: %s", image_path)
        else:
            logger.info("Successfully loaded static image: %s (shape %s)", image_path, self.frame.shape)
        self.repeat_count = repeat_count
        self.count = 0

    def isOpened(self) -> bool:
        return self.frame is not None and self.count < self.repeat_count

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self.isOpened():
            return False, None
        self.count += 1
        return True, self.frame.copy()

    def release(self) -> None:
        self.count = self.repeat_count


class SyntheticVideoCapture:
    def __init__(self, width: int = 640, height: int = 480, max_frames: int = 100):
        self.width = width
        self.height = height
        self.max_frames = max_frames
        self.count = 0

    def isOpened(self) -> bool:
        return self.count < self.max_frames

    def read(self) -> tuple[bool, np.ndarray]:
        if self.count >= self.max_frames:
            return False, np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.count += 1
        frame = np.full((self.height, self.width, 3), 40, dtype=np.uint8)
        return True, frame

    def release(self) -> None:
        pass




def _test_and_warmup(cap, retries: int = 20, delay: float = 0.05, require_non_black: bool = False) -> bool:
    import time

    for _ in range(retries):
        if not cap.isOpened():
            return False
        ok, frame = cap.read()
        if ok and frame is not None and frame.size > 0:
            if require_non_black and float(frame.max()) == 0.0:
                time.sleep(delay)
                continue
            return True
        time.sleep(delay)
    return False


def _try_open_camera_idx(idx: int, api_pref: int | None = None):
    import cv2

    cap = cv2.VideoCapture(idx, api_pref) if api_pref is not None else cv2.VideoCapture(idx)
    if not cap.isOpened():
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    try:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    except Exception:
        pass

    if _test_and_warmup(cap, retries=15, require_non_black=True):
        return cap

    # Retry without strict non-black check if no other camera stream is found
    if _test_and_warmup(cap, retries=5, require_non_black=False):
        return cap

    cap.release()
    return None


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}


def _open_source(source: str, dummy: bool = False, max_frames: int | None = None):
    import sys
    import cv2
    from pathlib import Path

    if dummy or source == "synthetic":
        return SyntheticVideoCapture(max_frames=max_frames or 100)

    if source.isdigit():
        requested_idx = int(source)
        candidate_indices = [requested_idx] + [i for i in range(4) if i != requested_idx]

        for idx in candidate_indices:
            # 1. Try DirectShow on Windows
            if sys.platform == "win32":
                cap = _try_open_camera_idx(idx, cv2.CAP_DSHOW)
                if cap is not None:
                    if idx != requested_idx:
                        logger.info(
                            "Camera index %d produced black frames; automatically switched to active RGB camera index %d (CAP_DSHOW)",
                            requested_idx,
                            idx,
                        )
                    else:
                        logger.info("Successfully opened webcam index %d via DirectShow (CAP_DSHOW)", idx)
                    return cap

                # 2. Try MSMF on Windows
                cap = _try_open_camera_idx(idx, cv2.CAP_MSMF)
                if cap is not None:
                    logger.info("Successfully opened webcam index %d via MSMF", idx)
                    return cap

            # 3. Default VideoCapture
            cap = _try_open_camera_idx(idx, None)
            if cap is not None:
                logger.info("Successfully opened webcam index %d via default VideoCapture", idx)
                return cap

        logger.warning(
            "Could not capture valid video frames from webcam index %s or alternative cameras. Falling back to synthetic feed.",
            source,
        )
        return SyntheticVideoCapture(max_frames=max_frames or 100)

    p = Path(source)
    if p.suffix.lower() in IMAGE_EXTENSIONS:
        return ImageVideoCapture(source, repeat_count=max_frames or 1)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.warning("Could not open video source %s. Falling back to synthetic feed.", source)
        return SyntheticVideoCapture(max_frames=max_frames or 100)

    if not _test_and_warmup(cap):
        logger.warning("Could not open video source %s. Falling back to synthetic feed.", source)
        return SyntheticVideoCapture(max_frames=max_frames or 100)

    if p.is_file():
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    return cap




def _draw(frame: np.ndarray, tracks, events: list[dict], lost_count: int = 0) -> np.ndarray:
    import cv2

    vis = frame.copy()
    for track in tracks:
        x1, y1, x2, y2 = [int(v) for v in track.bbox]
        color = (40, 200, 40) if track.class_name == "person" else (40, 140, 220)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        label = f"{track.class_name[0]}:{track.track_id}"
        if track.re_identification_confidence is not None:
            label += f" r={track.re_identification_confidence:.2f}"
        elif hasattr(track, "score") and track.score is not None:
            label += f" c={track.score:.2f}"

        if track.entity_id:
            label += f" [{track.entity_id}]"
        cv2.putText(vis, label, (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.putText(vis, f"Active Tracks: {len(tracks)} | Lost Buffered: {lost_count}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    if events:
        cv2.putText(vis, f"Events: {len(events)}", (8, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return vis


def _apply_gallery_match(tracker: HybridTracker, handoff: CrossCameraHandoff, tracks, camera_id: str, now_ts: float, publisher: EventPublisher) -> None:
    for track in tracks:
        if track.hits != 1 or not track.embeddings:
            continue
        match = handoff.try_match(
            embedding=track.embeddings[-1],
            camera_id=camera_id,
            class_name=track.class_name,
            now_ts=now_ts,
        )
        if match is None:
            continue
        tid, conf = match
        track.track_id = tid
        track.re_identification_confidence = conf
        tracker.byte.set_next_id(tid + 1)
        publisher.emit(
            event_type="cross_camera_match",
            track_id=tid,
            bbox=track.bbox,
            camera_id=camera_id,
            confidence=conf,
            extra={"matched_on_camera": camera_id},
        )


def run_loop(
    cfg: TrackingConfig,
    source: str,
    camera_id: str,
    dummy: bool,
    display: bool,
    redis_url: str | None,
    max_frames: int | None = None,
    scenario: str = "normal",
) -> None:
    detector = DummyDetector(scenario=scenario) if dummy else build_detector(cfg, dummy=False)
    embedder = build_embedder(cfg)
    logger.info("embedder=%s camera_id=%s scenario=%s", getattr(embedder, "name", type(embedder).__name__), camera_id, scenario)
    tracker = HybridTracker(cfg, embedder)
    binder = MockIdentityBinder(tracker)
    associator = PersonVehicleAssociator(cfg)
    store = RedisGalleryStore(redis_url) if redis_url else InMemoryGalleryStore()
    handoff = CrossCameraHandoff(cfg, store=store)
    publisher = EventPublisher(cfg)

    cap = _open_source(source, dummy=dummy, max_frames=max_frames)

    frame_idx = 0
    t0 = time.time()
    consecutive_failures = 0
    emitted_new_tracks: set[int] = set()
    video_writer = None

    from pathlib import Path

    is_image_input = isinstance(cap, ImageVideoCapture)
    is_video_file = Path(source).is_file() and Path(source).suffix.lower() not in IMAGE_EXTENSIONS

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None or frame.size == 0:
                if is_video_file or is_image_input:
                    logger.info("End of video stream reached.")
                    break
                consecutive_failures += 1
                if consecutive_failures > 30:
                    logger.warning("Failed to grab frames for 30 consecutive attempts. Exiting stream.")
                    break
                time.sleep(0.02)
                continue

            consecutive_failures = 0
            now_ts = time.time()
            detections = detector.detect(frame)
            tracks = tracker.update(frame, detections, camera_id=camera_id, now_ts=now_ts)

            # Auto-bind mock Face ID for Person 3 biometric simulation
            for track in tracks:
                if track.hits >= 1:
                    entity_id = "G-001" if track.class_name == "person" else f"LP-{track.track_id:04d}"
                    binder.bind_entity(track.track_id, entity_id, track.class_name)

                # Emit event to publisher (writes to event_queue.jsonl)
                if track.track_id not in emitted_new_tracks and track.hits >= 1:
                    emitted_new_tracks.add(track.track_id)
                    publisher.emit(
                        event_type="person_detected" if track.class_name == "person" else "vehicle_person_association",
                        track_id=track.track_id,
                        bbox=track.bbox,
                        camera_id=camera_id,
                        confidence=track.score,
                        extra={"entity_id": track.entity_id} if track.entity_id else None,
                    )

            _apply_gallery_match(tracker, handoff, tracks, camera_id, now_ts, publisher)
            h, w = frame.shape[:2]
            handoff.observe_exits(tracks, camera_id, now_ts, (w, h))
            assoc_events = associator.update(tracks, now_ts)
            for event in assoc_events:
                publisher.emit(
                    event_type="vehicle_person_association",
                    track_id=event["track_id"],
                    bbox=event["bbox"],
                    camera_id=camera_id,
                    confidence=event["confidence"],
                    extra=event.get("metadata"),
                )
            frame_idx += 1
            is_image_input = isinstance(cap, ImageVideoCapture)
            if display and cfg.draw:
                import cv2

                fps = frame_idx / max(1e-6, time.time() - t0)
                vis = _draw(frame, tracks, assoc_events, lost_count=len(tracker.lost))
                if not is_image_input:
                    cv2.putText(vis, f"{fps:.1f} fps", (8, vis.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                if is_image_input:
                    out_path = f"output_{Path(cap.image_path).name}"
                    cv2.imwrite(out_path, vis)
                    logger.info("Successfully saved annotated output image to %s", out_path)

                if is_video_file:
                    if video_writer is None:
                        out_vpath = f"output_{Path(source).stem}.mp4"
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        video_writer = cv2.VideoWriter(out_vpath, fourcc, cfg.fps, (w, h))
                        logger.info("Initialized output video recording to %s (%dx%d @ %.1ffps)", out_vpath, w, h, cfg.fps)
                    video_writer.write(vis)

                window_title = f"Tracking Preview: {camera_id}"
                cv2.imshow(window_title, vis)
                key = cv2.waitKey(0 if is_image_input else 1) & 0xFF
                if key in (27, ord("q")):
                    break
                try:
                    if cv2.getWindowProperty(window_title, cv2.WND_PROP_VISIBLE) < 1:
                        break
                except Exception:
                    pass
            if max_frames is not None and frame_idx >= max_frames:
                break

    finally:
        if video_writer is not None:
            video_writer.release()
            logger.info("Saved annotated prediction video file to disk.")
        cap.release()
        try:
            import cv2

            cv2.destroyAllWindows()
        except Exception:
            pass
        publisher.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="src.pipeline",
        description="Hybrid ByteTrack + ReID tracking pipeline (single-camera loop, occlusion recovery, handoff, events).",
    )
    parser.add_argument("--source", default="0", help="Video file path, webcam index, or image file")
    parser.add_argument("--video", default=None, help="Path to video file for testing")
    parser.add_argument("--image", default=None, help="Path to static image file for testing")
    parser.add_argument("--camera-id", default="cam1")
    parser.add_argument("--config", default=None, help="Path to configs/default.yaml")
    parser.add_argument("--cameras", default=None, help="Path to configs/cameras.yaml")
    parser.add_argument("--dummy", action="store_true", help="Use synthetic detections (no YOLO weights)")
    parser.add_argument("--scenario", default="normal", choices=["normal", "occlusion", "vehicle_entry"], help="Scenario for DummyDetector")
    parser.add_argument("--tracker", default=None, choices=["bytetrack", "deep_ocsort"], help="Tracker engine algorithm choice")
    parser.add_argument("--embedder", default=None, choices=["auto", "transreid", "osnet", "deepsort", "histogram"], help="Re-ID appearance embedder model choice")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--redis-url", default=None, help="Shared gallery Redis URL (multi-process)")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(args.config, args.cameras)
    if args.tracker:
        cfg.tracker_type = args.tracker
    if args.embedder:
        cfg.embedder = args.embedder
    source_val = str(args.video) if args.video else (str(args.image) if args.image else str(args.source))
    run_loop(
        cfg,
        source=source_val,
        camera_id=args.camera_id,
        dummy=bool(args.dummy),
        display=not args.no_display,
        redis_url=args.redis_url,
        max_frames=args.max_frames,
        scenario=args.scenario,
    )





if __name__ == "__main__":
    main()
