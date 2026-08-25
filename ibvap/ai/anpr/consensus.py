"""Weighted multi-frame and cross-camera plate consensus with provenance."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

from ai.common.config import ANPRConfig
from ai.contracts import CharacterProvenance, EvidenceState, PlateFrameResult, PlateTrackResult, QualityState


def edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, 1):
        current = [left_index]
        for right_index, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def text_similarity(left: str, right: str) -> float:
    return 1.0 - edit_distance(left, right) / max(len(left), len(right), 1)


def align_to_reference(reference: str, value: str) -> list[str | None]:
    """Map OCR characters to reference positions using edit-distance traceback."""
    rows, columns = len(reference) + 1, len(value) + 1
    costs = [[0] * columns for _ in range(rows)]
    moves = [[""] * columns for _ in range(rows)]
    for index in range(1, rows):
        costs[index][0], moves[index][0] = index, "delete"
    for index in range(1, columns):
        costs[0][index], moves[0][index] = index, "insert"
    for row in range(1, rows):
        for column in range(1, columns):
            choices = [
                (costs[row - 1][column - 1] + (reference[row - 1] != value[column - 1]), "match"),
                (costs[row - 1][column] + 1, "delete"),
                (costs[row][column - 1] + 1, "insert"),
            ]
            costs[row][column], moves[row][column] = min(choices, key=lambda item: item[0])
    aligned: list[str | None] = [None] * len(reference)
    row, column = len(reference), len(value)
    while row or column:
        move = moves[row][column]
        if move == "match":
            aligned[row - 1] = value[column - 1]
            row, column = row - 1, column - 1
        elif move == "delete":
            row -= 1
        else:
            column -= 1
    return aligned


class PlateConsensus:
    def __init__(self, config: ANPRConfig) -> None:
        self.config = config
        self._groups: dict[str, deque[PlateFrameResult]] = defaultdict(
            lambda: deque(maxlen=config.consensus_window)
        )
        self._track_keys: dict[str, set[str]] = defaultdict(set)
        self._last_emitted: dict[tuple[str, str], datetime] = {}

    @staticmethod
    def _weight(item: PlateFrameResult) -> float:
        return max(0.05, item.quality.score) * max(0.05, item.detector_confidence) * max(0.05, item.ocr_confidence)

    def add(self, result: PlateFrameResult, group_id: str | None = None) -> PlateTrackResult:
        track_key = f"{result.camera_id}:{result.track_id}"
        key = group_id or track_key
        window = self._groups[key]
        window.append(result)
        self._track_keys[key].add(track_key)
        usable = [
            item
            for item in window
            if item.quality.state != QualityState.UNUSABLE and item.normalized_text
        ]
        if not usable:
            return self._empty_result(key, result, len(window))

        reference_item = max(
            usable,
            key=lambda candidate: sum(
                self._weight(other) * text_similarity(candidate.normalized_text or "", other.normalized_text or "")
                for other in usable
            ),
        )
        reference = reference_item.normalized_text or ""
        alignments = [(item, align_to_reference(reference, item.normalized_text or ""), self._weight(item)) for item in usable]
        output: list[str] = []
        provenance: list[CharacterProvenance] = []
        agreements: list[float] = []
        for index in range(len(reference)):
            votes: dict[str, float] = defaultdict(float)
            contributors: dict[str, list[PlateFrameResult]] = defaultdict(list)
            total_weight = 0.0
            for item, aligned, weight in alignments:
                character = aligned[index]
                if character is None:
                    continue
                char_weight = weight
                if index < len(item.character_confidences):
                    char_weight *= max(0.05, item.character_confidences[index])
                votes[character] += char_weight
                contributors[character].append(item)
                total_weight += char_weight
            winner, support_weight = max(votes.items(), key=lambda item: item[1])
            agreement = support_weight / total_weight if total_weight else 0.0
            agreements.append(agreement)
            rendered = winner if agreement >= self.config.min_character_agreement else "*"
            output.append(rendered)
            sources = contributors[winner]
            provenance.append(
                CharacterProvenance(
                    index=index,
                    character=rendered,
                    support_weight=support_weight,
                    total_weight=total_weight,
                    cameras=tuple(sorted({item.camera_id for item in sources})),
                    frame_ids=tuple(sorted({item.frame_id for item in sources})),
                )
            )

        final_text = "".join(output)
        overall_agreement = sum(agreements) / len(agreements) if agreements else 0.0
        complete = "*" not in final_text
        enough_frames = len(usable) >= self.config.min_supporting_frames
        verified = complete and enough_frames and overall_agreement >= self.config.min_verified_agreement
        status = EvidenceState.VERIFIED if verified else EvidenceState.PARTIAL if final_text else EvidenceState.UNRESOLVED
        event_ready = False
        if verified:
            emitted_key = (key, final_text)
            last = self._last_emitted.get(emitted_key)
            if last is None or (result.timestamp - last).total_seconds() >= self.config.event_cooldown_seconds:
                event_ready = True
                self._last_emitted[emitted_key] = result.timestamp
        reasons: list[str] = []
        if not enough_frames:
            reasons.append("insufficient_usable_frames")
        if not complete:
            reasons.append("unresolved_characters")
        if overall_agreement < self.config.min_verified_agreement:
            reasons.append("low_consensus_agreement")
        return PlateTrackResult(
            track_keys=tuple(sorted(self._track_keys[key])),
            status=status,
            final_text=final_text,
            raw_candidates=tuple(item.raw_text or "" for item in usable),
            supporting_frames=len(usable),
            usable_frames=len(usable),
            total_frames=len(window),
            agreement=overall_agreement,
            provenance=tuple(provenance),
            source_cameras=tuple(sorted({item.camera_id for item in usable})),
            source_frame_ids=tuple(sorted({item.frame_id for item in usable})),
            model_name=result.model_name,
            event_ready=event_ready,
            reasons=tuple(reasons),
        )

    def _empty_result(self, key: str, result: PlateFrameResult, total_frames: int) -> PlateTrackResult:
        return PlateTrackResult(
            track_keys=tuple(sorted(self._track_keys[key])),
            status=EvidenceState.UNRESOLVED,
            final_text=None,
            raw_candidates=(),
            supporting_frames=0,
            usable_frames=0,
            total_frames=total_frames,
            agreement=0.0,
            provenance=(),
            source_cameras=(),
            source_frame_ids=(),
            model_name=result.model_name,
            event_ready=False,
            reasons=("no_usable_ocr_evidence",),
        )

    def clear(self, group_id: str) -> None:
        self._groups.pop(group_id, None)
        self._track_keys.pop(group_id, None)
