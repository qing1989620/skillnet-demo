"""Recompute descriptive inventory counts; never turn mock calls into research results."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .manifest import digest
from .schemas import SkillSnapshot


def inventory_metrics(
    snapshots: list[SkillSnapshot],
    baseline: list[dict[str, Any]],
    audits: list[dict[str, Any]],
    split: dict[str, Any],
    dedup: dict[str, Any],
) -> dict[str, Any]:
    ids = {s.skill_uid for s in snapshots}
    if len(ids) != len(snapshots):
        raise ValueError("Duplicate Skill UID")
    for rows in (baseline, audits):
        if len(rows) != len(ids) or {r["skill_uid"] for r in rows} != ids:
            raise ValueError("Incomplete or duplicated inventory cohort")
    flags = Counter(f["rule"] for row in audits for f in row["findings"])
    stored = Counter(round(row["stored_score"], 6) for row in baseline)
    recomputed = Counter(round(row["recomputed_score"], 6) for row in baseline)
    per_source = Counter(s.source_repo for s in snapshots)
    by_baseline = {row["skill_uid"]: row for row in baseline}
    by_uid = {item.skill_uid: item for item in snapshots}
    split_kinds = {
        part: dict(Counter(by_uid[uid].source_kind for uid in split["sample_ids"][part]))
        for part in ("D1", "D2")
    }

    def stored_grade(row: dict[str, Any], dimension: str) -> str | None:
        value = row["stored_quality"].get(dimension)
        return value.get("level") if isinstance(value, dict) else value

    good_flagged = [
        row["skill_uid"]
        for row in audits
        if row["findings"]
        and by_baseline[row["skill_uid"]]["recomputed_quality"]["safety"]["level"] == "Good"
    ]
    return {
        "scope": "D0_descriptive_static_audit_not_quality_accuracy_or_task_utility",
        "skills": len(snapshots),
        "sources": dict(sorted(per_source.items())),
        "domains": dict(sorted(Counter(s.domain for s in snapshots).items())),
        "source_kinds": dict(Counter(s.source_kind for s in snapshots)),
        "registered_resources_rehashed": sum(len(s.resources) for s in snapshots),
        "registered_resource_bytes_rehashed": sum(r.bytes for s in snapshots for r in s.resources),
        "license_declarations": dict(Counter(s.declared_license for s in snapshots)),
        "license_independent_review": "not_done",
        "raw_exact_duplicate_groups": len(dedup["exact_groups"]),
        "normalized_duplicate_groups": len(dedup["normalized_groups"]),
        "content_clusters": len(dedup["content_clusters"]),
        "near_pairs": len(dedup["near_pairs"]),
        "source_content_component_sizes": split["component_sizes"],
        "static_flag_occurrences": dict(flags),
        "skills_with_static_review_flags": sum(bool(r["findings"]) for r in audits),
        "recomputed_safety_good_with_full_body_flags": len(good_flagged),
        "flagged_good_skill_uids": good_flagged,
        "flag_interpretation": "review_leads_only; not_confirmed_vulnerabilities; no_safety_gold",
        "stored_score_distribution": {str(k): v for k, v in sorted(stored.items())},
        "recomputed_score_distribution": {str(k): v for k, v in sorted(recomputed.items())},
        "stored_vs_recomputed_grade_disagreements": sum(
            any(
                stored_grade(row, dim) in ("Good", "Average", "Poor")
                and stored_grade(row, dim) != value["level"]
                for dim, value in row["recomputed_quality"].items()
            )
            for row in baseline
        ),
        "stored_quality_absent_skills": sum(not row["stored_quality"] for row in baseline),
        "stored_quality_nonstandard_grade_skills": sum(
            any(
                stored_grade(row, dim) not in ("Good", "Average", "Poor", None)
                for dim in row["recomputed_quality"]
            )
            for row in baseline
        ),
        "D1_samples": len(split["sample_ids"]["D1"]),
        "D2_samples": len(split["sample_ids"]["D2"]),
        "sample_source_kinds": split_kinds,
        "split_confound": "derived_project_cards_exist_only_in_D2; stratify_and_expand_sources_before_formal_P1",
        "split_status": split["status"],
        "human_annotators": 0,
        "human_gold_items": 0,
        "new_live_api_calls": 0,
        "new_api_cost_usd": "0",
        "new_skill_execution_trials": 0,
        "P1": {"status": "not_run", "mae": None, "reason": "independent_human_gold_missing"},
        "P2": {"status": "not_run", "delta_pp": None, "reason": "paired_verified_trials_not_run"},
        "candidate_status": "shadow_only_not_validated",
        "production_weights_changed": False,
    }


def render_report(metrics: dict[str, Any]) -> str:
    source_lines = "\n".join(f"| {key} | {value} |" for key, value in metrics["sources"].items())
    return f"""# SkillNet 研究：Phase A 实测报告

