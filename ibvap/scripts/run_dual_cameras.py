"""Dual IP Webcam Real-Time Multi-Camera Tracking & Re-ID Handoff Runner.

Connects to 2 live IP phone cameras (e.g. http://192.168.1.5:8080/video) or webcams,
runs Deep-OC-SORT / ByteTrack tracking, TransReID feature extraction, and real-time
cross-camera re-identification handoff between Camera 1 (cam1) and Camera 2 (cam2).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure root workspace path is in sys.path for direct script execution
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from ibvap.configs.config import load_config
from ibvap.ai.detection import build_detector
from ibvap.ai.tracking.handoff import CrossCameraHandoff, InMemoryGalleryStore
from ibvap.ai.tracking.reid import build_embedder
from ibvap.ai.tracking import HybridTracker


def format_url(stream_input: str) -> str | int:
    """Format user input into OpenCV-compatible video stream URL or camera index."""
    if stream_input.isdigit():
        return int(stream_input)
    # If user provided raw IP like '192.168.1.5:8080', format it as HTTP video stream URL
    if not stream_input.startswith("http://") and not stream_input.startswith("rtsp://") and not stream_input.endswith(".mp4"):
        if ":" in stream_input and not stream_input.startswith("http"):
            return f"http://{stream_input}/video"
        if not stream_input.startswith("http"):
            return f"http://{stream_input}:8080/video"
    return stream_input


def run_dual_cameras(
    cam1_url: str,
    cam2_url: str,
    tracker_type: str = "deep_ocsort",
    embedder_type: str = "transreid",
    no_display: bool = False,
) -> None:
    cfg = load_config()
    cfg.tracker_type = tracker_type
    cfg.embedder = embedder_type

    print("=" * 65)
    print(" DUAL IP CAMERA RE-ID TRACKING RUNNER")
    print(f" Camera 1 (cam1): {cam1_url}")
    print(f" Camera 2 (cam2): {cam2_url}")
    print(f" Tracker: {cfg.tracker_type} | Embedder: {cfg.embedder}")
    print("=" * 65)

    # Build shared components
    detector = build_detector(cfg)
    embedder = build_embedder(cfg)

    # Camera 1 Pipeline Components
    tracker_cam1 = HybridTracker(cfg, embedder)
    
    # Camera 2 Pipeline Components
    tracker_cam2 = HybridTracker(cfg, embedder)

    # Shared Cross-Camera Gallery Handoff Engine
    shared_gallery = InMemoryGalleryStore()
    handoff_engine = CrossCameraHandoff(cfg, store=shared_gallery)

    # Open Video Streams
    cap1 = cv2.VideoCapture(format_url(cam1_url))
    cap2 = cv2.VideoCapture(format_url(cam2_url))

    if not cap1.isOpened():
        print(f"[ERROR] Could not open Camera 1 stream: {cam1_url}")
        return
    if not cap2.isOpened():
        print(f"[ERROR] Could not open Camera 2 stream: {cam2_url}")
        return

    print("\n[INFO] Both streams connected successfully! Press 'q' or ESC to stop.\n")

    frame_idx = 0
    start_ts = time.time()

    try:
        while True:
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()

            if not ret1 or not ret2:
                print("[WARNING] Frame drop or stream disconnected. Retrying...")
                time.sleep(0.1)
                if not ret1 and not ret2:
                    break
                continue

            frame_idx += 1
            now_ts = time.time() - start_ts

            # -------------------------------------------------------------
            # PROCESS CAMERA 1 (cam1)
            # -------------------------------------------------------------
            if ret1:
                dets1 = detector.detect(frame1)
                tracks1 = tracker_cam1.update(frame1, dets1, camera_id="cam1", now_ts=now_ts)

                # Monitor exit boundary on Camera 1
                handoff_engine.observe_exits(
                    tracks1, camera_id="cam1", now_ts=now_ts, frame_wh=(frame1.shape[1], frame1.shape[0])
                )

                # Annotate Camera 1 Frame
                for trk in tracks1:
                    x1, y1, x2, y2 = [int(v) for v in trk.bbox]
                    entity_label = trk.effective_entity_id
                    label = f"cam1 | P-{trk.track_id} ({entity_label})"
                    cv2.rectangle(frame1, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame1, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # -------------------------------------------------------------
            # PROCESS CAMERA 2 (cam2)
            # -------------------------------------------------------------
            if ret2:
                dets2 = detector.detect(frame2)
                tracks2 = tracker_cam2.update(frame2, dets2, camera_id="cam2", now_ts=now_ts)

                # Perform Cross-Camera Re-ID Handoff matching for new entries on Camera 2
                for trk in tracks2:
                    if trk.embeddings and not trk.entity_id:
                        latest_emb = trk.embeddings[-1]
                        match = handoff_engine.try_match(
                            embedding=latest_emb,
                            camera_id="cam2",
                            class_name=trk.class_name,
                            now_ts=now_ts,
                        )
                        if match:
                            matched_tid, conf = match
                            global_entity = f"G-{matched_tid:03d}"
                            tracker_cam2.bind_entity(trk.track_id, entity_id=global_entity, entity_type=trk.class_name)
                            print(f"[RE-ID MATCH!] Camera 2 Track P-{trk.track_id} matched to Camera 1 Exit Track P-{matched_tid} -> Entity {global_entity} (Conf: {conf:.2f})")

                # Annotate Camera 2 Frame
                for trk in tracks2:
                    x1, y1, x2, y2 = [int(v) for v in trk.bbox]
                    entity_label = trk.effective_entity_id
                    color = (255, 165, 0) if trk.entity_id else (255, 0, 0) # Orange if matched cross-camera
                    label = f"cam2 | P-{trk.track_id} ({entity_label})"
                    cv2.rectangle(frame2, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame2, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # -------------------------------------------------------------
            # DISPLAY DISPLAY WINDOWS
            # -------------------------------------------------------------
            if not no_display:
                # Resize to standard preview size
                p1 = cv2.resize(frame1, (640, 360))
                p2 = cv2.resize(frame2, (640, 360))
                combined = np.hstack((p1, p2))
                
                cv2.putText(combined, "CAMERA 1 (cam1)", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                cv2.putText(combined, "CAMERA 2 (cam2)", (660, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
                
                cv2.imshow("Dual Camera Tracking & Cross-Camera Re-ID Handoff", combined)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break

    finally:
        cap1.release()
        cap2.release()
        cv2.destroyAllWindows()
        print("\n[INFO] Stopped dual camera tracking streams.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Dual IP Webcam Cross-Camera Re-ID Pipeline")
    parser.add_argument("--cam1", required=True, help="IP address/URL for Camera 1 (e.g. 192.168.1.5:8080 or http://192.168.1.5:8080/video)")
    parser.add_argument("--cam2", required=True, help="IP address/URL for Camera 2 (e.g. 192.168.1.6:8080 or http://192.168.1.6:8080/video)")
    parser.add_argument("--tracker", default="deep_ocsort", choices=["deep_ocsort", "bytetrack"])
    parser.add_argument("--embedder", default="transreid", choices=["transreid", "osnet", "deepsort", "histogram"])
    parser.add_argument("--no-display", action="store_true")
    args = parser.parse_args()

    run_dual_cameras(
        cam1_url=args.cam1,
        cam2_url=args.cam2,
        tracker_type=args.tracker,
        embedder_type=args.embedder,
        no_display=args.no_display,
    )


if __name__ == "__main__":
    main()
