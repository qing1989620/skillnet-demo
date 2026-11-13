"""Selector-visible capability and context contracts; no implementation import."""

from __future__ import annotations

CAPS = {"p": "parse", "d": "dedup", "x": "exclude", "m": "drop", "t": "metrics", "b": "bundle"}
TEXT = {
    "parse": "parse read CSV records with schema header",
    "dedup": "deduplicate sample id keep first records",
    "exclude": "exclude all cross split subject records",
    "drop": "drop exactly missing empty score records",
    "metrics": "compute binary metrics accuracy precision recall f1",
    "bundle": "deduplicate sample id exclude cross split subjects drop missing score",
}


def allowed_caps(mask: int) -> set[str]:
    return (
        {"parse", "metrics"}
        | ({"dedup"} if mask & 1 else set())
        | ({"exclude"} if mask & 2 else set())
        | ({"drop"} if mask & 4 else set())
        | ({"bundle"} if mask == 7 else set())
    )


def contract(cap: str, mask: int) -> tuple[set[str], set[str]]:
    if cap == "parse":
        return {"raw"}, {"parsed"}
    if cap == "bundle":
        return {"parsed"}, {"dedup", "exclude", "drop"}
    required = {"parsed"}
    if cap in {"exclude", "drop", "metrics"} and mask & 1:
        required.add("dedup")
    if cap in {"drop", "metrics"} and mask & 2:
        required.add("exclude")
    if cap == "metrics" and mask & 4:
        required.add("drop")
    return required, {cap}


def context_group(node: dict, request: dict, conditional: bool) -> str:
    if not conditional:
        return "all"
    if node["capability"] == "parse":
        return "quoted=" + str(int(request["profile"]["quoted"]))
    if node["capability"] == "metrics":
        return "boundary=" + str(int(request["profile"]["boundary"]))
    return "all"
