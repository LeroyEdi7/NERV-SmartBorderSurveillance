"""Multi-frame consensus for face watchlist candidates."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

from ai.common.config import FaceConfig
from ai.contracts import EvidenceState, FaceFrameResult, FaceTrackResult, QualityState


class FaceConsensus:
    def __init__(self, config: FaceConfig) -> None:
        self.config = config
        self._windows: dict[str, deque[FaceFrameResult]] = defaultdict(
            lambda: deque(maxlen=config.consensus_window)
        )
        self._last_emitted: dict[tuple[str, str], datetime] = {}

    def add(self, result: FaceFrameResult) -> FaceTrackResult:
        key = f"{result.camera_id}:{result.track_id}"
        window = self._windows[key]
        window.append(result)
        usable = [item for item in window if item.quality.state != QualityState.UNUSABLE]
        candidates = [item for item in usable if item.watchlist_id]
        counts: dict[str, list[FaceFrameResult]] = defaultdict(list)
        for item in candidates:
            counts[str(item.watchlist_id)].append(item)

        winner_id: str | None = None
        supporting: list[FaceFrameResult] = []
        if counts:
            winner_id, supporting = max(
                counts.items(),
                key=lambda item: (len(item[1]), sum(frame.similarity or 0.0 for frame in item[1])),
            )
        support_ratio = len(supporting) / len(usable) if usable else 0.0
        confirmed = (
            winner_id is not None
            and len(supporting) >= self.config.min_supporting_frames
            and support_ratio >= self.config.min_support_ratio
        )
        if confirmed:
            status = EvidenceState.MATCH_CANDIDATE
        elif winner_id:
            status = EvidenceState.POSSIBLE_MATCH
        else:
            status = EvidenceState.UNRESOLVED

        event_ready = False
        if confirmed and winner_id:
            emitted_key = (key, winner_id)
            last = self._last_emitted.get(emitted_key)
            newest = result.timestamp
            if last is None or (newest - last).total_seconds() >= self.config.event_cooldown_seconds:
                event_ready = True
                self._last_emitted[emitted_key] = newest

        reasons: list[str] = []
        if len(usable) < self.config.min_supporting_frames:
            reasons.append("insufficient_usable_frames")
        if winner_id and support_ratio < self.config.min_support_ratio:
            reasons.append("insufficient_consensus_ratio")
        display_name = supporting[0].display_name if supporting else None
        similarities = [item.similarity for item in supporting if item.similarity is not None]
        return FaceTrackResult(
            camera_id=result.camera_id,
            track_id=result.track_id,
            status=status,
            watchlist_id=winner_id,
            display_name=display_name,
            supporting_frames=len(supporting),
            usable_frames=len(usable),
            total_frames=len(window),
            mean_similarity=(sum(similarities) / len(similarities)) if similarities else None,
            source_frame_ids=tuple(item.frame_id for item in supporting),
            model_name=result.model_name,
            event_ready=event_ready,
            reasons=tuple(reasons),
        )

    def clear(self, camera_id: str, track_id: int) -> None:
        self._windows.pop(f"{camera_id}:{track_id}", None)
