"""A documented precondition gate, deliberately separate from ability success."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .evidence import Citation


@dataclass(frozen=True)
class Clause:
    key: str
    expected: bool | str
    explanation: str
    origin: Literal["source_declared", "reviewer_operationalization"]
    evidence: tuple[Citation, ...]

    def __post_init__(self) -> None:
        if not self.key or type(self.expected) not in (bool, str) or not self.evidence:
            raise ValueError("A boundary clause needs an explicit value and source evidence")
        if not self.explanation.strip():
            raise ValueError("A boundary clause needs an explanation")
        if self.origin not in {"source_declared", "reviewer_operationalization"}:
            raise ValueError("Unknown clause provenance")


@dataclass(frozen=True)
class Contract:
    name: str
    task_families: tuple[str, ...]
    excluded_tasks: tuple[str, ...]
    required: tuple[Clause, ...]
    prohibited: tuple[Clause, ...]
    scope_note: str
    scope_evidence: tuple[Citation, ...]
    scope_origin: Literal["reviewer_operationalization"] = "reviewer_operationalization"
    empirical_scope: Literal["not_tested"] = "not_tested"

    def __post_init__(self) -> None:
        if not self.task_families or set(self.task_families) & set(self.excluded_tasks):
            raise ValueError("Supported and excluded task sets must be disjoint")
        keys = [c.key for c in self.required + self.prohibited]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate contract facts")
        if self.empirical_scope != "not_tested":
            raise ValueError("This preflight cannot issue empirical ability certificates")
        if not self.scope_evidence:
            raise ValueError("Task scope needs source evidence")


def preflight(contract: Contract, task_family: str, facts: dict[str, bool | str | None]) -> dict:
    """Missing facts are unknown; a match is NEVER an execution pass.

    Facts must come from a trusted task/environment adapter or explicit reviewer
    record, not from an untrusted Skill's self-reported safe/compatible label.
    This prototype does not authenticate such an adapter.
    """
    matched, failed, unknown, prohibited = [], [], [], []
    for clause in contract.required + contract.prohibited:
        value = facts.get(clause.key)
        if value is not None and type(value) is not type(clause.expected):
            raise ValueError("Fact type mismatch: " + clause.key)
    for clause in contract.prohibited:
        value = facts.get(clause.key)
        if value is None:
            unknown.append(clause.key)
        elif value == clause.expected:
            prohibited.append(clause.key)
    for clause in contract.required:
        value = facts.get(clause.key)
        if value is None:
            unknown.append(clause.key)
        elif value == clause.expected:
            matched.append(clause.key)
        else:
            failed.append(clause.key)
    if prohibited:
        status = "prohibited_action_in_declared_contract"
    elif task_family in contract.excluded_tasks:
        status = "outside_declared_scope"
    elif task_family not in contract.task_families:
        status = "scope_unknown"
    elif failed:
        status = "preconditions_unmet"
    elif unknown:
        status = "preconditions_unknown"
    else:
        status = "matches_documented_conditions_not_executed"
    return {
        "status": status,
        "matched": matched,
        "failed": failed,
        "unknown": unknown,
        "prohibited": prohibited,
        "execution_verified": False,
        "utility": "not_measured",
        "fact_provenance": "caller_supplied_not_authenticated_by_this_prototype",
    }
