"""Show recorded, independently rechecked method outcomes in Chinese, at no API cost."""

from __future__ import annotations

import json

from research.skill_quality.manifest import digest, read_jsonl

from .cli import LABELS
from .gate import evaluate
from .owned import program_bundle
from .reproduce import RESULTS, reproduce


def main() -> None:
    verification = reproduce()
    print("证据约束技能判别器 v1 | 规则＋产物验证 | 不调用模型 API\n")
    rows = read_jsonl(RESULTS / "diagnostic-v3/behavior-reports.jsonl")
    for program in ["sum_correct", "sum_abs", "dedup_key", "dag_reverse"]:
        report = next(r["report"] for r in rows if r["program"] == program)
        behavior = report["behavior"]
        print(f"{program}: {LABELS[report['decision']]}；独立产物 {behavior['passed']}/{behavior['n']} 通过")
    good = next(r["report"]["behavior"] for r in rows if r["program"] == "sum_correct")
    boundary = evaluate(
        program_bundle("sum_correct"),
        task_family="integer_sum",
        task_input_sha256=digest({"values": [999]}),
        behavior=good,
        trusted_behavior_ids=frozenset({good["receipt_id"]}),
    )
    print("新输入 [999]：" + LABELS[boundary["decision"]] + "；不从24个测试外推到所有整数输入。")
    natural = read_jsonl(RESULTS / "natural-v3/reports.jsonl")
    bad = next(r for r in natural if r["findings"])
    print(f"\n真实包案例：{bad['identity']} -> {LABELS[bad['decision']]}")
    command = next(c for c in bad["command_observations"] if c["result"]["status"] == "inconsistent_static")
    print(f"来源：{command['document']}:{command['start_line']}\n命令：{command['command']}")
    print("原因：文档参数与脚本字面契约冲突；不等同于整个技能永久无效。")
    print("\n真实包 200 个：1 个有明确接口冲突，199 个尚缺充分任务证据；没有把未知标成优秀。")
    print("受控留出：20 个父配置，140 个已知缺陷全部检出，40 个无害对照零误报。")
    print("以上构造样本成绩不能写成真实社区技能整体准确率。")
    print("\n复核：" + json.dumps(verification, ensure_ascii=False))


if __name__ == "__main__":
    main()
