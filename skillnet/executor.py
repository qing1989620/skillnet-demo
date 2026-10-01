# -*- coding: utf-8 -*-
"""executor.py —— 技能驱动的真实执行（Run → Validate → Fix 循环）。

设计依据（Agent Skills 官方实践）
--------------------------------
1. 技能是**可执行的程序性知识**：技能的 steps / pitfalls / verification 不只是
   提示词素材，而是**代码生成的约束**与**产物的验收标准**；
2. 官方推荐迭代方式为 Run → Validate → Fix → Repeat：先跑，用真实报错修，再跑；
3. 失败修复时必须带上该技能记录的**已知陷阱**——这正是「技能改变行为」的证据：
   同一个错误，没有技能只能盲试，有技能可以对照清单定位。

与旧实现的差别
--------------
旧：一次 LLM 调用产出整份方案文本（零代码运行，零验证）→ 产物是作文。
新：选定可执行步骤 → 生成代码 → **沙箱真跑** → 失败带错误与技能陷阱修复重试 →
    用技能 verification 逐条核对产物 → 产出「代码 + 真实输出 + 真实文件 + 自检报告」。
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any

from . import llm, sandbox

MAX_OUTPUT_IN_PROMPT = 2500
# 代码生成的 token 预算：实测 3000 会让中等长度的科研代码被截断（结尾缺 ```
# 导致提取失败），提到 7000 覆盖大多数单文件分析脚本。
CODE_MAX_TOKENS = 7000


def config_code_tokens() -> int:
    return CODE_MAX_TOKENS


def _skill_brief(skill: Any, mode: str = "contract") -> str:
    """把技能组织进执行提示词。

    mode 决定技能的「用法」，这是本项目的核心差异点：
      contract —— 契约约束：steps 当步骤、pitfalls 当红线、verification 当验收标准，
                  失败修复时也会带上 pitfalls（SkillNet 的做法）
      prompt   —— 背景资料：只把能力与步骤当参考塞进提示词，无陷阱约束、无验收
                  （「提示词里塞技能」的常见做法）
      none     —— 不给技能（裸模型）
    """
    if skill is None:
        return "（本步无对应技能，按通用最佳实践执行）"
    if mode == "prompt":
        return (f"参考资料（可选采纳）：{skill.name} —— {skill.capability}\n"
                + "\n".join(f"  - {s}" for s in (skill.steps or [])[:6]))
    lines = [f"技能：{skill.name}（{skill.domain}）", f"能力：{skill.capability}"]
    if skill.steps:
        lines.append("标准步骤（按此执行，可精简）：")
        lines += [f"  {i}. {s}" for i, s in enumerate(skill.steps[:6], 1)]
    if skill.pitfalls:
        lines.append("已知陷阱（**必须避免**，代码要体现规避措施）：")
        lines += [f"  - {p}" for p in skill.pitfalls[:5]]
    if skill.verification:
        lines.append("验收清单（产物必须能满足，代码中应有对应输出）：")
        lines += [f"  - {v}" for v in skill.verification[:5]]
    return "\n".join(lines)


def _gen_code_prompt(task: str, step: dict[str, Any], skill: Any,
                     stack: dict[str, str], prev_output: str = "",
                     mode: str = "contract") -> str:
    libs = "、".join(f"{k} {v}" for k, v in stack.items()) or "仅标准库"
    action = step.get("action") or step.get("title") or ""
    params = step.get("key_params") or []
    expect = step.get("expected_output") or ""
    return f"""你是一位严谨的科研工程师。请为下面这一步写出**可直接运行**的 Python 代码。

研究任务：{task}

当前步骤：{action}
关键参数：{json.dumps(params, ensure_ascii=False)}
预期产出：{expect}

{_skill_brief(skill, mode)}

执行环境（**只能使用这些库**，不要 import 其他第三方包）：
{libs}

要求：
1. 代码必须自包含、可直接运行，运行后把关键结果 print 出来（可量化的数字，不要只打印"完成"）；
2. 如涉及数据：**若无真实数据，用合理的模拟数据并在代码注释与输出中明确标注「模拟数据」**——
   绝不允许把模拟结果说成真实实验结论；
3. 若这一步适合出图（趋势/分布/对比/收敛），用 {sandbox.MATPLOTLIB_CJK_HINT.splitlines()[0].lstrip('# ')} 风格
   的 matplotlib 配置生成 1 张图并存为 figure.png（中文字体按下面给的方式设置）；
