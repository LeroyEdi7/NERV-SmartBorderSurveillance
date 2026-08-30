from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ibvap.configs.config import load_config
from src.pipeline import run_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Phase 6 Demonstration Pipeline Runner")
    parser.add_argument("--scenario", default="occlusion", choices=["normal", "occlusion", "vehicle_entry"])
    parser.add_argument("--camera-id", default="BOP-01")
    parser.add_argument("--max-frames", type=int, default=50)
    args = parser.parse_args()

    print("=" * 60)
    print(f"      PHASE 6: CLI DEMONSTRATION ({args.scenario.upper()} SCENARIO)")
    print("=" * 60)

    cfg = load_config()
    queue_file = Path("demo_events.jsonl")
    if queue_file.exists():
        queue_file.unlink()
    cfg.queue_path = str(queue_file)

    logger.info("Running synthetic dummy pipeline simulation (scenario=%s, camera_id=%s, max_frames=%d)...",
                args.scenario, args.camera_id, args.max_frames)

    run_loop(
        cfg=cfg,
        source="synthetic",
        camera_id=args.camera_id,
        dummy=True,
        display=False,
        redis_url=None,
        max_frames=args.max_frames,
        scenario=args.scenario,
    )

    if queue_file.exists():
        lines = queue_file.read_text(encoding="utf-8").strip().splitlines()
        print("\n" + "=" * 60)
        print(f"         DEMO EVENT LOG OUTPUT (Total Events: {len(lines)})")
        print("=" * 60)
        for i, line in enumerate(lines[:3]):
            data = json.loads(line)
            print(f"\n--- Event #{i+1} ---")
            print(json.dumps(data, indent=2))
        queue_file.unlink()
        print("\nSUCCESS: Phase 6 CLI Demonstration Pipeline run completed successfully.")
    else:
        print("\nNo events logged.")


if __name__ == "__main__":
    main()
