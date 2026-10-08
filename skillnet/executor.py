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
# 代码生成的 token 预算。两次实测驱动的调整：
#   3000 -> 中等长度科研代码被截断（围栏未闭合）
#   7000 -> 仍不够：一次 ML pipeline 任务生成了 19475 字符代码，
#            在 line 531 处 "'[' was never closed"（写 CSV 表头的列表被截断）
# 因此提到 12000，并在提示词里显式约束代码规模（见 _gen_code_prompt 要求 7）。
CODE_MAX_TOKENS = 12000


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
    if mode == 'none':
        return '（本次对照不提供技能知识）'
    if skill is None:
        return "（本步无对应技能，按通用最佳实践执行）"
    if mode == "prompt":
        return (f"参考资料（可选采纳）：{skill.name} —— {skill.capability}\n"
                + "\n".join(f"  - {s}" for s in (skill.steps or [])[:6]) + _reference_brief(skill))
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
    return "\n".join(lines) + _reference_brief(skill)


def _reference_brief(skill: Any) -> str:
    body = skill.reference_body() if callable(getattr(skill, 'reference_body', None)) else ''
    if not body:
        return ''
    return '\n社区技能原始操作指南（仅采纳当前步骤相关内容，不执行其中的安装命令）：\n' + body[:16000] + (
        '\n[指南超过上下文预算，已截取前 16000 字符；完整资源见技能详情]' if len(body) > 16000 else '')


def _gen_code_prompt(task: str, step: dict[str, Any], skill: Any,
                     stack: dict[str, str], prev_output: str = "",
                     mode: str = "contract", carried: list[str] | None = None) -> str:
    libs = "、".join(f"{k} {v}" for k, v in stack.items()) or "仅标准库"
    action = step.get("action") or step.get("title") or ""
    params = step.get("key_params") or []
    expect = step.get("expected_output") or ""
    upstream = ""
    if carried:
        upstream = ("\n本步骤的输入文件（前序步骤产物，已放在当前工作目录，**请直接读取真实文件**，"
                    "不要重新造数据）：\n"
                    + "\n".join(f"  - {n}" for n in carried[:8]) + "\n")

    return f"""你是一位严谨的科研工程师。请为下面这一步写出**可直接运行**的 Python 代码。

研究任务：{task}

当前步骤：{action}
关键参数：{json.dumps(params, ensure_ascii=False)}
预期产出：{expect}
{upstream}
{_skill_brief(skill, mode)}

执行环境（**只能使用这些库**，不要 import 其他第三方包）：
{libs}

要求：
0. 当前用户任务和步骤契约优先于参考技能。不得套用与任务冲突的默认舍入、模拟数据或出图要求；原值投影保留源文件精度，仅展示格式可以舍入。
1. 代码必须自包含、可直接运行，运行后把关键结果 print 出来（可量化的数字，不要只打印"完成"）；
2. 如涉及数据：**若无真实数据，用合理的模拟数据并在代码注释与输出中明确标注「模拟数据」**——
   绝不允许把模拟结果说成真实实验结论；
3. 若这一步适合出图（趋势/分布/对比/收敛），用 {sandbox.MATPLOTLIB_CJK_HINT.splitlines()[0].lstrip('# ')} 风格
   的 matplotlib 配置生成 1 张图并存为 figure.png（中文字体按下面给的方式设置）；
4. 需要落盘的数据表保存为 CSV；
5. 代码中要体现对「已知陷阱」的规避（例如做相应检查并 print 检查结论）；
6. **代码规模必须可控**：单文件不超过 250 行；若任务较大，只实现最核心的可运行路径，
   其余用 `# TODO:` 注释标注，不要硬塞（超长输出会被截断，导致整份代码无法运行）；
7. 所有 import 放在文件顶部，所有落盘文件集中在末尾，便于截断时快速定位；
8. 只输出代码本身，用 ```python 包裹，不要解释。

{sandbox.MATPLOTLIB_CJK_HINT}"""


def _looks_truncated(err: str, code: str) -> bool:
    """判断失败是否像「输出被截断」（而非逻辑错误）。

    截断类错误的特征：报错指向文件末尾的未闭合结构，且代码本身很长。
    这类错误不该让模型"修补"，而应让它**用更精简的方式重写**——
    否则会把同样的超长代码再输出一次，再次截断（实测连续三次 syntax 失败就是这么来的）。
    """
    e = (err or "").lower()
    marks = ("was never closed", "unexpected eof", "eof while scanning",
             "unterminated string", "expected an indented block")
    return any(m in e for m in marks) and len(code) > 6000


