"""GPU forward-only relevance probe over already frozen retrieval metadata."""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from research.skill_quality.manifest import digest, file_sha, freeze_files, read_jsonl, write_once

from .routing_pilot import candidate_text, dpp_kernel, score, vectors


def pair_key(query: str, candidate: dict[str, Any]) -> str:
    return digest([query, candidate_text(candidate)])


def select_scored(
    query: str, candidates: list[dict[str, Any]], logits: list[float], residual: float | None
) -> list[str]:
    if len(logits) != len(candidates) or not np.isfinite(logits).all():
        raise ValueError("Incomplete or nonfinite model scores")
    if not candidates:
        return []
    order = sorted(range(len(candidates)), key=lambda i: (-logits[i], i))
    if residual is None:
        return [candidates[i]["name"] for i in order[:5]]
    query_vector, skill_vectors = vectors(query, candidates)
    quality = 1 / (1 + np.exp(-np.clip(np.array(logits), -50, 50)))
    quality /= max(float(quality.max()), 1e-30)
    kernel = dpp_kernel(query_vector, skill_vectors, quality, residual)
    chosen: list[int] = []
    while len(chosen) < min(5, len(candidates)):
        gains = []
        for i in range(len(candidates)):
            if i in chosen:
                continue
            indices = chosen + [i]
            sign, logdet = np.linalg.slogdet(kernel[np.ix_(indices, indices)])
            gains.append((float(logdet) if sign > 0 else -math.inf, -order.index(i), i))
        chosen.append(max(gains)[2])
    chosen.sort(key=lambda i: (-logits[i], i))
    return [candidates[i]["name"] for i in chosen]


