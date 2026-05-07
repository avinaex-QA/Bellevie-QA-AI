"""
Deduplication logic for generated test cases.
Uses title similarity + step overlap to detect near-duplicates.
"""
from difflib import SequenceMatcher
from typing import List
from backend.models.schemas import TestCase


def _similarity(a: str, b: str) -> float:
    """Returns string similarity ratio between 0.0 and 1.0."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _steps_overlap(steps_a: List[str], steps_b: List[str]) -> float:
    """Returns how much the step lists overlap (jaccard-like)."""
    if not steps_a or not steps_b:
        return 0.0
    joined_a = " ".join(steps_a).lower()
    joined_b = " ".join(steps_b).lower()
    return _similarity(joined_a, joined_b)


def deduplicate(test_cases: List[TestCase], threshold: float = 0.82) -> List[TestCase]:
    """
    Removes test cases whose title + steps are too similar to an existing one.
    threshold: similarity score above which a test is considered a duplicate.
    """
    unique: List[TestCase] = []

    for candidate in test_cases:
        is_duplicate = False
        for existing in unique:
            title_sim = _similarity(candidate.title, existing.title)
            steps_sim = _steps_overlap(candidate.steps, existing.steps)
            # Weighted score: title matters more than steps
            combined = title_sim * 0.7 + steps_sim * 0.3
            if combined >= threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            unique.append(candidate)

    return unique


def renumber_ids(test_cases: List[TestCase]) -> List[TestCase]:
    """Re-assigns sequential IDs after deduplication (TC-001, TC-002, ...)."""
    for idx, tc in enumerate(test_cases, start=1):
        tc.id = f"TC-{idx:03d}"
    return test_cases
