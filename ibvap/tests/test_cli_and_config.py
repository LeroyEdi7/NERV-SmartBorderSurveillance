import numpy as np

from ibvap.configs.config import load_config
from ibvap.ai.tracking.pipeline import build_parser, main
from ibvap.ai.tracking.reid.embedder import HistogramEmbedder, build_embedder


def test_cli_help():
    parser = build_parser()
    help_text = parser.format_help()
    assert "--source" in help_text
    assert "--dummy" in help_text


def test_main_help_exits_zero():
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("expected SystemExit(0) from --help")


def test_load_config_thresholds():
    cfg = load_config()
    assert cfg.overlap_threshold == 0.6
    assert cfg.min_duration_sec == 1.5
    assert cfg.reid_cosine_threshold == 0.7
    assert cfg.embedding_buffer_size == 5
    assert cfg.occlusion_ttl_sec >= 5.0
    assert cfg.topology.is_adjacent("cam1", "cam2")


def test_auto_embedder_falls_back_to_histogram():
    from ibvap.configs.config import TrackingConfig

    cfg = TrackingConfig(embedder="auto")
    emb = build_embedder(cfg)
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[10:40, 10:30] = (12, 80, 200)
    vec = emb.embed(frame, (10, 10, 30, 40))
    assert vec.ndim == 1
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-3


def test_histogram_same_crop_high_cosine():
    emb = HistogramEmbedder()
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    frame[20:60, 20:40, 1] = 180
    a = emb.embed(frame, (20, 20, 40, 60))
    b = emb.embed(frame, (20, 20, 40, 60))
    assert float(np.dot(a, b)) > 0.99