def run(model_path: Path, source: Path, output: Path) -> dict:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if output.exists():
        raise FileExistsError("Use a new model-probe run ID")
    plan_path = Path(__file__).with_name("local_model_probe_plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if file_sha(source) != plan["input_sha256"]:
        raise ValueError("Capture input changed")
    if not torch.cuda.is_available():
        raise RuntimeError("Required CUDA GPU unavailable; no silent fallback")
    captures = read_jsonl(source)
    pairs = {}
    for capture in captures:
        result = capture["result"]
        if digest(result) != capture["result_sha256"]:
            raise ValueError("Capture identity mismatch")
        for candidate in result["candidates"]:
            key = pair_key(result["query"], candidate)
            pairs[key] = (result["query"], candidate_text(candidate))
    if len(pairs) > plan["max_unique_query_candidate_pairs"]:
        raise ValueError("Pair budget exceeded")
    download_manifest = json.loads((model_path / "download-manifest.json").read_text(encoding="utf-8"))
    if (
        download_manifest["model_id"] != plan["model_id"]
        or download_manifest["revision"] != plan["model_revision"]
        or file_sha(model_path / "model.safetensors") != plan["weights_sha256"]
    ):
        raise ValueError("Model identity mismatch")
    for item in download_manifest["files"]:
        if file_sha(model_path / item["path"]) != item["sha256"]:
            raise ValueError("Model resource changed")
    output.mkdir(parents=True, exist_ok=False)
    torch.manual_seed(20261106)
    torch.cuda.set_per_process_memory_fraction(plan["gpu_memory_fraction"])
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
    model = (
        AutoModelForCausalLM.from_pretrained(
            str(model_path),
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            torch_dtype=torch.float16,
            attn_implementation="sdpa",
        )
        .to("cuda")
        .eval()
    )
    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    yes, no = tokenizer.convert_tokens_to_ids("yes"), tokenizer.convert_tokens_to_ids("no")
    if yes == no or tokenizer.unk_token_id in (yes, no):
        raise ValueError("Expected distinct yes/no score tokens")
    prefix = "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Answer only yes or no.<|im_end|>\n<|im_start|>user\n"
    suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
    suffix_ids = tokenizer.encode(suffix, add_special_tokens=False)
    maximum = plan["max_length_tokens"] - len(prefix_ids) - len(suffix_ids)
    start = time.monotonic()
    scores, truncated, input_tokens = {}, 0, 0
    ordered = sorted(pairs)
    with (output / "pair-scores.jsonl").open("x", encoding="utf-8") as stream:
        for offset in range(0, len(ordered), plan["batch_size"]):
            if time.monotonic() - start > plan["max_inference_wall_seconds"]:
                break
            keys = ordered[offset : offset + plan["batch_size"]]
            batch = []
            for key in keys:
                query, document = pairs[key]
                prompt = f"<Instruct>: Rank the applicability of this skill to the requested task.\n<Query>: {query}\n<Document>: {document}"
                raw = tokenizer.encode(prompt, add_special_tokens=False)
                truncated += len(raw) > maximum
                ids = prefix_ids + raw[:maximum] + suffix_ids
                input_tokens += len(ids)
                batch.append(ids)
            padded = tokenizer.pad({"input_ids": batch}, padding=True, return_tensors="pt").to("cuda")
            with torch.inference_mode():
                logits = model(**padded, logits_to_keep=1, use_cache=False).logits[:, -1, :]
                values = (logits[:, yes] - logits[:, no]).float().cpu().tolist()
            for key, value in zip(keys, values, strict=True):
                if not math.isfinite(value):
                    raise ValueError("Nonfinite forward score")
                scores[key] = value
                stream.write(json.dumps({"pair_key": key, "yes_minus_no": value}) + "\n")
            stream.flush()
            if offset % 100 == 0:
                print(
                    json.dumps(
                        {
                            "pairs_scored": len(scores),
                            "pairs_total": len(pairs),
                            "inference_seconds": round(time.monotonic() - start, 2),
                        }
                    ),
                    flush=True,
                )
    rows = []
    complete = len(scores) == len(pairs)
    if complete:
        for capture in captures:
            result = capture["result"]
            candidates = result["candidates"]
            values = [scores[pair_key(result["query"], candidate)] for candidate in candidates]
            policies = {
                "original_capture_order": result["selected"],
                "local_pointwise": select_scored(result["query"], candidates, values, None),
                "local_DPP_raw": select_scored(result["query"], candidates, values, 0.0),
                "local_DPP_residual_0.5": select_scored(result["query"], candidates, values, 0.5),
                "local_DPP_residual_1.0": select_scored(result["query"], candidates, values, 1.0),
            }
            for policy, selected in policies.items():
                recall, full = score(selected, capture["gold"])
                rows.append(
                    {
                        "frame": capture["frame"],
                        "dataset": capture["dataset"],
                        "mode": capture["mode"],
                        "task_id": capture["task_id"],
                        "task_sha256": capture["task_sha256"],
                        "policy": policy,
                        "selected": selected,
                        "recall_at_5": recall,
                        "full_coverage": full,
                    }
                )
    groups = defaultdict(list)
    for row in rows:
        groups["/".join(row[k] for k in ("frame", "dataset", "mode", "policy"))].append(row)
    summary = {
        "experiment": plan["id"],
        "plan_sha256": file_sha(plan_path),
        "complete": complete,
        "unique_pairs": len(pairs),
        "scored_pairs": len(scores),
        "truncated_pairs": truncated,
        "input_tokens_before_padding": input_tokens,
        "forward_calls": math.ceil(len(scores) / plan["batch_size"]),
        "inference_wall_seconds": time.monotonic() - start,
        "peak_gpu_allocated_bytes": torch.cuda.max_memory_allocated(),
        "torch": torch.__version__,
        "gpu": torch.cuda.get_device_name(),
        "policies_task_records": len(rows),
        "paid_api_calls": 0,
        "skill_execution_trials": 0,
        "new_d2_quality_bodies_read": False,
        "model_revision": plan["model_revision"],
        "weights_sha256": plan["weights_sha256"],
        "download_manifest_sha256": file_sha(model_path / "download-manifest.json"),
        "summary_by_cohort": {
            k: {
                "tasks": len(v),
                "recall_at_5": float(np.mean([r["recall_at_5"] for r in v])),
                "full_coverage": float(np.mean([r["full_coverage"] for r in v])),
            }
            for k, v in groups.items()
        },
        "limitations": [
            "historical previously seen tasks",
            "metadata-only adapted prompt, not original paper reproduction",
            "Chinese inputs differ from model card English setting",
            "relevance is not trust or execution success",
        ],
    }
    write_once(output / "predictions.jsonl", rows, jsonl=True)
    write_once(output / "summary.json", summary)
    code_paths = [Path(__file__), plan_path, Path(__file__).with_name("routing_pilot.py")]
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), code_paths))
    write_once(output / "manifest.json", freeze_files(output, output.iterdir()))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("out/research/skill-quality/20261104-retrieval-v1/retrieval_candidates.jsonl"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.model_path, args.input, args.output)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "summary_by_cohort"}, ensure_ascii=False, indent=2
        )
    )
