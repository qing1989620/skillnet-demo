"""Conservative static signals. A flag is a review lead, never a safety gold label."""

from __future__ import annotations

import re
from typing import Any

from .schemas import SkillSnapshot

RULES = {
    "instruction_override": r"ignore\s+(?:all\s+)?(?:previous|prior|the)\s+(?:instructions|rubric)|忽略.{0,8}(?:规则|指令|评分标准)",
    "rating_manipulation": r"(?:give|assign|set).{0,30}(?:full\s+marks|maximum\s+score)|(?:安全|评分).{0,10}(?:满分|最高分)",
    "remote_shell_pattern": r"(?:curl|wget)[^\n]{0,200}\|\s*(?:bash|sh|powershell)",
    "destructive_command_mention": r"rm\s+-rf\b|drop\s+(?:table|database)\b",
    "credential_path_mention": r"\.ssh/|\.aws/credentials|/etc/shadow",
}


def audit(snapshot: SkillSnapshot) -> dict[str, Any]:
    flags = []
    for number, line in enumerate(snapshot.document.splitlines(), 1):
        for rule, pattern in RULES.items():
            if re.search(pattern, line, re.I):
                flags.append(
                    {
                        "rule": rule,
                        "start_line": number,
                        "end_line": number,
                        "source_sha256": snapshot.document_sha256,
                        "interpretation": "suspicious_text_requires_context_review",
                    }
                )
    scripts = [
        r.path
        for r in snapshot.resources
        if r.path.startswith("scripts/") or r.path.lower().endswith((".py", ".sh", ".ps1", ".js"))
    ]
    return {
        "skill_uid": snapshot.skill_uid,
        "source_sha256": snapshot.document_sha256,
        "method": "static-signals-v1",
        "findings": flags,
        "script_resources": scripts,
        "license_declared": snapshot.declared_license,
        "license_review": "not_reviewed",
        "security_gate": "human_review",
        "security_status": "not_verified",
        "reason_codes": (["suspicious_text"] if flags else ["absence_of_flags_is_not_safety"])
        + (["unreviewed_scripts"] if scripts else [])
        + ["license_review_required"],
        "execution_permitted": False,
        "utility_status": "not_estimated",
    }