4. 需要落盘的数据表保存为 CSV；
5. 代码中要体现对「已知陷阱」的规避（例如做相应检查并 print 检查结论）；
6. 只输出代码本身，用 ```python 包裹，不要解释。

{sandbox.MATPLOTLIB_CJK_HINT}"""


def _fix_prompt(code: str, err: str, skill: Any, attempt: int,
                mode: str = "contract") -> str:
    traps = ""
    if mode == "contract" and skill is not None and skill.pitfalls:
        traps = ("\n对照该技能记录的已知陷阱逐条排查（这是技能最有价值的部分）：\n"
                 + "\n".join(f"  - {p}" for p in skill.pitfalls[:5]))
    return f"""下面这段 Python 代码运行失败了（第 {attempt} 次尝试）。请修复它。

【代码】
```python
{code}
```

【错误输出】
{err[-MAX_OUTPUT_IN_PROMPT:]}
{traps}

修复要求：
1. 只改必要的部分，保持原有逻辑与分析目标；
2. 若错误是缺少第三方库，改用标准库或已装库实现（不要 import 未安装的包）；
3. 若错误与数据/维度/类型有关，做相应检查与兜底；
4. 修好后确保关键结果有 print 输出；
5. 只输出修复后的完整代码（```python 包裹），不要解释。"""


def _extract_code(text: str) -> str:
    """从模型回复里提取 Python 代码。

    必须容错三种情况（实测踩过）：① 正常围栏；② **围栏未闭合**（模型输出被
    max_tokens 截断，结尾没有 ```）；③ 完全没有围栏。早先只处理 ①，
    截断时会把带 ``` 的原文交给解释器，报一堆 "invalid syntax" 白跑三轮。
    """
    s = (text or "").strip()
    if not s:
        return ""
    # ① 完整围栏（可能有多个，取最长的一段）
    blocks = re.findall(r"```(?:python|py)?[ \t]*\r?\n(.*?)(?:```|\Z)", s, re.S)
    if blocks:
        code = max(blocks, key=len)
    else:
        # ②/③ 无围栏：去掉可能的开头围栏行与结尾围栏
        code = re.sub(r"^```(?:python|py)?[ \t]*\r?\n?", "", s)
        code = re.sub(r"\r?\n?```\s*$", "", code)
    return code.strip()


def _verify_with_skill(skill: Any, task: str, action: str, code: str,
                       stdout: str, files: list[str]) -> list[dict[str, Any]]:
    """用技能的验收清单逐条核对产物（技能契约的落地环节）。"""
    if skill is None or not skill.verification:
        return []
    items = list(skill.verification[:5])
    prompt = f"""下面是某一研究步骤的**产物**，请对照该技能的验收清单逐条判定是否满足。

任务：{task}
步骤：{action}
技能：{skill.name}

验收清单：
{chr(10).join(f'{i}. {v}' for i, v in enumerate(items, 1))}

产出的代码：
```python
{code[:3000]}
```

运行输出：
{stdout[-1500:]}

落盘文件：{', '.join(files) if files else '（无）'}

判定要求：
- 每条给出 passed(true/false)、evidence（引用产物中的具体证据，30 字内）；
- 证据必须来自上面的代码或输出，**不得推测**；无法判断时 passed=false 且 evidence 写"产物中未见"。

