"""Consent-aware, local watchlist template store and cosine matcher."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ai.common.image_ops import cosine_similarity, normalize_vector
from ai.contracts import EvidenceState


@dataclass(frozen=True, slots=True)
class WatchlistMatch:
    status: EvidenceState
    person_id: str | None
    display_name: str | None
    similarity: float | None
    second_best_similarity: float | None
    reasons: tuple[str, ...] = ()


class WatchlistStore:
    def __init__(self, path: str | Path, model_name: str) -> None:
        self.path = Path(path)
        self.model_name = model_name
        self.entries: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.entries = []
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        stored_model = payload.get("model_name")
        if stored_model and stored_model != self.model_name:
            raise ValueError(f"Watchlist uses {stored_model}, but backend uses {self.model_name}")
        self.entries = list(payload.get("entries", []))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        dimension = 0
        for entry in self.entries:
            templates = entry.get("templates", [])
            if templates:
                dimension = len(templates[0])
                break
        payload = {
            "version": 1,
            "model_name": self.model_name,
            "embedding_dimension": dimension,
            "privacy_note": "Stores embeddings only. Enrol only with documented consent/authority.",
            "entries": self.entries,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def enroll(
        self,
        person_id: str,
        display_name: str,
        embeddings: list[tuple[float, ...] | np.ndarray],
        consent_reference: str,
    ) -> None:
        if not person_id or not display_name or not consent_reference:
            raise ValueError("person_id, display_name, and consent_reference are required")
        if not embeddings:
            raise ValueError("At least one embedding is required")
        normalized = [normalize_vector(np.asarray(item, dtype=np.float32)).tolist() for item in embeddings]
        dimensions = {len(item) for item in normalized}
        if len(dimensions) != 1:
            raise ValueError("All embeddings must have the same dimension")
        self.entries = [entry for entry in self.entries if entry.get("person_id") != person_id]
        self.entries.append(
            {
                "person_id": person_id,
                "display_name": display_name,
                "consent_reference": consent_reference,
                "templates": normalized,
            }
        )
        self.save()

    def match(
        self,
        embedding: tuple[float, ...] | np.ndarray,
        possible_threshold: float,
        match_threshold: float,
        ambiguity_margin: float,
    ) -> WatchlistMatch:
        if not self.entries:
            return WatchlistMatch(EvidenceState.UNRESOLVED, None, None, None, None, ("watchlist_empty",))
        query = normalize_vector(np.asarray(embedding, dtype=np.float32))
        ranked: list[tuple[float, dict[str, Any]]] = []
        for entry in self.entries:
            templates = entry.get("templates", [])
            if not templates:
                continue
            best = max(cosine_similarity(query, np.asarray(template, dtype=np.float32)) for template in templates)
            ranked.append((float(best), entry))
        if not ranked:
            return WatchlistMatch(EvidenceState.UNRESOLVED, None, None, None, None, ("no_templates",))
        ranked.sort(key=lambda item: item[0], reverse=True)
        score, entry = ranked[0]
        second = ranked[1][0] if len(ranked) > 1 else None
        margin = score - second if second is not None else 1.0
        if score < possible_threshold:
            return WatchlistMatch(EvidenceState.UNRESOLVED, None, None, score, second, ("below_threshold",))
        if margin < ambiguity_margin:
            return WatchlistMatch(EvidenceState.POSSIBLE_MATCH, None, None, score, second, ("ambiguous_top_matches",))
        status = EvidenceState.MATCH_CANDIDATE if score >= match_threshold else EvidenceState.POSSIBLE_MATCH
        return WatchlistMatch(
            status,
            str(entry["person_id"]),
            str(entry["display_name"]),
            score,
            second,
            (),
        )
