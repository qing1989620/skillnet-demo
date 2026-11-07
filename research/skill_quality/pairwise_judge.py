"""Normalize AB/BA advisory judgments without treating majority votes as gold."""

from __future__ import annotations

from typing import Literal


def normalize_preference(left_uid: str, right_uid: str, verdict: Literal["A", "B", "tie", "unknown"]) -> str:
    if left_uid == right_uid:
        raise ValueError("Pair requires different Skill versions")
    if verdict not in ("A", "B", "tie", "unknown"):
        raise ValueError("Invalid pairwise verdict")
    return left_uid if verdict == "A" else right_uid if verdict == "B" else verdict


def swap_consistent(left_uid: str, right_uid: str, ab: str, ba: str) -> bool | None:
    first = normalize_preference(left_uid, right_uid, ab)  # type: ignore[arg-type]
    second = normalize_preference(right_uid, left_uid, ba)  # type: ignore[arg-type]
    return None if "unknown" in (first, second) else first == second