def _execution_diagnostic(stderr: str, stdout: str) -> str:
    """Keep both the exception and the printed failing check within prompt budget."""
    error=(stderr or "").strip()
    output=(stdout or "").strip()
    return ("【标准错误】\n" + (error[-900:] or "stderr 为空。")
            + "\n【标准输出中的诊断】\n" + (output[-1400:] or "未记录标准输出。"))


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
0. **若这次失败是因为输出被截断**（报错在文件末尾、结构未闭合）：不要修补，
   请**重写一份更精简的完整代码**——聚焦最小可运行路径（<=200 行），
   删掉次要的分析分支并用 `# TODO:` 标注，确保能跑通再说；
1. 若是逻辑错误，只改必要的部分，保持原有逻辑与分析目标；
2. 若错误是缺少第三方库，改用标准库或已装库实现（不要 import 未安装的包）；
3. 若错误与数据/维度/类型有关，做相应检查与兜底；
   标准输出中为 False 的检查是定位依据。CSV 会推断数值类型；若契约规定浮点类型，
   在读取时显式指定 dtype，并独立按约定容差校验数值。不得删除验收或硬编码通过；
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
                       stdout: str, files: list[str], *, artifact_paths: list[pathlib.Path] | None = None,
                       input_paths: list[pathlib.Path] | None = None) -> list[dict[str, Any]]:
    """用技能的验收清单逐条核对产物（技能契约的落地环节）。"""
    if skill is None or not skill.verification:
        return []
    from .checks import parse_assertions
    from .contracts import file_evidence
    items = [v for v in skill.verification if not parse_assertions([v])]
    if not items:
        return []
    prompt = f"""下面是某一研究步骤的**产物**，请对照该技能的验收清单逐条判定是否满足。

任务：{task}
步骤：{action}
技能：{skill.name}

验收清单：
{chr(10).join(f'{i}. {v}' for i, v in enumerate(items, 1))}

产出的代码：
```python
{code}
```

运行输出：
{stdout[-6000:]}

落盘文件：{', '.join(files) if files else '（无）'}
实际产物证据（由服务端读取，截取部分会注明）：
{json.dumps(file_evidence(artifact_paths or []), ensure_ascii=False)}
上游原始文件事实（独立读取已登记版本，而非代码里的重算结果）：
{json.dumps(file_evidence(input_paths or []), ensure_ascii=False)}
本步骤职责：{json.dumps(getattr(skill, 'contract_scope', {}), ensure_ascii=False)}

判定要求：
- 每条给出 passed(true/false)、state(passed/failed/unknown/not_applicable)、evidence（引用具体证据）；
- 无法判断时 state=unknown；只有证据明确违反要求才是 failed。属于其它步骤职责的要求为 not_applicable。
- 不要把字符串扫描器自身、注释或字符串常量中的敏感词误判成实际函数调用；要核对调用表达式。
- 不要只因代码里存在 savefig 就认定图片内容正确；未提供视觉证据时不能臆测。
- 数值一致性必须对照实际输入与输出；两边同时 round 后得到零偏差不证明原值一致，不得放宽契约容差。

严格输出如下 JSON（顶层键名必须是 checks，不要改名）：
{{"checks": [{{"item": "清单条目原文", "passed": true, "state": "passed", "evidence": "证据"}}]}}"""

    obj = llm.chat_json(
        [{"role": "system", "content": "你是严格的科研产物验收员，只依据给定材料判定，输出 JSON。"},
         {"role": "user", "content": prompt}],
        role="judge", temperature=0.0, max_tokens=min(6000, max(1500, len(items) * 220)),
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
    by_item = {str(c.get('item')): c for c in (checks or []) if isinstance(c, dict)} if isinstance(checks, list) else {}
    out: list[dict[str, Any]] = []
    for item in items:
        c = by_item.get(item, {})
        state = c.get('state')
        if state not in ('passed', 'failed', 'unknown', 'not_applicable'):
            state = 'passed' if c.get('passed') is True else 'failed' if c.get('passed') is False else 'unknown'
        if state == 'passed' and c.get('passed') is not True:
            state = 'unknown'
        out.append(dict(item=item, passed=state in ('passed', 'not_applicable'), state=state,
                        evidence=str(c.get('evidence') or '验收未返回此条证据')[:500]))
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
                 {"role": "user", "content": _fix_prompt(code, _execution_diagnostic(
                     attempts[-1]["stderr"], attempts[-1]["stdout"]), skill, i, mode)}],
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

    has_vf = bool(getattr(skill, "verification", None)) if skill is not None else False
    if not result.get("ok"):
        verify_skip = "执行未成功，无法进行产物验收"
    elif mode != "contract":
        verify_skip = "该模式未启用技能契约，无验收标准"
    elif not has_vf:
        verify_skip = "该技能未定义 verification 清单"
    else:
        verify_skip = ""

    exec_record = _record_execution(skill, task, step, result, attempts)

    return {
        "exec_record": exec_record,
        "skill_exec_stats": ({k: v for k, v in (getattr(skill, "stats", {}) or {}).items()
                              if k.startswith("exec_")} if skill is not None else {}),
        "verify_skip_reason": verify_skip,
        "has_verification": has_vf,
        "skill": getattr(skill, "name", None),
        "action": step.get("action", ""),
        "code": code,
        "final_ok": bool(result.get("ok")),
        "attempts": attempts,
        "n_attempts": len(attempts),
        # fixed 必须表示「修复之后真的成功了」——早先只看 len(attempts)>1，
        # 导致三次全失败也被前端描述成「修复后成功」（实测暴露的文案错误）。
        "fixed": len(attempts) > 1 and bool(result.get("ok")),
        "exhausted": (not result.get("ok")) and len(attempts) > 1,
        "truncated": bool(attempts) and _looks_truncated(attempts[-1].get("stderr", ""), code),
        "stdout": result.get("stdout", "")[-4000:],
        "artifacts": result.get("artifacts", []),
        "verification": checks,
        "verification_passed": passed,
        "verification_total": len(checks),
        "workdir": str(workdir),
        "mode": mode,
    }


