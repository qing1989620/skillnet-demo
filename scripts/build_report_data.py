#!/usr/bin/env python
"""从 out/*.json + config/experiment.yaml 派生全部对外数字。

## 为什么要这个脚本

v0.2 的数字是手抄的，结果出现多处漂移（权重 0.70 vs 0.55、bare 8.221 vs 8.32、
PDF 21 页 vs 22 页）。手工同步在多人协作下必然失效。

从 v0.3 起规则是：**任何对外呈现的数字都必须来自本脚本的产物**。
README、Dashboard、报告表格全部读 `out/manifest.json`，不再各自硬编码。

用法：
    python scripts/build_report_data.py            # 生成 manifest
    python scripts/build_report_data.py --check    # 校验现有 manifest 是否过期
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIG = ROOT / "config" / "experiment.yaml"
OUT = ROOT / "out"
MANIFEST = OUT / "manifest.json"


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _git_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _load_yaml() -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise SystemExit("需要 PyYAML：pip install PyYAML")
    if not CONFIG.exists():
        raise SystemExit(f"缺少配置文件 {CONFIG}")
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ======================================================================
# 各组实验的 KPI 提取
# ======================================================================
def _exp1(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    s = data.get("summary") or {}
    modes = ["bm25", "hybrid", "fabric"]
    return {
        "n_tasks": data.get("n_tasks"),
        "k": data.get("k"),
        "dataset": data.get("dataset", "dev-v1"),
        "rows": [
            {
                "mode": m,
                "label": {"bm25": "BM25 关键词", "hybrid": "混合检索",
                          "fabric": "Fabric 完整方案"}[m],
                "recall": round(float(s[m]["skill_recall"]) * 100, 1),
                "full_coverage": round(float(s[m]["full_coverage_rate"]) * 100, 1),
                "orchestration": round(float(s[m]["orchestration_completeness"]) * 100, 1),
            }
            for m in modes if m in s
        ],
    }


def _exp2(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    s = data.get("summary") or {}
    order = ["bare", "cards", "hybrid", "fabric"]
    labels = {"bare": "无技能", "cards": "仅技能卡（L1 元数据）",
              "hybrid": "混合检索 + 技能全文", "fabric": "完整方案（扩展+重排+全文）"}
    rows = []
    for m in order:
        if m not in s:
            continue
        d = s[m]
        rows.append({
            "mode": m,
            "label": labels[m],
            "score": round(float(d["avg_score"]), 2),
            "coverage": round(float(d["avg_coverage"]) * 100, 1),
            "adoption": (round(float(d["avg_adoption"]) * 100, 1)
                         if d.get("avg_adoption") is not None else None),
            "gain_pct": d.get("gain_pct"),
            "cost": round(float(d["avg_cost_yuan"]), 4),
        })
    base = s.get("bare", {}).get("avg_score")
    top = s.get("fabric", {}).get("avg_score")
    paired = (data.get("paired_vs_bare") or {}).get("fabric") or {}
    return {
        "n_tasks": data.get("n_tasks"),
        "repeats": data.get("repeats"),
        "dataset": data.get("dataset", "dev-v1"),
        "rows": rows,
        "base_score": round(float(base), 2) if base is not None else None,
        "top_score": round(float(top), 2) if top is not None else None,
        "coverage_gain_pp": (
            round(rows[-1]["coverage"] - rows[0]["coverage"], 1) if len(rows) >= 2 else None
        ),
        "paired_wins": paired.get("score_wins_vs_bare"),
        "paired_ties": paired.get("score_ties_vs_bare"),
        "paired_n": paired.get("n"),
    }


def _exp3(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not data:
        return None
    res = data.get("results") or {}
    if not res:
        return None
    out: dict[str, Any] = {"arms": {}}
    for arm, v in res.items():
        out["arms"][arm] = {
            "mean_reward": round(float(v["mean_reward"]), 4),
            "std": round(float(v.get("std", 0.0)), 4),
            "n_rounds": len(v.get("curve") or []),
            "best_skill": v.get("best_skill"),
            "cost": round(float(v.get("cost_yuan", 0.0)), 4),
            "evolved": len(v.get("evolved_skills") or []),
        }
    # 统计结论由 bench 写入；没有就标成「未知」，绝不猜
    out["statistics"] = data.get("statistics") or {
        "test": "not_computed",
        "conclusion": "样本量不足以区分两种选择策略；本实验仅验证闭环连通性。",
        "evidence_level": "preliminary",
    }
    out["evidence_level"] = "preliminary"
    return out


# ======================================================================
def _collect(split: str) -> dict[str, Any]:
    """收集某个 split 的三组实验 KPI。文件名形如 exp1_retrieval_dev.json。"""
    return {
        "exp1": _exp1(_load_json(OUT / f"exp1_retrieval_{split}.json")),
        "exp2": _exp2(_load_json(OUT / f"exp2_execution_{split}.json")),
        "exp3": _exp3(_load_json(OUT / f"exp3_evolution_{split}.json")),
    }


def build() -> dict[str, Any]:
    cfg = _load_yaml()

    splits = {
        "dev": _collect("dev"),
        "heldout": _collect("heldout"),
    }
    for name, data in splits.items():
        for key, val in data.items():
            if val is not None:
                val["split"] = name
                val["split_label"] = ("DEV（调参集，结果仅作过程记录）"
                                      if name == "dev"
                                      else "HELD-OUT（冻结测试集，最终结论只引这里）")

    manifest: dict[str, Any] = {
        "project": cfg["project"],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": _git_commit(),
        "provenance": {
            "config": "config/experiment.yaml",
            "config_hash": _sha256(CONFIG),
            "model": cfg["model"]["name"],
            "temperature": {
                "executor": cfg["model"]["temperature_executor"],
                "judge": cfg["model"]["temperature_judge"],
            },
            "retrieval_weights": cfg["retrieval"]["hybrid"]["weights"],
            "selection_policy": cfg["selection"]["policy"],
            "pricing_version": cfg["pricing"]["version"],
            "sources": {
                f.name: {"sha256": _sha256(f), "bytes": f.stat().st_size}
                for f in sorted(OUT.glob("exp*.json"))
            },
            "benchmark_hashes": {
                name: _sha256(ROOT / d["file"])
                for name, d in cfg["datasets"].items()
            },
        },
        "datasets": cfg["datasets"],
        "retrieval": cfg["retrieval"],
        "selection": cfg["selection"],
        "pricing": cfg["pricing"],
        "display": cfg["display"],
        # 报告口径规则：最终结论只能引用 heldout
        "reporting_rule": {
            "final_results_must_cite": "heldout",
            "dev_role": "tuning only",
            "note": "dev 集数字只能标注为调参结果；报告结论必须引用 held-out。",
        },
        "splits": splits,
    }
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="校验现有 manifest 是否与 out/*.json 一致")
    args = ap.parse_args()

    m = build()
    if args.check:
        old = _load_json(MANIFEST)
        if old is None:
            print("[check] out/manifest.json 不存在，请先运行 build")
            return 1
        # 只比数字部分，时间戳与 hash 天然会变
        a = json.dumps(old.get("splits") or old.get("experiments"), sort_keys=True)
        b = json.dumps(m.get("splits"), sort_keys=True)
        if a != b:
            print("[check] FAIL：manifest 与 out/*.json 不一致，请重新生成")
            return 1
        print("[check] PASS：manifest 与实验产物一致")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"已生成 {MANIFEST.relative_to(ROOT)}")
    print(f"  git commit : {m['git_commit']}")
    for split in ("dev", "heldout"):
        d = m["splits"].get(split) or {}
        if not any(d.values()):
            print(f"  [{split}] 暂无数据（未运行该 split 的实验）")
            continue
        print(f"  [{split.upper()}]")
        if d.get("exp1"):
            print("    召回    : " + " / ".join(f"{x['recall']}%" for x in d["exp1"]["rows"]))
            print("    编排完整: " + " / ".join(f"{x['orchestration']}%" for x in d["exp1"]["rows"]))
        if d.get("exp2"):
            print("    均分    : " + " / ".join(f"{x['score']}" for x in d["exp2"]["rows"]))
        if d.get("exp3"):
            print("    奖励    : " + " / ".join(f"{k}={v['mean_reward']}" for k, v in d["exp3"]["arms"].items()))
            print(f"    结论    : {d['exp3']['statistics'].get('verdict')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
