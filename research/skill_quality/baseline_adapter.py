"""Use the original Retriever and benchmark harness, with API calls disabled."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .manifest import canonical, digest, write_once
from .ranker import replay


def retrieval_replay(root: Path, output: Path) -> dict[str, Any]:
    from skillnet import config, llm
    from skillnet.catalog import SkillLibrary, build_seed_skills
    from skillnet.retriever import Retriever

    if config.API_KEY:
        raise ValueError("E00 replay requires an empty production API key")
    output.mkdir(parents=True, exist_ok=False)
    result_rows, summaries = [], {}
    before_calls = llm.LEDGER.calls
    for frame in ("original_benchmark_seed_library", "full_delivery_library"):
        library = SkillLibrary(build_seed_skills()) if frame.startswith("original_") else SkillLibrary.load()
        retriever = Retriever(library).build()
        encoder = getattr(retriever.vec, "status", {})
        # auto fallback must never be relabelled as the delivered E5 baseline.
        if encoder.get("kind") != "dense-onnx":
            raise ValueError("Delivered dense encoder unavailable; record a separate lexical cohort instead")
        for dataset in ("benchmark", "heldout"):
            task_file = root / "tasks" / (dataset + ".json")
            tasks = json.loads(task_file.read_text(encoding="utf-8"))["tasks"]
            for mode in ("bm25", "hybrid", "fabric"):
                scores = []
                for task in tasks:
                    first = retriever.search(task["query"], mode=mode, k=5, pool=20).to_dict()
                    repeated = retriever.search(task["query"], mode=mode, k=5, pool=20).to_dict()
                    if canonical(first) != canonical(repeated):
                        raise ValueError("Baseline replay is not deterministic")
                    if canonical(first) != canonical(replay(first, enable_shadow=False)):
                        raise ValueError("Shadow-disabled replay changed baseline")
                    gold = set(task["gold"])
                    if not gold:
                        raise ValueError("Missing historical gold")
                    recall = len(gold.intersection(first["selected"])) / len(gold)
                    full = gold.issubset(first["selected"])
                    scores.append((recall, full))
                    result_rows.append(
                        {
                            "frame": frame,
                            "dataset": dataset,
                            "task_id": task["id"],
                            "task_sha256": digest(task),
                            "dataset_sha256": digest(tasks),
                            "mode": mode,
                            "library_size": len(library),
                            "k": 5,
                            "pool": 20,
                            "result": first,
                            "result_sha256": digest(first),
                            "repeated_equal": True,
                            "gold": sorted(gold),
                            "recall_at_5": recall,
                            "full_coverage": full,
                            "historical_dataset_only": True,
                            "causal_utility": "not_measured",
                        }
                    )
                summaries[f"{frame}/{dataset}/{mode}"] = {
                    "tasks": len(tasks),
                    "library_size": len(library),
                    "encoder": encoder,
                    "recall_at_5": sum(r for r, _ in scores) / len(scores),
                    "full_coverage": sum(f for _, f in scores) / len(scores),
                    "fabric_status": "graph_expansion_only_llm_not_run"
                    if mode == "fabric"
                    else "not_applicable",
                }
    if llm.LEDGER.calls != before_calls:
        raise ValueError("Unexpected paid call in baseline replay")
    write_once(output / "retrieval_candidates.jsonl", result_rows, jsonl=True)
    write_once(output / "retrieval_summary.json", summaries)
    return summaries
