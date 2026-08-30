"""Utility script to check and download pre-trained TransReID & detector model weights."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = ROOT / "weights"

# Public pre-trained weight URLs / mirrors
WEIGHT_URLS = {
    "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
}


def download_file(url: str, dest_path: Path) -> None:
    print(f"Downloading {dest_path.name} from {url}...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest_path)
    print(f"Saved to {dest_path}")


def ensure_weights(transreid: bool = False) -> None:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Ensure YOLO weights in root or weights dir
    yolo_root = ROOT / "yolov8n.pt"
    if not yolo_root.exists():
        download_file(WEIGHT_URLS["yolov8n.pt"], yolo_root)
    else:
        print(f"Found YOLO weights: {yolo_root}")

    transreid_path = WEIGHTS_DIR / "transreid_vit_base.onnx"
    if transreid:
        if not transreid_path.exists():
            print(f"TransReID weights missing at {transreid_path}.")
            print("Run the cloud training notebook 'scripts/train_transreid_colab.ipynb' on Google Colab / GCP GPU")
            print("and place 'transreid_vit_base.onnx' in the weights/ directory.")
        else:
            print(f"Found TransReID weights: {transreid_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download model weights")
    parser.add_argument("--transreid", action="store_true", help="Check TransReID model weights")
    args = parser.parse_args()
    ensure_weights(transreid=args.transreid)


if __name__ == "__main__":
    main()