<!-- metrics-sha256={digest(metrics)} -->

本报告只报告仓库基线复核与 D0 静态描述。没有人类金标准、真实 Judge 调用或新的 Skill 执行结果。

| 实测量 | 数值 | 原始来源 |
| --- | ---: | --- |
| Skill 条目 | {metrics["skills"]} | snapshots/skills.jsonl |
| 已重新计算哈希的登记文件 | {metrics["registered_resources_rehashed"]} | snapshots/skills.jsonl → resources |
| 原始正文精确重复组 | {metrics["raw_exact_duplicate_groups"]} | duplicate_groups.json |
| 规范化正文重复组 | {metrics["normalized_duplicate_groups"]} | duplicate_groups.json |
| 词五元组近重配对（Jaccard ≥ 0.85） | {metrics["near_pairs"]} | duplicate_groups.json |
| 静态线索涉及的 Skill | {metrics["skills_with_static_review_flags"]} | static_audits.jsonl |
| 旧 safety=Good 且全文触发审查线索 | {metrics["recomputed_safety_good_with_full_body_flags"]} | baseline.jsonl + static_audits.jsonl |
| D1 未标注样本 | {metrics["D1_samples"]} | dataset_manifest.json |
| D2 未标注样本 | {metrics["D2_samples"]} | dataset_manifest.json |

以上线索可能只是文档在描述危险操作或防护措施，不能当作安全漏检率或认定作者恶意。
来源/内容连接组大小为 `{metrics["source_content_component_sizes"]}`。抽样状态：`{metrics["split_status"]}`。
所有登记资源均只读；`declared_license` 是仓库声明，尚未经独立许可审核。

| 来源仓库 | 条目 |
| --- | ---: |
{source_lines}

旧质量字典为空的有 {metrics["stored_quality_absent_skills"]} 项；旧排序对这些项目使用默认 0.6，它不是已完成的评级。
另有 {metrics["stored_quality_nonstandard_grade_skills"]} 项含旧规则不识别的等级，原排序仍保留原始回退行为。
只比较已有的 Good/Average/Poor 等级，有 {metrics["stored_vs_recomputed_grade_disagreements"]} 项至少一维与重新计算不同。
两种旧分数同时保留，不能把二者互换当作同一个 baseline。
源文档类型为 `{metrics["source_kinds"]}`；派生卡片不冒充上游原始 SKILL.md。
D1/D2 的文档类型分别为 `{metrics["sample_source_kinds"]}`。
目前 D2 混有项目派生卡片，而 D1 是原始社区正文；正式 P1 前须扩大独立来源或缩小原始正文子层样本量，并冻结分层口径。

P1：`not_run`，独立双人金标准尚未收集。P2：`not_run`，没有成对真实任务验收。
本轮新真实 API 调用 {metrics["new_live_api_calls"]} 次，API 费用 ${metrics["new_api_cost_usd"]}，
新 Skill 执行试次 {metrics["new_skill_execution_trials"]}。Mock 单测不计入这些数值。

本阶段代码可准备下一阶段材料，但不支持“评级更准”“任务成功率提高”或“候选已晋级”的结论。
旧生产排序、Skill.quality、stats 和十二门没有修改。

复算：`python -m research.skill_quality.cli verify --run-id <本运行ID>`。
每一项数字从固定 JSONL/manifest 重算；若 raw、metrics、报告或 SHA 不符，命令失败。
"""
