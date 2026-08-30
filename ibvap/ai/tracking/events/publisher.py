from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

from ibvap.configs.config import TrackingConfig
from src.events.payload import build_event_payload
from src.events.severity import determine_severity

logger = logging.getLogger(__name__)


class MockBackendReceiver:
    """Mock receiver for Person 4 backend event ingestion testing and JSON schema compliance verification."""

    REQUIRED_KEYS = {"event_id", "event_type", "timestamp", "camera_id", "entity", "detection", "severity"}

    def __init__(self) -> None:
        self.received_events: list[dict] = []

    def receive(self, payload: dict) -> bool:
        """Validate event payload schema compliance and store event locally."""
        missing = self.REQUIRED_KEYS - set(payload.keys())
        if missing:
            raise ValueError(f"Payload schema invalid: missing required fields {missing}")
        self.received_events.append(payload)
        return True

    def clear(self) -> None:
        self.received_events.clear()

    def get_events(self) -> list[dict]:
        return list(self.received_events)


class EventPublisher:
    """Only send path: validate → severity → idempotency → HTTP with retry queue."""

    def __init__(self, cfg: TrackingConfig, mock_receiver: MockBackendReceiver | None = None):
        self.cfg = cfg
        self.mock_receiver = mock_receiver
        self.queue: deque[dict] = deque()
        self.queue_path = Path(cfg.queue_path)
        self._load_queue()

    def emit(
        self,
        event_type: str,
        track_id,
        bbox,
        camera_id: str,
        confidence: float,
        extra: dict | None = None,
    ) -> dict:
        severity = determine_severity(event_type, confidence, extra)
        payload = build_event_payload(
            event_type=event_type,
            track_id=track_id,
            bbox=bbox,
            camera_id=camera_id,
            confidence=confidence,
            severity=severity,
            extra=extra,
        )
        self._append_to_file(payload)
        self.queue.append(payload)
        self.flush()
        return payload

    def _append_to_file(self, payload: dict) -> None:
        try:
            with self.queue_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
                handle.flush()
        except OSError as exc:
            logger.warning("could not append event to file: %s", exc)

    def flush(self) -> None:
        pending = list(self.queue)
        self.queue.clear()
        for payload in pending:
            if self._send(payload):
                continue
            self.queue.append(payload)

    def _send(self, payload: dict) -> bool:
        if self.mock_receiver is not None:
            return self.mock_receiver.receive(payload)
        url = (self.cfg.backend_url or "").strip()
        if not url:
            logger.info("event_log %s", json.dumps(payload))
            return True
        body = json.dumps(payload).encode("utf-8")
        delay = self.cfg.retry_backoff_sec
        for attempt in range(self.cfg.max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "Idempotency-Key": payload.get("idempotency_key", ""),
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.cfg.backend_timeout_sec) as resp:
                    if 200 <= resp.status < 300:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                logger.warning("backend send failed attempt=%s err=%s", attempt + 1, exc)
            time.sleep(delay)
            delay *= 2
        return False

    def _persist(self) -> None:
        try:
            with self.queue_path.open("w", encoding="utf-8") as handle:
                for item in self.queue:
                    handle.write(json.dumps(item) + "\n")
        except OSError as exc:
            logger.warning("could not persist event queue: %s", exc)


    def _load_queue(self) -> None:
        if not self.queue_path.exists():
            return
        try:
            for line in self.queue_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.queue.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            return

