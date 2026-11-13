"""Fixed-budget exploratory set reranking on historical SkillNet captures.

Selectors never receive reference labels. Lexical DPP is an adaptation, not a
reproduction of DSR's trained encoder/reranker. No execution uplift is measured.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from research.skill_quality.manifest import canonical, digest, file_sha, freeze_files, read_jsonl, write_once

POLICIES = (
    "original_order",
    "MMR_0.7",
    "DPP_raw",
    "DPP_query_residual_0.5",
    "DPP_query_residual_1.0",
    "query_coverage_0.5",
)


def features(text: str) -> Counter[str]:
    text = text.lower()
    output = Counter(re.findall(r"[a-z0-9]+", text))
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        output.update(run[i : i + 2] for i in range(len(run) - 1))
    for stop in ("the", "and", "of", "to", "a", "需要", "进行", "一个", "我们"):
        output.pop(stop, None)
    return output


def candidate_text(candidate: dict[str, Any]) -> str:
    return " ".join(
        [
            candidate["name"],
            candidate.get("capability", ""),
            *candidate.get("outputs", []),
            *candidate.get("use_when", []),
        ]
    )


def vectors(query: str, candidates: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    counts = [features(query)] + [features(candidate_text(c)) for c in candidates]
    vocabulary = sorted({term for row in counts for term in row})
    indices = {term: i for i, term in enumerate(vocabulary)}
    matrix = np.zeros((len(counts), len(vocabulary)))
    df = Counter(term for row in counts for term in row)
    for i, row in enumerate(counts):
        for term, frequency in row.items():
            matrix[i, indices[term]] = (1 + math.log(frequency)) * (
                1 + math.log((len(counts) + 1) / (df[term] + 1))
            )
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.maximum(norms, 1e-12)
    return matrix[0], matrix[1:]


def dpp_kernel(query: np.ndarray, skills: np.ndarray, quality: np.ndarray, residual: float) -> np.ndarray:
    residual_vectors = skills - np.outer(skills @ query, query)
    blended = residual * residual_vectors + (1 - residual) * skills
    lengths = np.linalg.norm(blended, axis=1)
    # Exact query alignment has zero residual; retain its original vector.
    blended[lengths < 1e-10] = skills[lengths < 1e-10]
    blended /= np.maximum(np.linalg.norm(blended, axis=1, keepdims=True), 1e-12)
    similarity = (1 + blended @ blended.T) / 2
    return np.outer(quality, quality) * similarity + np.eye(len(skills)) * 1e-10


def select(query: str, candidates: list[dict[str, Any]], policy: str, k: int = 5) -> list[str]:
    """No gold/reference argument exists in this selector's interface."""
    if policy not in POLICIES or k < 1:
        raise ValueError("Unsupported policy or k")
    if len({c["name"] for c in candidates}) != len(candidates):
        raise ValueError("Duplicate candidate identities")
    if not candidates:
        return []
    k = min(k, len(candidates))
    if policy == "original_order":
        return [c["name"] for c in candidates[:k]]
    qvec, svec = vectors(query, candidates)
    # Fixed rank-derived relevance; it is not a probability or trust score.
    quality = 1 / np.sqrt(np.arange(1, len(candidates) + 1))
    chosen: list[int] = []
    if policy.startswith("DPP"):
        residual = 0.0 if policy == "DPP_raw" else float(policy.rsplit("_", 1)[1])
        kernel = dpp_kernel(qvec, svec, quality, residual)
        while len(chosen) < k:
            gains = []
            for index in range(len(candidates)):
                if index in chosen:
                    continue
                subset = chosen + [index]
                sign, logdet = np.linalg.slogdet(kernel[np.ix_(subset, subset)])
                gains.append((float(logdet) if sign > 0 else -math.inf, -index, index))
            chosen.append(max(gains)[2])
    elif policy == "MMR_0.7":
        similarity = svec @ svec.T
        while len(chosen) < k:
            chosen.append(
                max(
                    (0.7 * quality[i] - 0.3 * (max(similarity[i, chosen]) if chosen else 0.0), -i, i)
                    for i in range(len(candidates))
                    if i not in chosen
                )[2]
            )
    else:
        covered = np.zeros_like(qvec)
        scale = max(float((svec @ qvec).max()), 1e-12)
        while len(chosen) < k:
            chosen.append(
                max(
                    (0.5 * quality[i] + 0.5 * float(np.maximum(svec[i] - covered, 0) @ qvec) / scale, -i, i)
                    for i in range(len(candidates))
                    if i not in chosen
                )[2]
            )
            covered = np.maximum(covered, svec[chosen[-1]])
    chosen.sort()
    return [candidates[i]["name"] for i in chosen]


