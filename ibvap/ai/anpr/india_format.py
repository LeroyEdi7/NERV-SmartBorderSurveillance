"""Non-destructive normalization and soft Indian plate-format scoring.

Grammar is evidence metadata only: it can suggest a correction but never replaces
the OCR/multi-frame result silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


INDIA_STANDARD = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
BHARAT_SERIES = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
_TO_DIGIT = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "G": "6", "B": "8"}
_TO_LETTER = {"0": "O", "1": "I", "2": "Z", "5": "S", "6": "G", "8": "B"}


@dataclass(frozen=True, slots=True)
class PlateGrammar:
    normalized: str
    score: float
    suggestion: str | None
    format_name: str | None


def normalize_plate(text: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def _coerce_positions(value: str, letter_positions: set[int], digit_positions: set[int]) -> str:
    output: list[str] = []
    for index, character in enumerate(value):
        if index in letter_positions:
            output.append(_TO_LETTER.get(character, character))
        elif index in digit_positions:
            output.append(_TO_DIGIT.get(character, character))
        else:
            output.append(character)
    return "".join(output)


def assess_indian_format(text: str | None) -> PlateGrammar:
    value = normalize_plate(text)
    if not value:
        return PlateGrammar("", 0.0, None, None)
    if INDIA_STANDARD.fullmatch(value):
        return PlateGrammar(value, 1.0, None, "INDIA_STANDARD")
    if BHARAT_SERIES.fullmatch(value):
        return PlateGrammar(value, 1.0, None, "BHARAT_SERIES")

    suggestions: list[tuple[float, str, str]] = []
    # Try all plausible district/series segmentations while preserving length.
    for district_len in (1, 2):
        for series_len in (1, 2, 3):
            expected = 2 + district_len + series_len + 4
            if len(value) != expected:
                continue
            letters = set(range(0, 2)) | set(range(2 + district_len, 2 + district_len + series_len))
            digits = set(range(2, 2 + district_len)) | set(range(expected - 4, expected))
            candidate = _coerce_positions(value, letters, digits)
            if INDIA_STANDARD.fullmatch(candidate):
                changed = sum(left != right for left, right in zip(value, candidate))
                suggestions.append((max(0.55, 0.94 - 0.12 * changed), candidate, "INDIA_STANDARD"))

    if len(value) in (9, 10):
        letters = {2, 3} | set(range(8, len(value)))
        digits = set(range(0, 2)) | set(range(4, 8))
        candidate = _coerce_positions(value, letters, digits)
        if BHARAT_SERIES.fullmatch(candidate):
            changed = sum(left != right for left, right in zip(value, candidate))
            suggestions.append((max(0.55, 0.94 - 0.12 * changed), candidate, "BHARAT_SERIES"))

    if suggestions:
        score, candidate, format_name = max(suggestions, key=lambda item: item[0])
        return PlateGrammar(value, score, candidate if candidate != value else None, format_name)
    length_score = max(0.0, 1.0 - abs(len(value) - 10) * 0.12)
    alphanumeric_score = sum(character.isalnum() for character in value) / len(value)
    return PlateGrammar(value, round(0.45 * length_score + 0.25 * alphanumeric_score, 3), None, None)