严格输出如下 JSON（顶层键名必须是 checks，不要改名）：
{{"checks": [{{"item": "清单条目原文", "passed": true, "evidence": "证据"}}]}}"""

    obj = llm.chat_json(
        [{"role": "system", "content": "你是严格的科研产物验收员，只依据给定材料判定，输出 JSON。"},
         {"role": "user", "content": prompt}],
        role="judge", temperature=0.0, max_tokens=1500,
        default={"checks": []})
    # 宽容解析：模型可能把顶层键写成 checklist / items / results（实测遇过 checklist）
    checks = None
    if isinstance(obj, dict):
        for key in ("checks", "checklist", "items", "results", "verification"):
            if isinstance(obj.get(key), list):
                checks = obj[key]
                break
        if checks is None and isinstance(obj.get("checks"), dict):
            checks = [obj["checks"]]
    out: list[dict[str, Any]] = []
    if isinstance(checks, list):
        for i, c in enumerate(checks[:len(items)]):
            if not isinstance(c, dict):
                continue
            out.append({
                "item": items[i],
                "passed": bool(c.get("passed")),
                "evidence": str(c.get("evidence") or "")[:120],
            })
    return out


def execute_step(task: str, step: dict[str, Any], skill: Any,
                 workdir: pathlib.Path, max_fix: int = 2,
                 timeout: int = 90, mode: str = "contract") -> dict[str, Any]:
    """执行单个步骤：生成代码 → 沙箱运行 → 失败修复重试 → 技能验收。

    返回结构化结果，供 API/前端展示（含每次尝试的真实输出，失败也如实返回）。
    """
    stack = sandbox.available_stack()
    attempts: list[dict[str, Any]] = []
    code = ""
    result: dict[str, Any] = {}

    for i in range(max_fix + 1):
        if i == 0:
            raw = llm.chat(
                [{"role": "system", "content": "你是严谨的科研工程师，只输出可运行代码。"},
                 {"role": "user", "content": _gen_code_prompt(task, step, skill, stack, mode=mode)}],
                role="executor", temperature=0.2, max_tokens=config_code_tokens())
            code = _extract_code(raw)
        else:
            raw = llm.chat(
                [{"role": "system", "content": "你是严谨的科研工程师，只输出修复后的完整代码。"},
                 {"role": "user", "content": _fix_prompt(code, attempts[-1]["stderr"], skill, i, mode)}],
                role="executor", temperature=0.1, max_tokens=config_code_tokens())
            code = _extract_code(raw)

        # 本地语法预检：语法错不必进沙箱（更快，且错误定位更准）
        import ast as _ast
        try:
            _ast.parse(code)
            result = sandbox.run_python(code, timeout=timeout, keep_dir=True,
                                        workdir=workdir / f"try{i + 1}")
        except SyntaxError as se:
            lines = code.splitlines()
            ctx = "\n".join(f"{n}: {lines[n - 1]}" for n in
                             range(max(1, (se.lineno or 1) - 2), min(len(lines), (se.lineno or 1) + 2) + 1))
            result = {
                "ok": False, "stdout": "", "returncode": -1, "duration": 0.0,
                "artifacts": [], "error_kind": "syntax",
                "stderr": f"SyntaxError: {se.msg} (line {se.lineno})\n{ctx}",
                "workdir": str(workdir),
            }
        attempts.append({
            "n": i + 1,
            "ok": result["ok"],
            "stderr": result["stderr"][-1200:],
            "stdout": result["stdout"][-1200:],
            "error_kind": result["error_kind"],
            "duration": result["duration"],
        })
        if result["ok"]:
            break

    # 落盘最终代码，供预览与复核
    (workdir / "final_code.py").write_text(code, encoding="utf-8")

    files = [a["name"] for a in result.get("artifacts", [])]
    checks = (_verify_with_skill(skill, task, step.get("action", ""), code,
                                 result.get("stdout", ""), files)
              if (result.get("ok") and mode == "contract") else [])
    passed = sum(1 for c in checks if c["passed"])

    return {
        "skill": getattr(skill, "name", None),
        "action": step.get("action", ""),
        "code": code,
        "final_ok": bool(result.get("ok")),
        "attempts": attempts,
        "n_attempts": len(attempts),
        "fixed": len(attempts) > 1,
        "stdout": result.get("stdout", "")[-4000:],
        "artifacts": result.get("artifacts", []),
        "verification": checks,
        "verification_passed": passed,
        "verification_total": len(checks),
        "workdir": str(workdir),
        "mode": mode,
    }


def pick_executable_step(plan: dict[str, Any]) -> int:
    """从方案里挑出最适合真实执行的一步（返回下标，-1 表示没有）。

    经验规则：优先挑「分析/计算/验证/统计/训练/评估」类动作，跳过纯文献/写作/沟通类。
    目的是让演示稳定产出可运行的东西，而不是碰运气选到「写一份综述」。
    """
    steps = plan.get("steps") or []
    score_kw = ("分析", "计算", "统计", "验证", "评估", "训练", "拟合", "模拟", "检验",
                "清洗", "处理", "提取", "建模", "测算", "对比", "可视化", "绘制", "审计")
    skip_kw = ("综述", "检索", "投稿", "沟通", "汇报", "撰写引言", "写一份", "收集反馈")
    best, best_score = -1, -1
    for i, st in enumerate(steps):
        text = str(st.get("action") if isinstance(st, dict) else st)
        if any(k in text for k in skip_kw):
            continue
        sc = sum(1 for k in score_kw if k in text)
        if sc > best_score:
            best, best_score = i, sc
    return best