def score(selected: list[str], reference: list[str]) -> tuple[float, bool]:
    if not reference:
        raise ValueError("Empty reference")
    wanted = set(reference)
    return len(wanted & set(selected)) / len(wanted), wanted.issubset(selected)


def run(root: Path, source: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError("Run IDs are write-once")
    captures = read_jsonl(source)
    rows, baseline_errors = [], []
    for capture in captures:
        result = capture["result"]
        if digest(result) != capture["result_sha256"]:
            raise ValueError("Frozen retrieval result hash changed")
        candidates = result["candidates"]
        baseline = select(result["query"], candidates, "original_order")
        if baseline != result["selected"]:
            baseline_errors.append(capture["task_id"])
        pool_recall, pool_full = score([c["name"] for c in candidates], capture["gold"])
        for policy in POLICIES:
            picked = select(result["query"], candidates, policy)
            recall, full = score(picked, capture["gold"])
            selected_rows = [c for c in candidates if c["name"] in picked]
            rows.append(
                {
                    "frame": capture["frame"],
                    "dataset": capture["dataset"],
                    "task_id": capture["task_id"],
                    "task_sha256": capture["task_sha256"],
                    "mode": capture["mode"],
                    "policy": policy,
                    "selected": picked,
                    "gold_recall_at_5": recall,
                    "full_gold_set_coverage": full,
                    "pool_reference_recall_ceiling": pool_recall,
                    "pool_full_coverage_ceiling": pool_full,
                    "selected_metadata_utf8_bytes": sum(
                        len(canonical({k: c[k] for k in ("name", "capability", "outputs", "use_when")}))
                        for c in selected_rows
                    ),
                    "reference_names": capture["gold"],
                    "execution_utility": "not_measured",
                    "evaluation_scope": "previously_seen_historical_named_anchor_labels_exploratory",
                }
            )
    if baseline_errors:
        raise ValueError("Baseline selection was not reproduced: " + repr(baseline_errors))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = "/".join(row[k] for k in ("frame", "dataset", "mode", "policy"))
        groups[key].append(row)
    summaries = {}
    for key, group in groups.items():
        base_key = key.rsplit("/", 1)[0] + "/original_order"
        baseline_group = {r["task_id"]: r for r in groups[base_key]}
        differences = [
            r["gold_recall_at_5"] - baseline_group[r["task_id"]]["gold_recall_at_5"] for r in group
        ]
        summaries[key] = {
            "tasks": len(group),
            "recall_at_5": float(np.mean([r["gold_recall_at_5"] for r in group])),
            "full_gold_set_coverage": float(np.mean([r["full_gold_set_coverage"] for r in group])),
            "pool_recall_ceiling": float(np.mean([r["pool_reference_recall_ceiling"] for r in group])),
            "pool_full_coverage_ceiling": float(np.mean([r["pool_full_coverage_ceiling"] for r in group])),
            "recall_delta": float(np.mean(differences)),
            "wins_losses_ties": [
                sum(d > 1e-12 for d in differences),
                sum(d < -1e-12 for d in differences),
                sum(abs(d) <= 1e-12 for d in differences),
            ],
            "mean_selected_metadata_utf8_bytes": float(
                np.mean([r["selected_metadata_utf8_bytes"] for r in group])
            ),
        }
    summary = {
        "experiment": "historical_set_reranking_development_v1",
        "captures": len(captures),
        "policy_task_records": len(rows),
        "unique_historical_tasks": len({r["task_sha256"] for r in rows}),
        "input_sha256": file_sha(source),
        "gold_used_by_selector": False,
        "baseline_reproduced": True,
        "summaries": summaries,
        "api_calls": 0,
        "execution_trials": 0,
        "production_policy_changed": False,
        "limitations": [
            "all 32 tasks previously seen; not independent holdout",
            "lexical proxy and rank-derived relevance, not published DSR reproduction",
            "reference skill names may omit functionally equivalent skills",
            "retrieval full-set coverage is not task success or quality certification",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "predictions.jsonl", rows, jsonl=True)
    write_once(output / "summary.json", summary)
    code = [Path(__file__), Path(__file__).with_name("experiment_plan.json")]
    snapshot = output / "code-snapshot"
    snapshot.mkdir()
    for path in code:
        (snapshot / path.name).write_bytes(path.read_bytes())
    write_once(output / "code-manifest.json", freeze_files(root, code))
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("out/research/skill-quality/20261104-retrieval-v1/retrieval_candidates.jsonl"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(Path.cwd(), args.input, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "summaries"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
