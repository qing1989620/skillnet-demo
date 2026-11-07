"""Whitelist-only, unscored annotation exports; annotators cannot be simulated."""

from __future__ import annotations

import re
from typing import Any

from .manifest import digest
from .schemas import DIMENSIONS, SkillSnapshot

HISTORICAL_SECTION = re.compile(
    r"(?im)^##\s+(?:质量评估|quality(?:\s+(?:assessment|ratings?))?|运行统计|stats)\s*\n.*?(?=^##\s|\Z)",
    re.S,
)


def blind_document(document: str) -> str:
    def hide(match: re.Match[str]) -> str:
        return "".join(
            "[Historical assessment section withheld for blinding]" + ("\n" if line.endswith("\n") else "")
            for line in match.group().splitlines(keepends=True)
        )

    text = HISTORICAL_SECTION.sub(hide, document)
    # Imported metadata may contain popularity wrappers. Preserve original line
    # numbers by replacing, rather than deleting, wrapper lines.
    lines = []
    for line in text.splitlines():
        if re.match(r"\s*(?:stars|quality|stats|reward_sum|pulls)\s*:", line, re.I):
            lines.append("[Popularity/historical metadata withheld]")
        else:
            lines.append(line)
    return "\n".join(lines)


def export_labels(
    snapshots: list[SkillSnapshot], ids: list[str], *, labeler_id: str, rubric: str = "quality-rubric-v1"
) -> list[dict[str, Any]]:
    by_uid = {item.skill_uid: item for item in snapshots}
    rows = []
    for uid in ids:
        item = by_uid[uid]
        text = blind_document(item.document)
        rows.append(
            {
                "label_id": digest([labeler_id, uid, rubric]),
                "skill_uid": uid,
                "version_sha256": item.document_sha256,
                "blinded_document": text,
                "blinded_document_sha256": digest(text),
                "line_number_policy": "original_source_line_numbers_preserved; withheld_lines_are_not_evidence",
                "labeler_id": labeler_id,
                "rubric_version": rubric,
                "dimensions": {
                    dim: {"score": None, "status": "unknown", "evidence_refs": [], "reason": "not_annotated"}
                    for dim in DIMENSIONS
                },
                "confirmed_security_risk": "unknown",
                "execution_evidence": "not_tested",
                "remarks": "",
                "blinding_limit": "authored_body_may_reveal_identity; no_algorithm_outputs_included",
            }
        )
    return rows
