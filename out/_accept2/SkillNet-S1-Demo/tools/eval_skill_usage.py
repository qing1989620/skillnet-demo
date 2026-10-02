# -*- coding: utf-8 -*-
"""Experiment B — Skill Usage（当前库 · FINALIZATION 核心实验）。

同一任务、同一模型、同一步骤数，只改「技能怎么被用起来」：
  none     不给任何技能
  prompt   技能以纯文本塞进提示词
  contract 技能契约模式（能力卡 + 陷阱 + verification）

指标：执行成功 / 尝试次数 / 程序化验收通过数 / 输出信息量 / 成本 / 时延。
每个任务×模式用独立 ledger_scope（成本互不串账）。
结果写入 out/bench/skill_usage_<ts>.json，manifest 锁定当前库。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillnet import config, llm, pipeline            # noqa: E402
from skillnet.catalog import SkillLibrary             # noqa: E402
from skillnet.retriever import Retriever              # noqa: E402
from skillnet.runtime import Run, RunStep, new_run_id  # noqa: E402

N_TASKS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
MODES = ("none", "prompt", "contract")


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def main() -> None:
    lib = SkillLibrary.load()
    retr = Retriever(lib).build()
    tasks = json.loads((ROOT / "tasks" / "benchmark.json").read_text(encoding="utf-8"))["tasks"][:N_TASKS]

    rows = []
    for t in tasks:
        # 选技能：fabric 检索 Top-1（带 LLM 重排，与生产主链路一致）
        res = retr.search(t["query"], k=5, mode="fabric")
        skill_name = (res.selected or [None])[0]
        skill_name = getattr(skill_name, "name", skill_name)
        for mode in MODES:
            led = llm.UsageLedger()
            run = Run(run_id=new_run_id(f"evB-{mode}"), task=t["query"], task_fp=f"evB")
            step = RunStep(idx=0, action=(t.get("steps") or ["完成该任务"])[0] if isinstance(t.get("steps"), list) and t.get("steps") else t["query"],
                           skill=skill_name if mode != "none" else None)
            ws = ROOT / "out" / "bench" / "ws" / f"{t['id']}-{mode}"
            t0 = time.perf_counter()
            try:
                with llm.ledger_scope(led):
                    pipeline.run_step(run, step, lib, ws, run.budget, [], max_attempts=3, mode=mode)
                ok = step.status == "done"
            except Exception as exc:                      # 单格失败不拖垮实验
                ok = False
                step.error = f"{type(exc).__name__}: {exc}"
            dur = time.perf_counter() - t0
            checks_p = sum(1 for c in step.checks if c.passed)
            out_chars = sum(len(a.stdout or "") for a in step.attempts)
            rows.append({
                "task_id": t["id"], "mode": mode, "skill": skill_name,
                "ok": ok, "attempts": step.n_attempts, "checks_passed": checks_p,
                "checks_total": len(step.checks),
                "out_chars": out_chars,
                "cost_yuan": round(float(led.cost_yuan), 4),
                "latency_s": round(dur, 1),
                "error": (step.error or "")[:120],
            })
            print(f"[{t['id']}] {mode:8s} ok={ok} try={step.n_attempts} "
                  f"checks={checks_p}/{len(step.checks)} ¥{led.cost_yuan:.4f} {dur:.0f}s")

    def agg(mode):
        rs = [r for r in rows if r["mode"] == mode]
        n = len(rs) or 1
        return {"success_rate": round(sum(r["ok"] for r in rs) / n, 3),
                "avg_attempts": round(sum(r["attempts"] for r in rs) / n, 2),
                "repair_rate": round(sum(1 for r in rs if r["attempts"] > 1 and r["ok"]) / n, 3),
                "avg_checks_passed": round(sum(r["checks_passed"] for r in rs) / n, 2),
                "avg_out_chars": round(sum(r["out_chars"] for r in rs) / n),
                "avg_cost": round(sum(r["cost_yuan"] for r in rs), 4),
                "avg_latency_s": round(sum(r["latency_s"] for r in rs) / n, 1), "n": len(rs)}

    out = {"manifest": {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": _git_commit(),
        "skill_count": len(lib), "evolved_count": sum(1 for s in lib if s.source != "seed"),
        "library_hash": _sha(config.LIBRARY_FILE),
        "dataset": "tasks/benchmark.json", "n_tasks": len(tasks),
        "model": config.MODEL, "max_attempts": 3, "skill_selection": "fabric-top1",
    }, "summary": {m: agg(m) for m in MODES}, "rows": rows}
    dest = ROOT / "out" / "bench"
    dest.mkdir(parents=True, exist_ok=True)
    fp = dest / f"skill_usage_{time.strftime('%Y%m%d_%H%M%S')}.json"
    fp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n已写出", fp)
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