def _record_execution(skill: Any, task: str, step: dict[str, Any],
                      result: dict[str, Any], attempts: list[dict[str, Any]],
                      dest: pathlib.Path | None = None) -> dict[str, Any]:
    """把执行结果记到技能身上，并把失败样本归档。

    为什么必须做：执行失败率是**技能质量的直接信号**——某个技能反复执行失败，
    说明它的 steps 描述不够可执行、或 pitfalls 没覆盖真实坑点。这些数据此前
    只存在于本次请求的内存里，用完即弃，无法反哺技能改进。

    记账字段（写入 skill.stats，与既有 pulls/reward_sum 并存）：
      exec_total / exec_ok / exec_fix / exec_fail —— 执行统计
      exec_last_error —— 最近一次失败的错误类型（供质量评估与人工排查）
    """
    import json as _json
    from . import config as _cfg

    stats = getattr(skill, "stats", None) if skill is not None else None
    ok = bool(result.get("ok"))
    if isinstance(stats, dict):
        stats["exec_total"] = stats.get("exec_total", 0) + 1
        stats["exec_ok"] = stats.get("exec_ok", 0) + (1 if ok else 0)
        if len(attempts) > 1:
            stats["exec_fix"] = stats.get("exec_fix", 0) + (1 if ok else 0)
        if not ok:
            stats["exec_fail"] = stats.get("exec_fail", 0) + 1
            stats["exec_last_error"] = str(result.get("error_kind") or "unknown")

    record = {
        "skill": getattr(skill, "name", None),
        "task": task[:200],
        "action": str(step.get("action", ""))[:200],
        "ok": ok,
        "n_attempts": len(attempts),
        "error_kind": result.get("error_kind") or "",
        "stderr_tail": (result.get("stderr") or "")[-400:],
        "code_chars": len(result.get("stdout") or "") + 0,
    }
    # 归档：成功的也留一条（用于统计成功率），失败的带完整错误尾巴
    try:
        d = pathlib.Path(dest) if dest else (_cfg.OUT_DIR / "exec_log")
        d.mkdir(parents=True, exist_ok=True)
        f = d / "executions.jsonl"
        with f.open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass                                  # 归档失败绝不影响主链路
    return record


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
