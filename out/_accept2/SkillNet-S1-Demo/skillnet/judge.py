"""独立评审：用 LLM rubric 盲评研究方案的执行质量。

与执行者分离（立理 S1 的「执行智能体与评审智能体相互独立」设计），
评审时隐藏方案来自哪个实验组，避免位置偏见。
"""
from __future__ import annotations

from typing import Any

from .llm import chat_json

RUBRIC = {
    "skill_grounding": "是否用到了与任务真正匹配的专业方法；技能/工具的调用是否恰当、是否覆盖了任务的关键环节",
    "executability": "步骤是否具体可执行：是否给出参数、阈值、工具名与判据，而非空泛的方法论",
    "rigor": "是否包含对结果可靠性的验证方式，是否指出常见陷阱与失败模式并给出应对",
    "scientific_validity": "科学上是否成立：方法选择、统计/实验设计与结论边界是否合理",
}
WEIGHTS = {
    "skill_grounding": 0.30,
    "executability": 0.25,
    "rigor": 0.25,
    "scientific_validity": 0.20,
}


def score_plan(
    task: str, plan: dict[str, Any], reference_points: list[str] | None = None
) -> dict[str, Any]:
    """对一份研究方案打分。

    除 0-10 的 rubric 分数外，若给出 `reference_points`（来自领域技能库的
    专业操作要点：常见陷阱 + 验证清单），还会计算**要点覆盖率**——
    这是比纯主观打分更客观的指标，用来衡量方案是否真的包含专业操作性知识。
    """
    steps = plan.get("steps") or []
    body = []
    for i, st in enumerate(steps, 1):
        if isinstance(st, dict):
            body.append(
                f"{i}. [{(st.get('skill') or 'manual')}] {st.get('action','')} "
                f"| 参数: {', '.join(map(str, st.get('key_params') or []))[:240]} "
                f"| 产出: {st.get('expected_output','')} "
                f"| 校验: {st.get('check','')}"
            )
        else:
            body.append(f"{i}. {st}")
    plan_text = (
        f"思路: {plan.get('approach','')}\n"
        + "\n".join(body)
        + f"\n风险: {'; '.join(map(str, plan.get('risks') or []))}"
        + f"\n交付物: {'; '.join(map(str, plan.get('artifacts') or []))}"
    )

    dims = "\n".join(f"- {k}：{v}" for k, v in RUBRIC.items())
    pts = reference_points or []
    pts_block = ""
    if pts:
        listed = "\n".join(f"P{i}: {p}" for i, p in enumerate(pts, 1))
        pts_block = (
            "\n【领域专业要点（来自该领域的技能库，非评分参考，仅用于判定覆盖）】\n"
            f"{listed}\n\n"
            "请逐条判断该方案是否实质性地覆盖了要点 Pi："
            "只要方案里明确要求做这件事（哪怕措辞不同）就算覆盖；只是泛泛提及不算。\n"
            "输出 covered 数组，元素为被覆盖要点的编号（整数）。\n"
        )
    prompt = (
        "你是一位严格的科研方法学评审专家。请对下面这份「研究执行方案」按 rubric 打分。\n"
        "评审只看方案本身是否能让一个有能力的执行者真正完成任务；\n"
        "不要因为文风好而加分，也不要因为方案写得长、术语多就加分或减分。\n"
        "0-3 分表示缺失或不可执行，4-6 分表示部分可用，7-8 分表示合格，9-10 分表示专业级。\n\n"
        f"【研究任务】\n{task}\n\n"
        f"【方案】\n{plan_text[:6000]}\n"
        f"{pts_block}\n"
        f"【评分维度】\n{dims}\n\n"
        '严格输出 JSON：{"skill_grounding": 数字, "executability": 数字, '
        '"rigor": 数字, "scientific_validity": 数字, "covered": [编号...], '
        '"comment": "一到两句关键理由"}'
    )
    out = chat_json(
        [{"role": "user", "content": prompt}],
        role="judge",
        temperature=0.0,
        max_tokens=600,
        default={},
    )
    scores: dict[str, float] = {}
    for k in RUBRIC:
        try:
            scores[k] = float(out.get(k, 0))
        except (TypeError, ValueError):
            scores[k] = 0.0
    total = sum(scores[k] * WEIGHTS[k] for k in RUBRIC)

    covered_ids: list[int] = []
    for x in out.get("covered") or []:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if 1 <= i <= len(pts):
            covered_ids.append(i)
    coverage = len(set(covered_ids)) / len(pts) if pts else None

    return {
        "scores": scores,
        "weighted": round(total, 3),
        "coverage": round(coverage, 4) if coverage is not None else None,
        "covered": sorted(set(covered_ids)),
        "n_points": len(pts),
        "comment": str(out.get("comment", ""))[:300],
    }


def reference_points_from_skills(lib, gold_names: list[str], per_skill: int = 3) -> list[str]:
    """从 gold 技能中抽取专业操作要点：常见陷阱 + 验证清单。"""
    pts: list[str] = []
    for n in gold_names:
        s = lib.get(n)
        if not s:
            continue
        pts.extend(s.pitfalls[:2])
        pts.extend(s.verification[:1])
    # 去重并限长
    seen: set[str] = set()
    uniq = []
    for p in pts:
        k = p.strip()
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq[: per_skill * max(1, len(gold_names))]
