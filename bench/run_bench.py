"""对照实验：验证「技能网络 + 检索 + 强化学习 + 进化」对科研 Agent 的实际增益。

三组实验（对标文献）：
  retrieval   技能检索与编排能力          —— SkillNet-Gym 表 3 / Fabric 表 5
  execution   技能对执行质量与成本的影响   —— SkillNet 表 1 / DisCo
  evolution   老虎机选择 + 技能进化闭环    —— COBRA-Skills 表 4 / 图 4

用法：
    python bench/run_bench.py retrieval  --limit 20
    python bench/run_bench.py execution  --limit 12
    python bench/run_bench.py evolution  --limit 6 --rounds 5
    python bench/run_bench.py all
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillnet import config, llm  # noqa: E402
from skillnet.agent import ResearchAgent, STYLE_BARE, STYLE_CARDS, STYLE_GUIDED  # noqa: E402
from skillnet.bandit import LinUCB, RandomSelector  # noqa: E402
from skillnet.catalog import SkillLibrary, build_seed_skills  # noqa: E402
from skillnet.evolver import SkillEvolver  # noqa: E402
from skillnet.judge import reference_points_from_skills, score_plan  # noqa: E402
from skillnet.orchestrator import Orchestrator  # noqa: E402
from skillnet.retriever import Retriever, gold_overlap  # noqa: E402

DATASETS = {
    "dev": ("tasks/benchmark.json", "dev-v1", "dev"),
    "heldout": ("tasks/heldout.json", "heldout-v1", "heldout"),
}


def load_tasks(dataset: str = "dev") -> list[dict]:
    """按数据集加载任务。

    dev 集用于调参，可以反复看；heldout 集已冻结，
    只应被用于产出最终结果，**不得**据此调参。
    """
    rel, _ver, _split = DATASETS[dataset]
    path = ROOT / rel
    if not path.exists():
        raise SystemExit(f"数据集不存在：{path}")
    return json.loads(path.read_text(encoding="utf-8"))["tasks"]


TASKS = load_tasks("dev")   # 兼容旧引用（默认 dev）


def load_lib() -> SkillLibrary:
    return SkillLibrary(build_seed_skills())


def banner(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72, flush=True)


def _std(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def paired_bootstrap(
    a: list[float], b: list[float], *, n_boot: int = 4000, seed: int = 17
) -> dict[str, Any]:
    """配对 bootstrap：均值差的 95% 置信区间。

    为什么用配对：两组跑的是同一批任务、同一顺序，逐轮可以配成对。
    配对后任务难度被消掉，只剩「同一任务下两个策略谁更好」的差异，
    比直接比两个独立均值灵敏得多。

    为什么必须给区间而不是只给点估计：本项目 exp3 只有 6 轮，
    0.02 量级的均值差完全在噪声范围内。只看点估计会得出
    「LinUCB 赢了」或「随机赢了」这种随运行方向翻转的结论 ——
    上一版就出现过两次运行结论相反的情况。

    判定规则：区间跨 0 → 不能宣称任何一方更好。
    """
    import random as _random

    n = min(len(a), len(b))
    if n == 0:
        return {"n": 0, "verdict": "insufficient_data"}
    diffs = [a[i] - b[i] for i in range(n)]
    rng = _random.Random(seed)
    means = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += diffs[rng.randrange(n)]
        means.append(s / n)
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    obs = sum(diffs) / n
    contains_zero = lo <= 0.0 <= hi
    return {
        "n": n,
        "n_boot": n_boot,
        "mean_diff": round(obs, 4),
        "ci95": [round(lo, 4), round(hi, 4)],
        "contains_zero": contains_zero,
        "verdict": "indistinguishable" if contains_zero else "distinguishable",
    }


def _dump(name: str, payload: dict) -> str:
    p = config.OUT_DIR / f"{name}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(p)


# ======================================================================
# 实验一：技能检索与编排
# ======================================================================
def exp_retrieval(limit: int, k: int, dataset: str = "dev") -> dict:
    banner("实验一 · 技能检索与编排（对标 SkillNet-Gym 表 3 / Fabric 表 5）")
    lib = load_lib()
    r = Retriever(lib).build()
    orch = Orchestrator(lib)
    tasks = load_tasks(dataset)[:limit]

    methods = ["bm25", "hybrid", "fabric"]
    agg = {
        m: {"recall": 0.0, "full": 0, "orch": 0.0, "orchestrated": 0, "n": 0} for m in methods
    }
    per_task = []

    for t in tasks:
        row = {"id": t["id"], "domain": t["domain"], "gold": t["gold"]}
        for m in methods:
            llm.LEDGER.reset()
            res = r.search(t["query"], k=k, mode=m)
            recall = gold_overlap(res.selected, t["gold"])
            full = int(set(t["gold"]).issubset(set(res.selected)))
            entry = {
                "selected": res.selected,
                "recall": round(recall, 4),
                "full": bool(full),
                "cost_yuan": round(llm.LEDGER.cost_yuan, 5),
                "trace": res.trace,
            }
            # 编排：在选中技能上推导工作流
            wf = orch.build_from_relations(res.selected)
            comp = Orchestrator.completeness(wf["workflow"], t["workflow"])
            entry["workflow"] = wf["workflow"]
            entry["orchestration"] = round(comp, 4)
            row[m] = entry

            a = agg[m]
            a["recall"] += recall
            a["full"] += full
            a["orch"] += comp
            a["orchestrated"] += 1
            a["n"] += 1
            print(
                f"  [{t['id']}] {m:6s} recall={recall:.2f} full={full} "
                f"orch={comp:.2f} -> {res.selected[:3]}"
            )
        per_task.append(row)

    summary = {
        m: {
            "skill_recall": round(v["recall"] / max(1, v["n"]), 4),
            "full_coverage_rate": round(v["full"] / max(1, v["n"]), 4),
            "orchestration_completeness": round(v["orch"] / max(1, v["orchestrated"]), 4),
            "n_tasks": v["n"],
        }
        for m, v in agg.items()
    }
    print("\n汇总：")
    for m, v in summary.items():
        print(
            f"  {m:8s} 检索召回 {v['skill_recall']:.1%} | 完全覆盖 {v['full_coverage_rate']:.1%} "
            f"| 编排完整度 {v['orchestration_completeness']:.1%}"
        )
    payload = {
        "experiment": "retrieval",
        "dataset": "dev-v1",
        "split": "dev",
        "k": k,
        "n_tasks": len(tasks),
        "summary": summary,
        "per_task": per_task,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _dump(f"exp1_retrieval_{dataset}", payload)
    return payload


# ======================================================================
# 实验二：技能对执行质量与成本的影响
# ======================================================================
def exp_execution(limit: int, k: int, repeats: int = 2, dataset: str = "dev") -> dict:
    banner("实验二 · 技能对执行质量的影响（对标 SkillNet 表 1 / DisCo）")
    lib = load_lib()
    r = Retriever(lib).build()
    agent = ResearchAgent(lib)
    tasks = load_tasks(dataset)[:limit]

    arms = [
        ("bare", STYLE_BARE, None),          # 不给技能
        ("cards", STYLE_CARDS, "fabric"),    # 只给技能卡 L1 元数据
        ("hybrid", STYLE_GUIDED, "hybrid"),  # 混合检索 + 技能全文
        ("fabric", STYLE_GUIDED, "fabric"),  # 完整方案（关系扩展 + LLM 重排 + 全文）
    ]
    agg = {
        a[0]: {"score": 0.0, "cov": 0.0, "cov_n": 0, "adopt": 0.0, "adopt_n": 0,
               "cost": 0.0, "tokens": 0, "dims": {}, "runs": 0}
        for a in arms
    }
    rows = []

    for t in tasks:
        ref_pts = reference_points_from_skills(lib, t["gold"])
        row = {"id": t["id"], "domain": t["domain"], "n_reference_points": len(ref_pts)}
        for name, style, mode in arms:
            scores, covs, adop, costs, toks, dims, samples = [], [], [], [], [], {}, []
            for _ in range(repeats):
                llm.LEDGER.reset()
                skills = [] if mode is None else r.search(t["query"], k=k, mode=mode).selected
                run = agent.run(t["query"], skills=skills, style=style)
                j = score_plan(t["query"], run.response, ref_pts)
                scores.append(j["weighted"])
                if j["coverage"] is not None:
                    covs.append(j["coverage"])
                if skills:
                    adop.append(run.adoption)
                costs.append(llm.LEDGER.cost_yuan)
                toks.append(llm.LEDGER.prompt_tokens + llm.LEDGER.completion_tokens)
                for dk, dv in j["scores"].items():
                    dims[dk] = dims.get(dk, 0.0) + dv
                samples.append(
                    {"weighted": j["weighted"], "coverage": j["coverage"],
                     "adoption": round(run.adoption, 3) if skills else None,
                     "scores": j["scores"], "comment": j["comment"]}
                )
            avg = sum(scores) / len(scores)
            cov = sum(covs) / len(covs) if covs else None
            row[name] = {
                "skills": skills,
                "weighted": round(avg, 3),
                "score_std": round(_std(scores), 3),
                "coverage": round(cov, 4) if cov is not None else None,
                "adoption": round(sum(adop) / len(adop), 4) if adop else None,
                "runs": samples,
                "cost_yuan": round(sum(costs), 5),
                "tokens": int(sum(toks) / max(1, len(toks))),
            }
            a = agg[name]
            a["score"] += avg
            a["runs"] += 1
            if cov is not None:
                a["cov"] += cov
                a["cov_n"] += 1
            if adop:
                a["adopt"] += sum(adop) / len(adop)
                a["adopt_n"] += 1
            a["cost"] += sum(costs)
            a["tokens"] += row[name]["tokens"]
            for dk, dv in dims.items():
                a["dims"][dk] = a["dims"].get(dk, 0.0) + dv / len(scores)
            adopt_txt = f"{row[name]['adoption']:.0%}" if row[name]["adoption"] is not None else " — "
            print(
                f"  [{t['id']}] {name:7s} 得分 {avg:.2f} "
                f"覆盖 {('%.0f%%' % (cov * 100)) if cov is not None else 'n/a':>4s} "
                f"采纳 {adopt_txt:>4s} 成本 ¥{sum(costs):.4f}"
            )
        rows.append(row)

    n = max(1, len(tasks))
    summary = {}
    for name, a in agg.items():
        summary[name] = {
            "avg_score": round(a["score"] / max(1, a["runs"]), 3),
            "avg_coverage": round(a["cov"] / a["cov_n"], 4) if a["cov_n"] else None,
            "avg_adoption": round(a["adopt"] / a["adopt_n"], 4) if a["adopt_n"] else None,
            "avg_cost_yuan": round(a["cost"] / max(1, a["runs"]), 4),
            "avg_tokens": int(a["tokens"] / max(1, a["runs"])),
            "dim_avg": {k2: round(v / max(1, a["runs"]), 3) for k2, v in a["dims"].items()},
        }
    base_score = summary["bare"]["avg_score"]
    base_cov = summary["bare"]["avg_coverage"] or 0.0
    for name in summary:
        s = summary[name]
        s["gain_vs_bare"] = round(s["avg_score"] - base_score, 3)
        s["gain_pct"] = round((s["avg_score"] - base_score) / max(1e-6, base_score) * 100, 1)
        s["coverage_gain_pp"] = (
            round((s["avg_coverage"] - base_cov) * 100, 1) if s["avg_coverage"] is not None else None
        )

    # 配对比较：在同一任务内比，消除任务难度差异
    paired = {}
    for other in ("cards", "hybrid", "fabric"):
        wins = sum(1 for row in rows if row[other]["weighted"] > row["bare"]["weighted"])
        ties = sum(1 for row in rows if row[other]["weighted"] == row["bare"]["weighted"])
        cov_wins = sum(
            1 for row in rows
            if (row[other]["coverage"] or 0) > (row["bare"]["coverage"] or 0)
        )
        paired[other] = {
            "score_wins_vs_bare": wins,
            "score_ties_vs_bare": ties,
            "coverage_wins_vs_bare": cov_wins,
            "n": len(rows),
        }

    print("\n汇总：")
    for name, s in summary.items():
        cov = f"{s['avg_coverage']:.1%}" if s["avg_coverage"] is not None else "  n/a"
        ado = f"{s['avg_adoption']:.1%}" if s["avg_adoption"] is not None else "  n/a"
        print(
            f"  {name:8s} 均分 {s['avg_score']:.2f} | 要点覆盖 {cov} | 技能采纳 {ado} "
            f"| 相对基线 {s['gain_pct']:+.1f}% | 成本 ¥{s['avg_cost_yuan']:.4f}/任务"
        )
    print("\n配对比较（同任务内 vs 无技能基线）：")
    for k2, v in paired.items():
        print(
            f"  {k2:8s} 评分胜 {v['score_wins_vs_bare']}/{v['n']}，平 {v['score_ties_vs_bare']}，"
            f"覆盖胜 {v['coverage_wins_vs_bare']}/{v['n']}"
        )
    payload = {
        "experiment": "execution",
        "dataset": "dev-v1",
        "split": "dev",
        "k": k,
        "repeats": repeats,
        "n_tasks": len(tasks),
        "summary": summary,
        "per_task": rows,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _dump(f"exp2_execution_{dataset}", payload)
    return payload


# ======================================================================
# 实验三：老虎机选择 + 技能进化闭环
# ======================================================================
def exp_evolution(limit: int, rounds: int, k: int, alpha: float, dataset: str = "dev") -> dict:
    banner("实验三 · 老虎机选择 + 技能进化闭环（对标 COBRA-Skills 表 4 / 图 4）")
    lib = load_lib()
    r = Retriever(lib).build()
    agent = ResearchAgent(lib)
    orch = Orchestrator(lib)
    tasks = load_tasks(dataset)[:limit]

    results = {}
    for arm in ("linucb", "random"):
        llm.LEDGER.reset()
        # 每个 arm 从同一份种子库开始，保证可比
        arm_lib = SkillLibrary(build_seed_skills())
        arm_r = Retriever(arm_lib).build()
        arm_agent = ResearchAgent(arm_lib)
        evolver = SkillEvolver(arm_lib)
        selector = (
            LinUCB(arm_lib, alpha=alpha) if arm == "linucb" else RandomSelector(arm_lib)
        )
        print(f"\n--- arm = {arm} ---")
        curve = []
        for rd in range(1, rounds + 1):
            t = tasks[(rd - 1) % len(tasks)]
            cand = arm_r.search(t["query"], k=max(k, 4), mode="hybrid").selected
            extra = {n: {"retrieval": 1.0 - i / max(1, len(cand))} for i, n in enumerate(cand)}
            # v0.3：选择器是 task-conditioned 的，必须把任务传进去
            chosen, info = selector.select(t["query"], cand, extra=extra)
            if not chosen:
                continue
            run = arm_agent.run(t["query"], skills=[chosen], style=STYLE_GUIDED)
            j = score_plan(t["query"], run.response)
            reward = round(j["weighted"] / 10.0, 4)
            selector.update(t["query"], chosen, reward, extra.get(chosen))
            selector.log(rd, chosen, info.get("predicted_reward", 0.0), reward,
                         f"explore={info.get('exploration_bonus', 0.0):.3f}",
                         info.get("exploration_bonus", 0.0), t["query"])

            # 周期性技能进化（COBRA-Skills 的「不逐轮重写」）
            evolved = None
            if rd % 2 == 0:
                best = selector.best_by_actual(cand) or arm_lib.get(chosen)
                evolved = evolver.distill(
                    t["query"], run.trajectory, score=j["weighted"] / 10.0,
                    parent=[best.name] if best else [],
                )
                if evolved:
                    arm_r.refresh()
                    print(f"   round {rd}: 蒸馏出新技能 {evolved.name}（G{evolved.generation}）")

            curve.append(
                {
                    "round": rd,
                    "task": t["id"],
                    "chosen": chosen,
                    "reward": reward,
                    "predicted": info.get("predicted_reward", 0.0),
                    "explore": info.get("exploration_bonus", 0.0),
                    "score": j["weighted"],
                    "evolved": evolved.name if evolved else None,
                }
            )
            print(
                f"   round {rd}/{rounds} 任务{t['id']} 选择 {chosen:32s} "
                f"实测 {j['weighted']:.2f}/10"
            )

        best = selector.best_by_actual([s.name for s in arm_lib])
        rewards = [c["reward"] for c in curve]
        results[arm] = {
            "curve": curve,
            "mean_reward": round(sum(rewards) / max(1, len(rewards)), 4),
            "std": round(_std(rewards), 4),
            "n_rounds": len(rewards),
            "best_skill": best.name if best else None,
            "best_mean_reward": round(best.mean_reward, 4) if best else 0.0,
            "library_size": len(arm_lib),
            "evolved_skills": [
                {"name": s.name, "source": s.source, "generation": s.generation}
                for s in arm_lib if s.source != "seed"
            ],
            "selector": selector.snapshot(),
            "evolver": evolver.summary(),
            "cost_yuan": round(llm.LEDGER.cost_yuan, 4),
            "tokens": llm.LEDGER.prompt_tokens + llm.LEDGER.completion_tokens,
        }

    # ---- 统计检验：不给点估计就下结论 ----
    stats: dict[str, Any] = {"test": "paired_bootstrap", "alpha": 0.05}
    if "linucb" in results and "random" in results:
        ra = [c["reward"] for c in results["linucb"]["curve"]]
        rb = [c["reward"] for c in results["random"]["curve"]]
        stats.update(paired_bootstrap(ra, rb))
        if stats.get("verdict") == "indistinguishable":
            stats["conclusion"] = (
                "两组在 95% 置信区间上不可区分。本实验仅验证「选择→执行→奖励→更新→进化」"
                "闭环可运行，不构成「选择策略优于随机」的证据。"
            )
        else:
            stats["conclusion"] = (
                "本次运行两组差异落在 95% 区间之外，但轮次与任务数都很少，"
                "需重复实验与更多任务复核后才可下结论。"
            )
        stats["evidence_level"] = "preliminary"

    print("\n汇总（均值 ± 标准差）：")
    for arm, v in results.items():
        print(
            f"  {arm:8s} {v['mean_reward']:.3f} ± {v['std']:.3f} | 最佳技能 {v['best_skill']} "
            f"({v['best_mean_reward']:.3f}) | 库规模 {v['library_size']} | 成本 ¥{v['cost_yuan']:.3f}"
        )
    print("\n统计检验（配对 bootstrap，4000 次重采样）：")
    if stats.get("mean_diff") is not None:
        print(f"  均值差 {stats['mean_diff']:+.4f}  95% CI [{stats['ci95'][0]:+.4f}, {stats['ci95'][1]:+.4f}]"
              f"  → {stats['verdict']}")
    print(f"  {stats.get('conclusion', 'n/a')}")
    payload = {
        "experiment": "evolution",
        "dataset": "dev-v1",
        "split": "dev",
        "statistics": stats,
        "rounds": rounds,
        "n_tasks": len(tasks),
        "alpha": alpha,
        "results": results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _dump(f"exp3_evolution_{dataset}", payload)
    return payload


# ======================================================================
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["retrieval", "execution", "evolution", "all"])
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--alpha", type=float, default=0.1)
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--dataset", choices=["dev", "heldout"], default="dev",
                    help="dev=调参用；heldout=冻结测试集，只用于产出最终结果")
    args = ap.parse_args()

    t0 = time.time()
    if args.mode in ("retrieval", "all"):
        exp_retrieval(args.limit, args.k, args.dataset)
    if args.mode in ("execution", "all"):
        exp_execution(args.limit, args.k, args.repeats, args.dataset)
    if args.mode in ("evolution", "all"):
        exp_evolution(min(args.limit, 8), args.rounds, args.k, args.alpha, args.dataset)
    print(f"\n全部完成，用时 {time.time() - t0:.1f}s，产物见 {config.OUT_DIR}")


if __name__ == "__main__":
    main()
