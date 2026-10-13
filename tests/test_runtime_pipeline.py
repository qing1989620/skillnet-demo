# -*- coding: utf-8 -*-
"""runtime / checks / pipeline / API 的自动化测试（Round 2 要求）。

覆盖 Qing 指定的最低清单：
- runtime：状态转换、终态不可覆盖、僵尸恢复、历史不覆盖、预算超限、取消
- checks：合法 CSV / 非法 CSV / 缺列 / 坏 JSON / 无效 PNG / Python 语法 / 数值范围 / 未知断言
- pipeline：2 步依赖、产物传播、上游失败阻断下游、重试、部分完成（LLM 用 mock，确定性）
- API：创建 run / get run / 列表（需要服务运行，单独标记）
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillnet import checks, pipeline, runtime                    # noqa: E402
from skillnet.runtime import (                                    # noqa: E402
    BudgetExceeded, Run, RunStep, RunStore, check_budget, new_run_id,
    now_ms, task_fingerprint,
)


# ======================================================================
# runtime
# ======================================================================
def _mkrun(fp: str = "abc123", status: str | None = None) -> Run:
    r = Run(run_id=new_run_id(fp), task="测试任务", task_fp=fp)
    if status:
        r.status = status
    return r


@pytest.fixture(autouse=True)
def _fresh_llm_ledger():
    """每个测试前后重置进程级默认账本。

    账本是 contextvar 缺省回落的全局单例（见 llm.current_ledger）：任何先跑的
    测试若真实调了 LLM（如 fabric 重排），会把 run.llm_calls 顶到预算上限，
    让本文件的 pipeline 测试集体死于 BudgetExceeded（实测 41 > 40 毒死 4 个）。
    """
    from skillnet import llm as _llm

    _llm.LEDGER.reset()
    yield
    _llm.LEDGER.reset()


def test_run_id_unique_per_execution(tmp_path):
    """同一任务重复运行：task_fp 相同，run_id 不同（历史不覆盖）。"""
    a, b = _mkrun(), _mkrun()
    assert a.task_fp == b.task_fp
    assert a.run_id != b.run_id


def test_zombie_sweep_marks_non_terminal(tmp_path):
    """启动清扫：进程被杀留下的非终态 Run → INTERRUPTED；终态不受影响。"""
    store = RunStore(tmp_path)
    zombie = _mkrun(status="CREATED"); zombie.run_id = new_run_id("z1"); store.save(zombie)
    done = _mkrun(status="COMPLETED"); done.run_id = new_run_id("z2"); store.save(done)
    assert store.sweep_interrupted() >= 1
    z = store.load(zombie.run_id)
    assert z.status == "INTERRUPTED"
    assert store.load(done.run_id).status == "COMPLETED"   # 终态不被覆盖


def test_history_no_overwrite(tmp_path):
    """同指纹两次运行：落盘为两个文件，互相不覆盖。"""
    store = RunStore(tmp_path)
    r1, r2 = _mkrun(), _mkrun()
    r1.run_id = new_run_id("grp"); r2.run_id = new_run_id("grp")
    r1.status = "COMPLETED"; r2.status = "FAILED"
    store.save(r1); store.save(r2)
    assert store.load(r1.run_id).status == "COMPLETED"
    assert store.load(r2.run_id).status == "FAILED"


def test_terminal_state_cannot_be_overwritten_by_finalize(tmp_path):
    """终态不可被 finalize_status 覆盖（PARTIAL/FAILED 保留）。"""
    store = RunStore(tmp_path)
    r = _mkrun(status="PARTIAL")
    r.steps = [RunStep(idx=0, action="a", status="done"), RunStep(idx=1, action="b", status="failed")]
    store.save(r)
    loaded = store.load(r.run_id)
    assert pipeline.finalize_status(loaded) == "PARTIAL"


def test_budget_exceeded_on_cost(tmp_path):
    """预算：成本超限 → BudgetExceeded。"""
    r = _mkrun(); r.cost_yuan = 2.0; r.budget.max_cost_yuan = 1.0
    with pytest.raises(BudgetExceeded):
        check_budget(r)


def test_budget_exceeded_on_cancel(tmp_path):
    """取消：cancel_requested → BudgetExceeded（检查点退出）。"""
    r = _mkrun(); r.cancel_requested = True
    with pytest.raises(BudgetExceeded):
        check_budget(r)


def test_step_duration_survives_roundtrip(tmp_path):
    """步骤时间戳随 to_dict/_from_dict 往返保留（修复过：曾全部变 0ms）。"""
    store = RunStore(tmp_path)
    r = _mkrun()
    st = RunStep(idx=0, action="x", status="done")
    st.started_at_ms = 1000; st.ended_at_ms = 25915
    r.steps = [st]
    store.save(r)
    loaded = store.load(r.run_id)
    assert loaded.steps[0].duration_ms == 24915


# ======================================================================
# checks（L1 确定性 + L2 技能断言）
# ======================================================================
def _run_checks_on(files: dict[str, str], sandbox_ok=True, tmp_path=None):
    d = pathlib.Path(tmp_path) if tmp_path else pathlib.Path(tempfile.mkdtemp())
    paths = []
    for name, content in files.items():
        p = d / name
        p.write_text(content, encoding="utf-8")
        paths.append(p)
    sandbox = {"ok": sandbox_ok, "returncode": 0 if sandbox_ok else 1,
               "stdout": "x" * 100, "stderr": "", "artifacts": [
                   {"name": p.name, "path": str(p)} for p in paths]}
    out = checks.run_checks(paths, sandbox)
    return out


def test_check_valid_csv(tmp_path):
    out = _run_checks_on({"a.csv": "sample,score\nx1,0.5\nx2,0.7\n"}, tmp_path=tmp_path)
    names = {c["name"]: c["passed"] for c in out}
    assert any("可解析 CSV" in n and ok for n, ok in names.items())
    assert any("含数据行" in n and ok for n, ok in names.items())
    assert any("列数一致" in n and ok for n, ok in names.items())


def test_check_invalid_csv_inconsistent_columns(tmp_path):
    out = _run_checks_on({"bad.csv": "a,b\n1,2\n3\n"}, tmp_path=tmp_path)
    assert any("列数一致" in c["name"] and not c["passed"] for c in out)


def test_check_missing_columns_via_assertion(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    out = checks.checks_from_skill(["[csv_columns] sample,score"], [p])
    assert out and not out[0]["passed"]


def test_check_malformed_json(tmp_path):
    out = _run_checks_on({"x.json": "{not json"}, tmp_path=tmp_path)
    assert any("合法 JSON" in c["name"] and not c["passed"] for c in out)


def test_check_invalid_png(tmp_path):
    p = tmp_path / "broken.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\nGARBAGE")       # 头对、内容坏
    out = checks.check_image(p)
    assert any(not ok for _, ok, _ in out)


def test_check_python_syntax(tmp_path):
    d = pathlib.Path(tmp_path)
    good = d / "good.py"; good.write_text("import sys\nprint(1)\n", encoding="utf-8")
    bad = d / "bad.py"; bad.write_text("def f(:\n  pass\n", encoding="utf-8")
    rg = checks.check_python(good); rb = checks.check_python(bad)
    assert rg[0][1] is True and rb[0][1] is False


def test_check_numeric_range(tmp_path):
    d = pathlib.Path(tmp_path)
    p = d / "s.csv"; p.write_text("score\n0.1\n0.9\n1.5\n", encoding="utf-8")
    out = checks.check_numeric_ranges(p, {"score": (0.0, 1.0)})
    assert any(not ok for _, ok, _ in out)              # 1.5 越界


def test_unknown_assertion_ignored():
    """未知断言类型被忽略（不 crash、不产出检查）。"""
    assert checks.parse_assertions(["[unknown_thing] x"]) == []
    assert checks.checks_from_skill(["[unknown_thing] x"], []) == []


# ======================================================================
# pipeline（LLM 用 mock，确定性验证执行语义）
# ======================================================================
class _FakeLedger:
    cost_yuan = 0.05
    prompt_tokens = 100
    completion_tokens = 200

    def snapshot(self):
        return {"by_role": {"executor": {"calls": 1}}}


NL = chr(10)   # 用 chr(10) 构造换行：heredoc/转义层可能把 "\n" 写成 "/n"（实测踩过）
GOOD_STEP1 = ("```python" + NL
              + "import csv" + NL
              + 'with open("clean.csv","w",newline="",encoding="utf-8") as f:' + NL
              + "    w=csv.writer(f); w.writerow(['v']); w.writerow([1]); print('ok')" + NL
              + "```")
GOOD_STEP2 = ("```python" + NL
              + "import csv" + NL
              + 'rows=list(csv.reader(open("clean.csv",encoding="utf-8")))' + NL
              + 'print("rows", len(rows))' + NL
              + "```")
BAD_STEP = '```python\nx = [1,2\n```'


def _mock_llm(monkeypatch, code_seq):
    seq = list(code_seq)
    calls = {"n": 0}
    def fake_chat(messages, **kw):
        c = seq[min(calls["n"], len(seq) - 1)]
        calls["n"] += 1
        return c
    monkeypatch.setattr(pipeline.llm, "chat", fake_chat)
    return calls


def test_two_step_dependency_and_artifact_propagation(tmp_path, monkeypatch):
    """两步依赖：第 2 步的沙箱目录里**真的有**第 1 步的产物。"""
    store = RunStore(tmp_path / "runs")
    r = _mkrun("dep")
    plan = {"steps": [{"action": "产数据"}, {"action": "读数据做分析"}]}
    _mock_llm(monkeypatch, [GOOD_STEP1, GOOD_STEP2])
    pipeline.execute_run(r, None, tmp_path / "ws", plan, max_steps=2)
    pipeline.finalize_status(r)          # 终态唯一权威：execute_run 后必须 finalize（见 pipeline.py 注释）
    assert r.status == "COMPLETED"
    s1, s2 = r.steps[0], r.steps[1]
    assert s1.status == "done" and s2.status == "done"
    assert "clean.csv" in s2.inputs
    assert (tmp_path / "ws" / "artifacts" / "step1_clean.csv").exists()
    # 第 2 步的代码里真的引用了第 1 步的文件（文件系统级传播的证据）
    assert "clean.csv" in s2.code


def test_failed_upstream_blocks_downstream(tmp_path, monkeypatch):
    """上游失败 → 下游被标记 skipped（依赖链阻断），run 状态 PARTIAL/FAILED。"""
    store = RunStore(tmp_path / "runs")
    r = _mkrun("blk")
    plan = {"steps": [{"action": "第一步会失败"}, {"action": "依赖第一步的产物"}]}
    _mock_llm(monkeypatch, [BAD_STEP, BAD_STEP])       # 第 1 步两次都语法错
    pipeline.execute_run(r, None, tmp_path / "ws", plan, max_steps=2)
    pipeline.finalize_status(r)
    assert r.steps[0].status == "failed"
    assert r.steps[1].status == "skipped"
    assert r.status in ("FAILED", "PARTIAL")


def test_retry_then_success(tmp_path, monkeypatch):
    """重试：第 1 次失败、第 2 次成功 → step done 且 fixed=True。"""
    store = RunStore(tmp_path / "runs")
    r = _mkrun("retry")
    plan = {"steps": [{"action": "产数据并落盘"}]}
    _mock_llm(monkeypatch, [BAD_STEP, GOOD_STEP1])
    pipeline.execute_run(r, None, tmp_path / "ws", plan, max_steps=3)
    pipeline.finalize_status(r)
    s = r.steps[0]
    assert s.status == "done" and s.n_attempts == 2 and s.fixed
    assert r.status == "COMPLETED"


def test_partial_completion(tmp_path, monkeypatch):
    """部分完成：第一步成功、第二步失败 → run=PARTIAL，且第一步产物仍在。"""
    store = RunStore(tmp_path / "runs")
    r = _mkrun("part")
    plan = {"steps": [{"action": "产数据"}, {"action": "第二步写坏文件"}]}
    _mock_llm(monkeypatch, [GOOD_STEP1, BAD_STEP, BAD_STEP, BAD_STEP])
    pipeline.execute_run(r, None, tmp_path / "ws", plan, max_steps=2)
    pipeline.finalize_status(r)
    assert r.status in ("PARTIAL", "FAILED")
    assert r.steps[0].status == "done"
    # 第一步的产物在 workspace/artifacts 里保留（不被第二步失败抹掉）
    assert (tmp_path / "ws" / "artifacts" / "step1_clean.csv").exists()


def test_deterministic_checks_appear_in_step(tmp_path, monkeypatch):
    """L1 检查真实出现在步骤里（文件存在/非空/表头等）。"""
    store = RunStore(tmp_path / "runs")
    r = _mkrun("chk")
    plan = {"steps": [{"action": "产数据并落盘 clean.csv"}]}
    _mock_llm(monkeypatch, [GOOD_STEP1])
    pipeline.execute_run(r, None, tmp_path / "ws", plan, max_steps=1)
    names = [c.name for c in r.steps[0].checks]
    assert any("存在" in n for n in names)
    assert any("CSV" in n for n in names)


# ======================================================================

# ======================================================================
# DAG = Runtime 集成测试（Round 4：编排 workflow 必须成为权威执行图）
# ======================================================================
DAG_WORKFLOW = [["s-a", "s-b"], ["s-a", "s-c"], ["s-b", "s-d"], ["s-c", "s-d"]]

GOOD_A = ("```python" + NL + 'open("shared.csv","w",encoding="utf-8").write("v\\n1\\n")' + NL + "print('A ok')" + "```")
GOOD_B = ("```python" + NL + "import time" + NL + 'rows = open("shared.csv",encoding="utf-8").read()' + NL
          + "time.sleep(0.5)" + NL + 'open("out_b.csv","w",encoding="utf-8").write("b:"+rows)' + NL + "print('B ok')" + "```")
GOOD_C = ("```python" + NL + "import time" + NL + 'rows = open("shared.csv",encoding="utf-8").read()' + NL
          + "time.sleep(0.5)" + NL + 'open("out_c.csv","w",encoding="utf-8").write("c:"+rows)' + NL + "print('C ok')" + "```")
GOOD_D = ("```python" + NL + "import json" + NL + 'b = open("out_b.csv",encoding="utf-8").read()' + NL
          + 'c = open("out_c.csv",encoding="utf-8").read()' + NL
          + 'json.dump({"b": b, "c": c}, open("final.json","w",encoding="utf-8"))' + NL + "print('D ok')" + "```")


def _dag_plan():
    return {"steps": [
        {"action": "产共享数据", "skill": "s-a"},
        {"action": "分支B加工", "skill": "s-b"},
        {"action": "分支C加工", "skill": "s-c"},
        {"action": "汇总D", "skill": "s-d"},
    ]}


def test_dag_parallel_branch_and_artifact_flow(tmp_path, monkeypatch):
    """A→(B,C)→D：B/C 等 A、可并行、D 等全部上游、产物真实跨步传递。"""
    _mock_llm(monkeypatch, [GOOD_A, GOOD_B, GOOD_C, GOOD_D])
    r = _mkrun("dag")
    pipeline.execute_run(r, None, tmp_path / "ws", _dag_plan(),
                         max_steps=4, workflow=DAG_WORKFLOW)
    pipeline.finalize_status(r)
    s = r.steps
    assert r.status == "COMPLETED", r.error
    assert all(x.status == "done" for x in s)
    assert s[0].started_at_ms < s[1].started_at_ms      # A 先于 B/C
    assert s[0].started_at_ms < s[2].started_at_ms
    assert s[3].started_at_ms >= s[1].ended_at_ms       # D 等全部上游
    assert s[3].started_at_ms >= s[2].ended_at_ms
    assert (r.staged.get("max_concurrency") or 0) >= 2  # B/C 真并行
    assert r.staged.get("scheduler") == "dag-parallel"
    assert "shared.csv" in s[1].inputs and "shared.csv" in s[2].inputs
    assert "out_b.csv" in s[3].inputs and "out_c.csv" in s[3].inputs
    cp = r.staged.get("critical_path") or {}
    # A and D startup time varies by OS. Check the actual longest dependency
    # path instead of assuming a Windows-specific minimum wall-clock overhead.
    paths = [[0, 1, 3], [0, 2, 3]]
    durations = [max(0, x.ended_at_ms - x.started_at_ms) for x in s]
    assert cp.get("steps") in paths
    assert cp.get("ms") == max(sum(durations[i] for i in path) for path in paths)


def test_dag_critical_failure_blocks_all_downstream(tmp_path, monkeypatch):
    """DAG 中 A 失败 → B/C/D 全部 skipped（依赖链阻断），run 不谎报 COMPLETED。"""
    _mock_llm(monkeypatch, [BAD_STEP, BAD_STEP, BAD_STEP])
    r = _mkrun("dagf")
    pipeline.execute_run(r, None, tmp_path / "ws", _dag_plan(),
                         max_steps=4, workflow=DAG_WORKFLOW)
    pipeline.finalize_status(r)
    assert r.steps[0].status == "failed"
    assert all(x.status == "skipped" for x in r.steps[1:])
    assert r.status in ("FAILED", "PARTIAL")


def test_build_steps_workflow_mapping():
    """build_steps 直接消费编排边：A→(B,C)→D 的依赖映射正确、无环。"""
    steps = pipeline.build_steps(_dag_plan(), DAG_WORKFLOW)
    assert [st.depends_on for st in steps] == [[], [0], [0], [1, 2]]
    steps2 = pipeline.build_steps(_dag_plan(), None)     # 线性兜底不回归
    assert [st.depends_on for st in steps2] == [[], [0], [1], [2]]

# ======================================================================
# DAG = Runtime 集成测试（Round 4：编排 workflow 必须成为权威执行图）
# ======================================================================
DAG_WORKFLOW = [["s-a", "s-b"], ["s-a", "s-c"], ["s-b", "s-d"], ["s-c", "s-d"]]

GOOD_A = ("```python" + NL + 'open("shared.csv","w",encoding="utf-8").write("v\\n1\\n")' + NL + "print('A ok')" + "```")
GOOD_B = ("```python" + NL + "import time" + NL + 'rows = open("shared.csv",encoding="utf-8").read()' + NL
          + "time.sleep(0.5)" + NL + 'open("out_b.csv","w",encoding="utf-8").write("b:"+rows)' + NL + "print('B ok')" + "```")
GOOD_C = ("```python" + NL + "import time" + NL + 'rows = open("shared.csv",encoding="utf-8").read()' + NL
          + "time.sleep(0.5)" + NL + 'open("out_c.csv","w",encoding="utf-8").write("c:"+rows)' + NL + "print('C ok')" + "```")
GOOD_D = ("```python" + NL + "import json" + NL + 'b = open("out_b.csv",encoding="utf-8").read()' + NL
          + 'c = open("out_c.csv",encoding="utf-8").read()' + NL
          + 'json.dump({"b": b, "c": c}, open("final.json","w",encoding="utf-8"))' + NL + "print('D ok')" + "```")


def _dag_plan():
    return {"steps": [
        {"action": "产共享数据", "skill": "s-a"},
        {"action": "分支B加工", "skill": "s-b"},
        {"action": "分支C加工", "skill": "s-c"},
        {"action": "汇总D", "skill": "s-d"},
    ]}


def test_dag_parallel_branch_and_artifact_flow(tmp_path, monkeypatch):
    """A→(B,C)→D：B/C 等 A、可并行、D 等全部上游、产物真实跨步传递。"""
    _mock_llm(monkeypatch, [GOOD_A, GOOD_B, GOOD_C, GOOD_D])
    r = _mkrun("dag")
    pipeline.execute_run(r, None, tmp_path / "ws", _dag_plan(),
                         max_steps=4, workflow=DAG_WORKFLOW)
    pipeline.finalize_status(r)
    s = r.steps
    assert r.status == "COMPLETED", [(st.status, st.error, [c.to_dict() for c in st.checks if not c.passed]) for st in s]
    assert all(x.status == "done" for x in s)
    assert s[0].started_at_ms < s[1].started_at_ms      # A 先于 B/C
    assert s[0].started_at_ms < s[2].started_at_ms
    assert s[3].started_at_ms >= s[1].ended_at_ms       # D 等全部上游
    assert s[3].started_at_ms >= s[2].ended_at_ms
    assert (r.staged.get("max_concurrency") or 0) >= 2  # B/C 真并行
    assert r.staged.get("scheduler") == "dag-parallel"
    assert "shared.csv" in s[1].inputs and "shared.csv" in s[2].inputs
    assert "out_b.csv" in s[3].inputs and "out_c.csv" in s[3].inputs
    cp = r.staged.get("critical_path") or {}
    # A and D startup time varies by OS. Check the actual longest dependency
    # path instead of assuming a Windows-specific minimum wall-clock overhead.
    paths = [[0, 1, 3], [0, 2, 3]]
    durations = [max(0, x.ended_at_ms - x.started_at_ms) for x in s]
    assert cp.get("steps") in paths
    assert cp.get("ms") == max(sum(durations[i] for i in path) for path in paths)


def test_dag_critical_failure_blocks_all_downstream(tmp_path, monkeypatch):
    """DAG 中 A 失败 → B/C/D 全部 skipped（依赖链阻断），run 不谎报 COMPLETED。"""
    _mock_llm(monkeypatch, [BAD_STEP, BAD_STEP, BAD_STEP])
    r = _mkrun("dagf")
    pipeline.execute_run(r, None, tmp_path / "ws", _dag_plan(),
                         max_steps=4, workflow=DAG_WORKFLOW)
    pipeline.finalize_status(r)
    assert r.steps[0].status == "failed"
    assert all(x.status == "skipped" for x in r.steps[1:])
    assert r.status in ("FAILED", "PARTIAL")


def test_build_steps_workflow_mapping():
    """build_steps 直接消费编排边：A→(B,C)→D 的依赖映射正确、无环。"""
    steps = pipeline.build_steps(_dag_plan(), DAG_WORKFLOW)
    assert [st.depends_on for st in steps] == [[], [0], [0], [1, 2]]
    steps2 = pipeline.build_steps(_dag_plan(), None)     # 线性兜底不回归
    assert [st.depends_on for st in steps2] == [[], [0], [1], [2]]


def test_two_runs_concurrent_smoke(tmp_path):
    """并发 smoke：两个 Run 同时提交——工作区不串、状态互不污染（指令 31）。

    账本不串已由 ledger_scope 单测与 context 传播覆盖；这里验证
    DAG 调度器线程 + 外层线程并存时，两条 Run 都能完整收敛。
    """
    import threading
    from skillnet import llm as _llm

    seq_holder = {"n": 0}
    lock = threading.Lock()

    def fake_chat(messages, **kw):
        with lock:
            i = seq_holder["n"]
            seq_holder["n"] += 1
        code = GOOD_STEP1 if i % 2 == 0 else GOOD_STEP2
        return code

    orig = pipeline.llm.chat
    pipeline.llm.chat = fake_chat
    try:
        results = {}
        def one(tag):
            ws = tmp_path / f"ws-{tag}"
            r = _mkrun(tag)
            plan = {"steps": [{"action": "产数据"}, {"action": "读数据做分析"}]}
            pipeline.execute_run(r, None, ws, plan, max_steps=2)
            pipeline.finalize_status(r)
            results[tag] = r

        ths = [threading.Thread(target=one, args=(t,)) for t in ("A", "B")]
        for x in ths: x.start()
        for x in ths: x.join(60)
        assert set(results) == {"A", "B"}, "有 Run 未在时限内完成"
        for tag, r in results.items():
            assert r.status == "COMPLETED", (tag, r.status, r.error)
            assert (tmp_path / f"ws-{tag}" / "artifacts" / "step1_clean.csv").exists()
        # 两条 Run 的步骤状态互不污染
        assert all(s.status == "done" for s in results["A"].steps)
        assert all(s.status == "done" for s in results["B"].steps)
    finally:
        pipeline.llm.chat = orig


def test_two_runs_concurrent_smoke(tmp_path):
    """并发 smoke：两个 Run 同时提交——工作区不串、状态互不污染（指令 31）。

    账本不串已由 ledger_scope 单测与 context 传播覆盖；这里验证
    DAG 调度器线程 + 外层线程并存时，两条 Run 都能完整收敛。
    """
    import threading
    from skillnet import llm as _llm

    seq_holder = {"n": 0}
    lock = threading.Lock()

    def fake_chat(messages, **kw):
        with lock:
            i = seq_holder["n"]
            seq_holder["n"] += 1
        code = GOOD_STEP1 if i % 2 == 0 else GOOD_STEP2
        return code

    orig = pipeline.llm.chat
    pipeline.llm.chat = fake_chat
    try:
        results = {}
        def one(tag):
            ws = tmp_path / f"ws-{tag}"
            r = _mkrun(tag)
            plan = {"steps": [{"action": "产数据"}, {"action": "读数据做分析"}]}
            pipeline.execute_run(r, None, ws, plan, max_steps=2)
            pipeline.finalize_status(r)
            results[tag] = r

        ths = [threading.Thread(target=one, args=(t,)) for t in ("A", "B")]
        for x in ths: x.start()
        for x in ths: x.join(60)
        assert set(results) == {"A", "B"}, "有 Run 未在时限内完成"
        for tag, r in results.items():
            assert r.status == "COMPLETED", (tag, r.status, r.error)
            assert (tmp_path / f"ws-{tag}" / "artifacts" / "step1_clean.csv").exists()
        # 两条 Run 的步骤状态互不污染
        assert all(s.status == "done" for s in results["A"].steps)
        assert all(s.status == "done" for s in results["B"].steps)
    finally:
        pipeline.llm.chat = orig


def test_sandbox_chinese_output_and_artifact_names(tmp_path):
    """沙箱中文回归（用户实测踩过）：

    -I 隔离模式蕴含 -E，会丢弃 PYTHONIOENCODING —— 中文 Windows 下子进程
    stdout 落回 GBK，父进程按 UTF-8 解码即满屏乱码。修复后必须：
    ① 中文 print 原样可读；② 中文文件名产物被发现登记。"""
    from skillnet import sandbox
    code = ('print("模块: 2 个 (28.6%)")' + NL
            + 'print("评分算法: 2 项")' + NL
            + 'open("报告.csv","w",encoding="utf-8").write("章节,错题" + chr(10) + "数列,12")' + NL
            + 'print("已保存: 报告.csv")')
    res = sandbox.run_python(code, timeout=60, keep_dir=True,
                             workdir=tmp_path / "try1")
    assert res["ok"], res["stderr"]
    assert "模块: 2 个 (28.6%)" in res["stdout"]
    assert "评分算法: 2 项" in res["stdout"]
    assert "\ufffd" not in res["stdout"], "stdout 仍有替换符（编码断裂）"
    assert "报告.csv" in [a["name"] for a in res["artifacts"]]


def test_final_reply_prompt_carries_real_facts(tmp_path, monkeypatch):
    """Agent 最终回复（Codex 式收尾）的真实性约束：

    - prompt 必须携带真实运行事实（任务/技能/每步状态与尝试/产物/成本）；
    - 必须显式禁止编造数字与结论；
    - 失败/跳过要如实进入 prompt（不许粉饰）。"""
    import server
    from skillnet.runtime import Artifact, ExecutionAttempt

    captured = {}

    def fake_chat(messages, **kw):
        captured["messages"] = messages
        captured["kw"] = kw
        return "### 完成情况\n- 三步均已真实执行"

    monkeypatch.setattr(server.llm, "chat", fake_chat)
    r = _mkrun("reply")
    r.task = "对一批剂量-存活率数据做剂量反应分析"
    r.skills = ["s-a", "s-b"]
    s1 = RunStep(idx=0, action="产共享数据", skill="s-a", status="done")
    s1.attempts = [ExecutionAttempt(n=1, ok=True, stdout="ok", stderr="", error_kind="",
                                    duration_ms=900, truncated=False)]
    s1.artifacts = [Artifact(name="step1_shared.csv", kind="真实运行产物", bytes=2048,
                             sha256="x" * 8, from_step=0)]
    s2 = RunStep(idx=1, action="分支处理", skill="s-b", status="done")
    s2.attempts = [ExecutionAttempt(n=1, ok=False, stdout="", stderr="ValueError: bad",
                                    error_kind="exception", duration_ms=500, truncated=False),
                   ExecutionAttempt(n=2, ok=True, stdout="ok", stderr="", error_kind="",
                                    duration_ms=700, truncated=False)]
    r.steps = [s1, s2]
    r.artifacts = list(s1.artifacts)
    r.cost_yuan = 0.0512
    r.tokens = 3210
    r.started_at_ms = now_ms() - 12000          # duration_ms 是只读 property
    r.ended_at_ms = now_ms()
    r.judge = {"weighted": 8.2, "coverage": 0.75}

    text = server._compose_final_reply(r, None)
    assert text.startswith("###")
    assert captured["kw"].get("role") == "reporter"
    assert int(captured["kw"].get("max_tokens") or 0) >= 2000   # 详细回复需要足够输出空间
    assert int(captured["kw"].get("max_tokens") or 0) >= 2000   # 详细回复需要足够输出空间
    prompt = captured["messages"][1]["content"]
    assert "不得编造" in prompt or "禁止编造" in prompt
    for kw in ("剂量反应分析", "s-a", "s-b", "step1_shared.csv", "¥0.051", "3210",
               "自动修复", "8.2", "步骤结果", "不要在回复里写具体终态词",
               # 加法增强：回复必须带真实素材（否则只能写执行汇报，回答不了问题）
               "每步真实执行输出摘录", "产物内容摘录", "直接回答", "600~1500 字"):
        assert kw in prompt, f"prompt 缺少：{kw}" if kw in old else kw
    for kw in ("剂量反应分析", "s-a", "s-b", "step1_shared.csv", "¥0.051", "3210",
               "自动修复", "8.2", "步骤结果", "不要在回复里写具体终态词",
               # 加法增强：回复必须带真实素材（否则只能写执行汇报，回答不了问题）
               "每步真实执行输出摘录", "产物内容摘录", "直接回答", "600~1500 字"):
        assert kw in prompt, f"prompt 缺少：{kw}" if kw in old else kw
    for kw in ("剂量反应分析", "s-a", "s-b", "step1_shared.csv", "¥0.051", "3210",
               "自动修复", "8.2", "步骤结果", "不要在回复里写具体终态词"):
        assert kw in prompt, f"prompt 缺少真实事实：{kw}"

    # 失败步骤必须如实进入 prompt（不粉饰）
    r.steps[1].status = "failed"
    r.steps[1].error = "ValueError: 真实错误"
    prompt2 = server._compose_final_reply(r, None) and captured["messages"][1]["content"]
    assert "失败" in prompt2 and "真实错误" in prompt2
