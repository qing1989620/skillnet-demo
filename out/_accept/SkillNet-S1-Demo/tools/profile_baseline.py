# -*- coding: utf-8 -*-
"""profile_baseline.py —— 记录一次真实闭环的端到端耗时与成本（baseline 数据）。

用途：为「性能优化」提供 before 数据。当前 /api/demo 不返回分阶段耗时，
因此本脚本只能测端到端总时长 + token + 成本；分阶段耗时需要在 Run Runtime
中补齐（属重构任务）。
"""
import json, sys, time, urllib.request

BASE = "http://127.0.0.1:8848"
TASKS = [
    "我有一批不同剂量下的细胞存活率数据，想估计 IC50 并检查数据质量",
    "分析一份含缺失值的表格数据，建立基线预测模型并做误差分析",
    "对两组实验数据做统计检验，报告效应量与置信区间",   # 偏纯统计，可能不触发沙箱
]

out = []
for i, task in enumerate(TASKS, 1):
    body = json.dumps({"task": task, "gold": [], "k": 5}).encode()
    req = urllib.request.Request(f"{BASE}/api/demo", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=600))
        ms = int((time.time() - t0) * 1000)
        sb = (d["stages"][4] or {}).get("detail") or {}
        rec = {
            "task": task[:40], "total_ms": ms,
            "cost_yuan": d.get("cost_yuan"), "tokens": d.get("tokens"),
            "n_stages": len(d.get("stages") or []),
            "sandbox_ok": sb.get("final_ok"), "sandbox_attempts": sb.get("n_attempts"),
            "sandbox_ms": int(sum(a.get("duration", 0) for a in (sb.get("attempts") or [])) * 1000),
            "artifacts": len((d["stages"][6]["detail"] or {}).get("artifacts") or []),
            "declared": (d["stages"][6]["detail"] or {}).get("declared"),
            "generated": (d["stages"][6]["detail"] or {}).get("generated"),
            "usage_by_role": d.get("usage_by_role"),
        }
    except Exception as exc:
        rec = {"task": task[:40], "error": str(exc)[:200], "total_ms": int((time.time()-t0)*1000)}
    out.append(rec)
    print(json.dumps(rec, ensure_ascii=False))

tot = [r for r in out if "total_ms" in r and "error" not in r]
if tot:
    ms = sorted(r["total_ms"] for r in tot)
    cost = sum(r.get("cost_yuan") or 0 for r in tot)
    tok = sum(r.get("tokens") or 0 for r in tot)
    print(f"\n汇总：n={len(tot)} 总时长 p50={ms[len(ms)//2]}ms max={ms[-1]}ms "
          f"| 平均成本 ¥{cost/len(tot):.4f} | 平均 tokens {tok//len(tot)}")
    print(f"沙箱成功 {sum(1 for r in tot if r.get('sandbox_ok'))}/{len(tot)}")
    print("按角色 token 分账：", json.dumps(tot[-1].get("usage_by_role"), ensure_ascii=False))
json.dump(out, open("out/baseline/profile.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
