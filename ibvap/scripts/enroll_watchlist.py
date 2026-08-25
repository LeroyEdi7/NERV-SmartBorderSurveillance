#!/usr/bin/env python3
"""Enrol one consenting person from several clear reference photos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.common.config import load_config
from ai.common.image_ops import load_bgr_image
from ai.face.backend import InsightFaceBackend
from ai.face.watchlist import WatchlistStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--person-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--consent-reference", required=True)
    parser.add_argument("--images", nargs="+", required=True)
    parser.add_argument("--config", default="configs/person3.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    backend = InsightFaceBackend(
        config.face.model_pack,
        config.face.providers,
        config.face.detection_size,
        config.face.model_root,
    )
    embeddings = []
    for path in args.images:
        faces = backend.detect(load_bgr_image(path))
        if len(faces) != 1:
            raise ValueError(f"{path}: expected exactly one face, found {len(faces)}")
        embeddings.append(faces[0].embedding)
    store = WatchlistStore(config.watchlist_path, backend.model_name)
    store.enroll(args.person_id, args.name, embeddings, args.consent_reference)
    print(f"Enrolled {args.person_id} with {len(embeddings)} templates in {store.path}")


if __name__ == "__main__":
    main()
