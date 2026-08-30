"""Unit tests for TransReID Vision Transformer embedder."""

import numpy as np
from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.reid.embedder import TransReIDEmbedder, build_embedder


def test_transreid_embedder_dimension_and_norm():
    embedder = TransReIDEmbedder()
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    bbox = (100.0, 100.0, 250.0, 400.0)

    vec = embedder.embed(frame, bbox)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (768,)
    # Verify L2 normalization
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0, atol=1e-4)


def test_transreid_factory_build():
    cfg = TrackingConfig(embedder="transreid")
    embedder = build_embedder(cfg)
    assert embedder.name == "transreid"
