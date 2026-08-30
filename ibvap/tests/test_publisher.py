from ibvap.configs.config import TrackingConfig
from ibvap.ai.tracking.events.publisher import EventPublisher


def test_log_only_backend_drains_queue(tmp_path):
    cfg = TrackingConfig(backend_url="", queue_path=str(tmp_path / "q.jsonl"), max_retries=1)
    pub = EventPublisher(cfg)
    payload = pub.emit(
        event_type="cross_camera_match",
        track_id=1,
        bbox=[0, 0, 1, 1],
        camera_id="cam1",
        confidence=0.91,
    )
    assert payload["idempotency_key"]
    assert len(pub.queue) == 0


def test_failed_http_keeps_queue(tmp_path, monkeypatch):
    cfg = TrackingConfig(
        backend_url="http://127.0.0.1:1/events",
        queue_path=str(tmp_path / "q.jsonl"),
        max_retries=1,
        retry_backoff_sec=0.0,
        backend_timeout_sec=0.2,
    )
    monkeypatch.setattr("src.events.publisher.time.sleep", lambda *_: None)
    pub = EventPublisher(cfg)
    pub.emit(
        event_type="vehicle_person_association",
        track_id=9,
        bbox=[1, 2, 3, 4],
        camera_id="cam1",
        confidence=0.88,
    )
    assert len(pub.queue) == 1
    assert pub.queue[0]["idempotency_key"]
    persisted = (tmp_path / "q.jsonl").read_text(encoding="utf-8").strip()
    assert "vehicle_person_association" in persisted
