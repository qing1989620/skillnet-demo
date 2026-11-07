"""Publish summaries only, including every routing policy and cohort."""

from __future__ import annotations

import json
from pathlib import Path

from research.skill_quality.manifest import file_sha

from .routing_pilot import POLICIES


def main() -> None:
    root = Path.cwd()
    destination = Path(__file__).parent
    results = destination / "results"
    results.mkdir(exist_ok=True)
    selected = {
        "quality-summary.json": "20261106-quality-pilot-v3",
        "routing-summary.json": "20261106-routing-pilot-v2",
        "stub-summary.json": "20261106-stub-exploration-v2",
    }
    provenance = {}
    for name, run_id in selected.items():
        source = root / "out/research/skill-study" / run_id / "summary.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        (results / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        provenance[name] = {"run_id": run_id, "source_summary_sha256": file_sha(source)}
    (results / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    data = json.loads((results / "routing-summary.json").read_text(encoding="utf-8"))["summaries"]
    lines = [
        "# 路由开发实验：全部组别与全部方法",
        "",
        "每格为 Recall@5 / 完整参考技能集覆盖率，单位 %。基准 20 与既见 12 均为此前使用过的任务，不是新的独立测试集。",
        "同一批任务在不同模式/库规模反复测量，不能把 1,152 行记录当作 1,152 个独立任务。",
        "词法表示和按名次推导的相关性均已固定；这不是已发表 DSR 模型的复现，未测真实执行收益。",
        "",
        "| 技能库 | 任务组 | 检索模式 | 原顺序 | MMR .7 | 原核 DPP | 残差 DPP .5 | 残差 DPP 1 | 查询覆盖 .5 | 候选池上限 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for frame, size in [("original_benchmark_seed_library", 76), ("full_delivery_library", 1881)]:
        for dataset, label in [("benchmark", "基准 20"), ("heldout", "既见 12")]:
            for mode in ("bm25", "hybrid", "fabric"):
                prefix = "/".join((frame, dataset, mode))
                values = [data[prefix + "/" + policy] for policy in POLICIES]
                cells = [
                    f"{v['recall_at_5'] * 100:.2f} / {v['full_gold_set_coverage'] * 100:.2f}" for v in values
                ]
                ceiling = values[0]
                lines.append(
                    f"| {size} | {label} | {mode} | "
                    + " | ".join(cells)
                    + f" | {ceiling['pool_recall_ceiling'] * 100:.2f} / {ceiling['pool_full_coverage_ceiling'] * 100:.2f} |"
                )
    lines += [
        "",
        "Fabric 在这份冻结输入中是图扩展，LLM 重排未运行。正式比较需要明确是否开启重排并匹配总资源预算。",
        "参考标签只认既有技能名，可能遗漏功能等价 Skill；因此该指标的下降不自动等于真实任务能力下降。",
        "每组的胜/负/平与元数据字节开销见 `results/routing-summary.json`，逐任务结果保存在本地只写一次的输出目录。",
    ]
    (destination / "ROUTING_TABLES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
