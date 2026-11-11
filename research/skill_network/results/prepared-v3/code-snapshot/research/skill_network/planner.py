"""Budgeted compatible paths. No gold artifacts or execution functions imported."""

from __future__ import annotations

import math

from research.skill_study.routing_pilot import select, vectors
from skillnet.frontier import plan as native_plan

from .contracts import allowed_caps, context_group, contract

POLICIES = [
    "lexical_top5",
    "mmr_top5",
    "dpp_top5",
    "metadata_shortest_path",
    "fixed_workflow",
    "global_filter_path",
    "global_risk_path",
    "conditional_evidence_path",
    "conditional_top5",
    "evidence_without_version",
]


def eligible(nodes: list[dict], request: dict) -> list[dict]:
    caps = allowed_caps(request["intent"]["mask"])
    return [n for n in nodes if n["capability"] in caps]


def evidence(
    node: dict, request: dict, records: list[dict], conditional: bool, ignore_version: bool = False
) -> tuple[int, int]:
    group = context_group(node, request, conditional)
    rows = [
        r
        for r in records
        if ((r["node_id"] == node["id"]) if ignore_version else (r["source_sha256"] == node["source_sha256"]))
        and (not conditional or r["group"] == group)
    ]
    return sum(r["passed"] for r in rows), len(rows)


def enumerate_paths(nodes: list[dict], request: dict, budget: int) -> list[tuple[list[str], int]]:
    output = []
    mask = request["intent"]["mask"]

    def visit(facts: set[str], path: list[str], cost: int):
        if "metrics" in facts:
            output.append((path, cost))
            return
        if len(path) >= 5:
            return
        for node in nodes:
            required, adds = contract(node["capability"], mask)
            if not required <= facts or adds <= facts or cost + node["context_bytes"] > budget:
                continue
            visit(facts | adds, path + [node["id"]], cost + node["context_bytes"])

    visit({"raw"}, [], 0)
    return output


def metadata_path(nodes: list[dict], request: dict) -> dict:
    actions = []
    for node in nodes:
        required, adds = contract(node["capability"], request["intent"]["mask"])
        actions.append(
            {
                "id": node["id"],
                "requires": sorted(required),
                "adds": sorted(adds),
                "deletes": [],
                "cost": node["context_bytes"],
            }
        )
    return native_plan(["raw"], ["metrics"], actions, max_depth=5, max_states=4096)


def choose(
    nodes: list[dict],
    request: dict,
    records: list[dict],
    budget: int,
    policy: str,
    fixed_ids: dict[str, str] | None = None,
) -> dict:
    if policy not in POLICIES:
        raise ValueError("unknown policy")
    assert set(request) == {"task_id", "intent", "profile", "query"}
    assert set(request["profile"]) == {"quoted", "boundary"}
    assert all(set(n) == {"id", "capability", "text", "source_sha256", "context_bytes"} for n in nodes)
    pool = eligible(nodes, request)
    conditional = policy in {"conditional_evidence_path", "conditional_top5", "evidence_without_version"}
    cache = {}

    def lookup(node):
        key = node["id"]
        if key not in cache:
            cache[key] = evidence(node, request, records, conditional, policy == "evidence_without_version")
        return cache[key]

    if policy == "fixed_workflow":
        if fixed_ids is None:
            raise ValueError("manual fixed workflow needs its predefined configuration")
        caps = (
            ["parse"]
            + [c for bit, c in [(1, "dedup"), (2, "exclude"), (4, "drop")] if request["intent"]["mask"] & bit]
            + ["metrics"]
        )
        if not set(caps) <= set(fixed_ids):
            return {"plan": [], "bytes": 0, "reason": "fixed_node_unavailable"}
        path = [fixed_ids[c] for c in caps]
        available = {n["id"]: n for n in pool}
        if not set(path) <= set(available):
            return {"plan": [], "bytes": 0, "reason": "fixed_node_unavailable"}
        cost = sum(available[p]["context_bytes"] for p in path)
        return {
            "plan": path if cost <= budget else [],
            "bytes": cost if cost <= budget else 0,
            "reason": "fixed_workflow",
        }
    if policy in {"lexical_top5", "mmr_top5", "dpp_top5", "conditional_top5"}:
        candidates = [
            {"name": n["id"], "capability": n["text"], "outputs": [n["capability"]], "use_when": []}
            for n in pool
        ]
        if candidates:
            q, s = vectors(request["query"], candidates)
            relevance = s @ q
            ranked = sorted(range(len(pool)), key=lambda i: (-float(relevance[i]), pool[i]["id"]))
            pool = [pool[i] for i in ranked]
            candidates = [candidates[i] for i in ranked]
        if policy == "conditional_top5":

            def key(node):
                passed, n = lookup(node)
                return (-(passed + 1) / (n + 2), node["context_bytes"], node["id"])

            pool = sorted(pool, key=key)[:5]
        else:
            which = {"lexical_top5": "original_order", "mmr_top5": "MMR_0.7", "dpp_top5": "DPP_raw"}[policy]
            picked = set(select(request["query"], candidates, which, k=5))
            pool = [n for n in pool if n["id"] in picked]
    if policy in {"metadata_shortest_path", "lexical_top5", "mmr_top5", "dpp_top5", "conditional_top5"}:
        result = metadata_path(pool, request)
        found = result["status"] == "plan_found" and result["cost"] <= budget
        return {
            "plan": result["plan"] if found else [],
            "bytes": int(result["cost"]) if found else 0,
            "reason": result["status"] if found else "no_budget_feasible_path",
        }
    # A failed development probe is a conservative selection veto for its
    # observed context group, not a general future-task incapability label.
    usable = [n for n in pool if (lambda a: a[0] == a[1])(lookup(n))]
    paths = enumerate_paths(usable, request, budget)
    if not paths:
        return {"plan": [], "bytes": 0, "reason": "no_evidence_compatible_path"}
    by_id = {n["id"]: n for n in usable}

    def objective(row):
        path, cost = row
        if policy == "global_filter_path":
            return (cost, len(path), path)
        risk = 0.0
        for identifier in path:
            passed, n = lookup(by_id[identifier])
            risk -= math.log((passed + 1) / (n + 2))
        return (risk + 0.05 * cost / budget + 0.02 * len(path), cost, path)

    path, cost = min(paths, key=objective)
    return {"plan": path, "bytes": cost, "reason": "evidence_conditioned_feasible_path"}
