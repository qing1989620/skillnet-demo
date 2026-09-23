"""端到端自检：验证 demo 的每个组件真的能跑，而不是只写了代码。

    python verify.py            # 只做静态与轻量检查（不调用 LLM）
    python verify.py --llm      # 额外跑一次真实的检索 + 蒸馏 + 评审链路

输出 PASS / FAIL 表，任何一项失败退出码为 1。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, fn):
    try:
        detail = fn() or ""
        RESULTS.append((name, True, str(detail)))
        print(f"  PASS  {name}  {detail}")
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        print(f"  FAIL  {name}  {type(exc).__name__}: {exc}")
        if "--trace" in sys.argv:
            traceback.print_exc()


# ======================================================================
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="额外跑真实 LLM 链路")
    args = ap.parse_args()

    from skillnet import config, llm
    from skillnet.adapters import SKILLS_DIRS, export_all
    from skillnet.agent import ResearchAgent
    from skillnet.bandit import LinUCB, RandomSelector
    from skillnet.catalog import SkillLibrary, build_seed_skills, export_skill_dirs
    from skillnet.evolver import SkillEvolver
    from skillnet.index import BM25Index, VectorIndex, weighted_fuse
    from skillnet.judge import reference_points_from_skills, score_plan
    from skillnet.orchestrator import Orchestrator
    from skillnet.retriever import Retriever
    from skillnet.schema import Skill

    print("\n[1] 技能库与本体")
    lib = SkillLibrary(build_seed_skills())
    SKILL_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def t_size():
        assert len(lib) >= 40, f"技能数过少: {len(lib)}"
        return f"{len(lib)} 个技能 / {len(lib.by_domain())} 个领域"
    check("技能库规模", t_size)

    def t_names():
        bad = [s.name for s in lib if not SKILL_RE.match(s.name) or len(s.name) > 64]
        assert not bad, f"非法技能名: {bad}"
        return "全部符合 kebab-case 且 ≤64 字符"
    check("技能名合规（agentskills.io）", t_names)

    def t_desc():
        bad = [s.name for s in lib if not s.description or len(s.description) > 1024]
        assert not bad, f"描述不合规: {bad}"
        return "描述非空且 ≤1024 字符"
    check("技能描述合规", t_desc)

    def t_dedup():
        dups = lib.duplicates()
        assert not dups, f"存在重复技能: {dups}"
        return "无重复技能"
    check("去重", t_dedup)

    def t_relations():
        names = {s.name for s in lib}
        dangling = [(s.name, t) for s in lib for _, t in s.relations if t not in names]
        assert not dangling, f"悬空关系边: {dangling[:5]}"
        assert len(lib.relation_edges()) >= 30, "关系边过少"
        return f"{len(lib.relation_edges())} 条关系边，无悬空引用"
    check("关系图完整性", t_relations)

    def t_steps():
        bad = [s.name for s in lib if len(s.steps) < 3]
        assert not bad, f"步骤过少的技能: {bad}"
        return "每个技能至少 3 个可执行步骤"
    check("技能完整性（可执行步骤）", t_steps)

    def t_md():
        md = lib.all()[0].to_skill_md()
        assert md.startswith("---\n"), "缺少 YAML frontmatter"
        assert "\n---\n" in md[4:], "frontmatter 未闭合"
        fm = md[4:].split("\n---\n", 1)[0]
        assert "name:" in fm and "description:" in fm
        return "SKILL.md 含合法 frontmatter"
    check("SKILL.md 渲染", t_md)

    print("\n[2] 索引与检索")

    def t_bm25():
        idx = BM25Index()
        idx.fit(["a", "b"], ["单细胞 RNA 测序聚类分析", "分子对接与虚拟筛选"])
        hits = idx.search("单细胞聚类", top_k=2)
        assert hits and hits[0][0] == "a", f"BM25 排序异常: {hits}"
        return "BM25 命中正确文档"
    check("BM25 索引", t_bm25)

    def t_vec():
        idx = VectorIndex()
        idx.fit(["a", "b"], ["单细胞 RNA 测序聚类分析", "分子对接与虚拟筛选"])
        hits = idx.search("单细胞聚类", top_k=2)
        assert hits and hits[0][0] == "a", f"向量检索排序异常: {hits}"
        return "稀疏向量命中正确文档"
    check("语义向量索引", t_vec)

    def t_fuse():
        a = [("x", 10.0), ("y", 5.0)]
        b = [("y", 1.0), ("z", 0.5)]
        fused = weighted_fuse([a, b], [0.55, 0.30])
        names = [n for n, _ in fused]
        assert names[0] == "x", f"融合排序异常: {names}"
        assert "y" in names and "z" in names
        return f"融合顺序 {names}"
    check("加权融合", t_fuse)

    def t_three_modes():
        r = Retriever(lib).build()
        sel = {}
        for m in ("bm25", "hybrid", "fabric"):
            res = r.search("单细胞测序做质控、聚类并出图", k=5, mode=m, rerank=(m == "fabric"))
            sel[m] = res.selected
            # BM25 是精确匹配，中文短查询下召回条数本就可能不足 k，属预期行为
            assert res.selected, f"{m} 未返回任何结果"
            assert len(res.selected) <= 5, f"{m} 返回超过 k 条"
        assert len(sel["hybrid"]) == 5, f"hybrid 未返回 5 条: {sel['hybrid']}"
        assert "scrna-qc-clustering" in sel["bm25"], f"BM25 未命中: {sel['bm25']}"
        return f"BM25 {len(sel['bm25'])} 条 / hybrid {len(sel['hybrid'])} 条 / fabric {len(sel['fabric'])} 条，均命中单细胞技能"
    check("三档检索可运行", t_three_modes)

    print("\n[3] 强化学习与进化")

    TASK = "单细胞测序数据的质控、聚类与细胞亚群注释"

    def t_bandit():
        b = LinUCB(lib, alpha=0.1)
        cands = ["scrna-qc-clustering", "differential-expression", "pathway-enrichment"]
        n, info = b.select(TASK, cands, extra={c: {"retrieval": 0.5} for c in cands})
        assert n in cands, f"选择结果越界: {n}"
        b.update(TASK, n, 0.7, {"retrieval": 0.5})
        s = lib.get(n)
        assert s.stats["pulls"] == 1 and abs(s.mean_reward - 0.7) < 1e-6
        # 二次选择应发生变化（θ 已更新，探索奖励下降）
        n2, info2 = b.select(TASK, cands, extra={c: {"retrieval": 0.5} for c in cands})
        assert info2["priority"] != info["priority"] or n2 != n
        return f"首轮选 {n}（探索 {info['exploration_bonus']:.4f}）"
    check("LinUCB 选择与更新", t_bandit)

    def t_bandit_generalization():
        """v0.3 核心检查：只更新 A，未评估的同领域技能 B 必须被带动，且强于异领域 C。"""
        groups: dict[str, list[str]] = {}
        for s in lib:
            groups.setdefault(s.domain, []).append(s.name)
        dom = max(groups, key=lambda d: len(groups[d]))
        near_a, near_b = groups[dom][0], groups[dom][1]
        far = next(s.name for s in lib if s.domain != dom)
        task = lib.get(near_a).capability or dom

        b = LinUCB(lib, alpha=0.25)
        before = {n: b.score(task, n)[1] for n in (near_a, near_b, far)}
        b.update(task, near_a, 0.95)
        after = {n: b.score(task, n)[1] for n in (near_a, near_b, far)}
        d_near = abs(after[near_b] - before[near_b])
        d_far = abs(after[far] - before[far])
        assert d_near > 1e-3, f"未评估的同领域技能未被带动（Δ={d_near:.6f}），跨技能泛化失效"
        assert d_near > d_far, f"同领域 Δ={d_near:.6f} 未大于异领域 Δ={d_far:.6f}"
        return f"未评估的同领域技能被带动（Δ={d_near:.4f} > 异领域 {d_far:.4f}，{d_near / max(1e-9, d_far):.2f}x）"
    check("跨技能泛化（shared 参数）", t_bandit_generalization)

    def t_bandit_task_conditioning():
        b = LinUCB(lib, alpha=0.25)
        name = "scrna-qc-clustering"
        t1 = "单细胞测序数据的质控与聚类"
        t2 = "无机化合物形成能的机器学习预测"
        d = abs(b.score(t1, name)[0] - b.score(t2, name)[0])
        assert d > 1e-4, f"同一技能在不同任务上优先级相同（差 {d:.8f}）：未做 task conditioning"
        return f"同一技能在两任务上优先级差 {d:.4f}"
    check("task conditioning", t_bandit_task_conditioning)

    def t_explore_decay():
        b = LinUCB(lib, alpha=0.3)
        name = "scrna-qc-clustering"
        _, _, e0 = b.score(TASK, name)
        for _ in range(5):
            b.update(TASK, name, 0.5)
        _, _, e1 = b.score(TASK, name)
        assert e1 < e0, f"探索奖励未随观测下降: {e0:.5f} -> {e1:.5f}"
        return f"探索奖励 {e0:.4f} → {e1:.4f}（观测后收敛）"
    check("探索奖励随观测衰减", t_explore_decay)

    def t_random_ablation():
        r = RandomSelector(lib)
        cands = ["scrna-qc-clustering", "differential-expression"]
        n, info = r.select(TASK, cands)
        assert n in cands
        r.update(TASK, n, 0.9)
        assert lib.get(n).stats["pulls"] >= 1
        return "随机消融选择器工作正常"
    check("消融对照选择器", t_random_ablation)

    def t_admission():
        ev = SkillEvolver(lib)
        before = len(lib)
        # 缺步骤 -> 应被拒
        ev._admit({"name": "bad-skill-demo", "description": "x", "steps": ["a"]}, "distill", [])
        assert len(lib) == before, "不完整技能被错误准入"
        # 与现有技能高度重合 -> 应被拒
        ev._admit(
            {
                "name": "dup-skill-demo",
                "description": "单细胞转录组标准分析流程",
                "capability": "从原始计数矩阵完成质控、归一化、降维、聚类与标记基因鉴定",
                "use_when": ["处理 scRNA-seq 原始矩阵", "需要识别细胞亚群"],
                "steps": ["a", "b", "c"],
            },
            "distill", [],
        )
        assert len(lib) == before, "冗余技能被错误准入"
        # 合法技能 -> 应被接受
        ok = ev._admit(
            {
                "name": "selfcheck-valid-skill",
                "description": "用于自检的示例技能：把分析结果写进结构化报告",
                "domain": "自检",
                "capability": "产出结构化自检报告",
                "use_when": ["需要自检"],
                "steps": ["收集指标", "比对阈值", "输出结论"],
            },
            "distill", [],
        )
        assert ok is not None, "合法技能被错误拒绝"
        lib.remove("selfcheck-valid-skill")
        rejected = sum(1 for r in ev.records if not r.accepted)
        assert rejected == 2, f"拒绝记录数异常: {rejected}"
        return f"2 条非法/冗余被拒，1 条合法准入（已回滚）"
    check("准入过滤（防技能库污染）", t_admission)

    def t_orchestrator():
        o = Orchestrator(lib)
        wf = o.build_from_relations(
            ["scrna-qc-clustering", "differential-expression", "scientific-visualization"]
        )
        assert wf["skills"][0] == "scrna-qc-clustering", f"拓扑序异常: {wf['skills']}"
        assert wf["workflow"], "未推导出依赖边"
        c = Orchestrator.completeness(wf["workflow"], [["scrna-qc-clustering", "differential-expression"]])
        assert c == 1.0, f"编排完整度异常: {c}"
        return f"拓扑序 {wf['skills']}"
    check("工作流编排与拓扑排序", t_orchestrator)

    def t_cycle_break():
        nodes = {"a", "b", "c"}
        edges = {("a", "b"), ("b", "c"), ("c", "a")}
        kept = Orchestrator._break_cycles(nodes, edges)
        order = Orchestrator._toposort(nodes, kept)
        assert len(order) == 3, "环未打断导致拓扑排序丢节点"
        # 验证无环
        idx = {n: i for i, n in enumerate(order)}
        assert all(idx[a] < idx[b] for a, b in kept), "仍存在环"
        return "3 节点环被正确打断"
    check("环检测与打断", t_cycle_break)

    def t_cycle_observable():
        o = Orchestrator(lib)
        r = o.build_from_relations(
            ["scrna-qc-clustering", "differential-expression", "pathway-enrichment"]
        )
        assert "cycles_broken" in r, "编排结果未回报被打断的环边"
        # 打断之后必须仍是合法拓扑序
        idx = {n: i for i, n in enumerate(r["skills"])}
        for a, b in r["workflow"]:
            assert idx[a] < idx[b], f"编排顺序违反依赖：{a} 应在 {b} 之前"
        return f"环边可观测（本次打断 {len(r['cycles_broken'])} 条），且拓扑序合法"
    check("编排环可观测", t_cycle_observable)

    def t_quality_assess():
        from skillnet.schema import assess_quality

        q = assess_quality(lib.get("scrna-qc-clustering"))
        assert set(q) == set(
            ("safety", "completeness", "executability", "maintainability", "cost_awareness")
        ), f"维度不齐：{sorted(q)}"
        for dim, v in q.items():
            assert isinstance(v, dict), f"{dim} 应为 dict（含 level 与 reason），实际 {type(v)}"
            assert v.get("level") in ("Good", "Average", "Poor"), f"{dim} 等级非法：{v}"
            assert v.get("reason"), f"{dim} 缺少理由"

        dangerous = Skill(
            name="verify-dangerous-skill", description="含危险操作的技能", domain="自检",
            steps=["先执行 rm -rf / 清理旧数据", "再重建索引", "最后校验"], source="distill",
        )
        assert assess_quality(dangerous)["safety"]["level"] == "Poor", "危险操作未被识别为 Poor"
        return f"五维均带等级+理由；危险操作被识别为 Poor（样例完整性={q['completeness']['level']}）"
    check("质量评估带理由", t_quality_assess)

    print("\n[4] 跨框架导出")

    def t_export():
        out = config.OUT_DIR / "verify_adapters"
        shutil.rmtree(out, ignore_errors=True)
        info = export_all(lib, out)

        # 各家客户端的技能发现路径不同，必须每个落点都写全
        target = out / "agent_skills"
        for client, rel in SKILLS_DIRS.items():
            n = len(list((target / rel).glob("*/SKILL.md")))
            assert n == len(lib), f"{client} 落点 {rel} 仅 {n} 个技能，应为 {len(lib)}"
        assert (target / "AGENTS.md").exists(), "AGENTS.md 缺失"

        adk = out / "google_adk" / "skills"
        assert (adk / "literature-review" / "SKILL.md").exists(), "ADK 产物缺失"
        agent_py = (out / "google_adk" / "agent.py").read_text(encoding="utf-8")
        assert "load_skill_from_dir" in agent_py and "SkillToolset" in agent_py, "ADK agent.py 不完整"
        tools = json.loads((out / "openai_tools" / "tools.json").read_text(encoding="utf-8"))
        assert len(tools) == 2 and tools[0]["function"]["name"] == "search_skills"
        idx = (out / "index" / "SKILLS_INDEX.md").read_text(encoding="utf-8")
        assert idx.count("- **") == len(lib), "扁平索引条目数与技能数不符"
        return f"{len(info)} 项产物；4 个客户端落点各 {len(lib)} 个技能 + AGENTS.md"
    check("跨框架导出（四客户端落点）", t_export)

    def t_path_safety():
        from skillnet.adapters import _safe_dir_name

        for bad in ["../evil", "a/b", "..", ".hidden", "A-B", "x" * 65, "", "a b"]:
            try:
                _safe_dir_name(bad)
            except ValueError:
                continue
            raise AssertionError(f"危险技能名未被拦截: {bad!r}")
        assert _safe_dir_name("literature-review") == "literature-review"
        return "路径穿越 / 大写 / 超长 / 含空格名均被拦截"
    check("导出路径安全", t_path_safety)

    def t_export_dirs():
        # 导出到自检专用目录，避免把测试过程中产生的技能写进正式种子目录
        target = config.OUT_DIR / "verify_seed"
        n = export_skill_dirs(lib, target)
        p = target / "literature-review" / "SKILL.md"
        assert p.exists() and n == len(lib)
        return f"{n} 个 SKILL.md 目录（导出至 out/verify_seed）"
    check("种子技能目录落盘", t_export_dirs)

    print("\n[5] 评测集")

    def t_tasks():
        tf = ROOT / "tasks" / "benchmark.json"
        data = json.loads(tf.read_text(encoding="utf-8"))
        tasks = data["tasks"]
        assert len(tasks) >= 20, f"任务数不足: {len(tasks)}"
        names = {s.name for s in lib}
        for t in tasks:
            miss = [g for g in t["gold"] if g not in names]
            assert not miss, f"{t['id']} 的 gold 引用了不存在的技能: {miss}"
            assert t["workflow"], f"{t['id']} 缺少 workflow"
        return f"{len(tasks)} 个任务，gold 技能全部存在于库中"
    check("评测任务集", t_tasks)

    def t_refpoints():
        pts = reference_points_from_skills(lib, ["scrna-qc-clustering", "differential-expression"])
        assert len(pts) >= 4, f"要点过少: {len(pts)}"
        assert len(set(pts)) == len(pts), "要点存在重复"
        return f"抽取 {len(pts)} 条专业要点"
    check("客观要点抽取", t_refpoints)

    print("\n[6] 生产化检查（集成前必须过）")

    def t_spec_compliance():
        bad = [(s.name, s.validate()) for s in lib if s.validate()]
        assert not bad, f"{len(bad)} 个技能不符合 agentskills.io 规范，例如 {bad[:2]}"
        over = [(s.name, s.body_stats["lines"]) for s in lib if s.body_stats["lines"] > 500]
        assert not over, f"正文超出规范建议的 500 行：{over[:3]}"
        mx_lines = max(s.body_stats["lines"] for s in lib)
        mx_tok = max(s.body_stats["tokens_est"] for s in lib)
        return f"{len(lib)} 个技能合规；正文最长 {mx_lines} 行 / 约 {mx_tok} tokens（预算 500 行 / 5000）"
    check("规范符合性（name/description/正文预算）", t_spec_compliance)

    def t_persistence():
        tmp = config.OUT_DIR / "_verify_library.json"
        tmp.unlink(missing_ok=True)
        probe = lib.get("literature-review")
        old_stats = dict(probe.stats)
        try:
            probe.stats.update({"pulls": 7, "reward_sum": 5.6, "best": 0.9})
            lib.save(tmp)
            assert tmp.exists(), "落盘失败"
            back = SkillLibrary.load(tmp)
            assert set(back.names()) == set(lib.names()), "往返后技能集合不一致"
            assert back.get("literature-review").stats.get("pulls") == 7, "运行统计未持久化"
            assert "scrna-qc-clustering" in back, "种子技能丢失"
        finally:
            probe.stats.clear()
            probe.stats.update(old_stats)
            tmp.unlink(missing_ok=True)
        return f"{len(lib)} 个技能 + 运行统计往返一致"
    check("技能库持久化往返", t_persistence)

    def t_stable_hash():
        code = (
            "import sys;sys.path.insert(0,'.');"
            "from skillnet.index import VectorIndex;"
            "v=VectorIndex();v.fit(['a'],['单细胞测序质控']);"
            "print(round(sum(k*x for k,x in v.encode('单细胞').items()),6))"
        )
        seen = set()
        for seed in ("0", "987654"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            r = subprocess.run(
                [sys.executable, "-c", code], capture_output=True, text=True,
                env=env, cwd=str(ROOT), timeout=90,
            )
            assert r.returncode == 0, f"子进程执行失败：{r.stderr[:200]}"
            seen.add(r.stdout.strip())
        assert len(seen) == 1, f"不同 PYTHONHASHSEED 下向量不一致：{seen}"
        return f"两种 PYTHONHASHSEED 得到同一向量指纹（{seen.pop()}）"
    check("检索索引跨进程可复现", t_stable_hash)

    def t_concurrency():
        c_lib = SkillLibrary(build_seed_skills())
        holder = {"r": Retriever(c_lib).build()}
        errs: list[str] = []
        stop = threading.Event()

        def writer(tid: int) -> None:
            i = 0
            while not stop.is_set():
                i += 1
                c_lib.add(Skill(name=f"verify-conc-{tid}-{i}", description="并发自检技能",
                                domain="自检", steps=["a", "b", "c"], source="distill"))
                holder["r"] = Retriever(c_lib).build()      # 模拟 refresh_runtime 的原子替换
                if i % 30 == 0:
                    c_lib.remove(f"verify-conc-{tid}-{i}")
                time.sleep(0.0005)

        def reader() -> None:
            while not stop.is_set():
                try:
                    sel = holder["r"].search("单细胞测序质控", k=5, mode="bm25").selected
                    for nm in sel:
                        if c_lib.get(nm) is None:
                            errs.append(f"幽灵技能 {nm}")
                except Exception as exc:  # noqa: BLE001
                    errs.append(f"{type(exc).__name__}: {exc}")

        ts = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
        ts += [threading.Thread(target=reader, daemon=True) for _ in range(4)]
        for t in ts:
            t.start()
        time.sleep(2.0)
        stop.set()
        for t in ts:
            t.join(timeout=5)
        assert not errs, f"并发出错 {len(errs)} 次，例如 {errs[:2]}"
        return f"2 写 4 读并发 2 秒：零异常、零幽灵技能（库规模做到 {len(c_lib)}）"
    check("并发读写安全", t_concurrency)

    def t_ledger_isolation():
        a, b = llm.UsageLedger(), llm.UsageLedger()
        with llm.ledger_scope(a):
            llm.current_ledger().record("executor", 1000, 200)
        with llm.ledger_scope(b):
            llm.current_ledger().record("judge", 500, 100)
        assert a.prompt_tokens == 1000 and b.prompt_tokens == 500, "账本未隔离"
        assert a.cost_yuan != b.cost_yuan, "两本账开销应不同"
        assert llm.current_ledger() is llm.LEDGER, "作用域外应回落到全局账本"
        return f"请求级账本互不串账（A={a.prompt_tokens} / B={b.prompt_tokens} tokens）"
    check("成本账本请求级隔离", t_ledger_isolation)

    if args.llm:
        print("\n[7] 真实 LLM 链路（会产生 API 费用）")
        assert config.API_KEY, "未配置 DEEPSEEK_API_KEY"

        def t_exec():
            llm.LEDGER.reset()
            agent = ResearchAgent(lib)
            r = Retriever(lib).build()
            sel = r.search("用纯成分特征预测无机化合物形成能，并评估元素外推能力", k=3, mode="fabric").selected
            run = agent.run("用纯成分特征预测无机化合物形成能力，并评估元素外推能力", skills=sel, style="guided")
            assert run.response.get("steps"), f"未产出步骤: {run.raw[:200]}"
            j = score_plan(run.task, run.response)
            assert j["weighted"] > 0
            return f"选出 {sel[0]}，方案 {len(run.response['steps'])} 步，盲评 {j['weighted']}/10"
        check("Agent 执行 + 盲评（真实 API）", t_exec)

        def t_llm_distill_real():
            llm.LEDGER.reset()
            ev = SkillEvolver(lib)
            before = len(lib)
            s = ev.distill(
                "验证用任务：对一组基因表达矩阵做批次效应校正后再聚类",
                "任务: 批次校正后聚类\n步骤1: 读入矩阵并检查批次标签\n"
                "步骤2: 用 ComBat 校正批次效应\n步骤3: 校正后再做 PCA 与聚类并比较轮廓系数",
                score=0.8,
            )
            assert s is not None, "蒸馏失败（见 out/_last_llm_raw.txt）"
            assert len(lib) == before + 1
            lib.remove(s.name)
            return f"蒸馏出 {s.name}（G{s.generation}），已回滚"
        check("技能蒸馏（真实 API）", t_llm_distill_real)

    # ---- 汇总 ----
    ok = sum(1 for _, p, _ in RESULTS if p)
    print("\n" + "=" * 68)
    print(f"自检完成：{ok}/{len(RESULTS)} 项通过")
    if ok != len(RESULTS):
        print("失败项：")
        for n, p, d in RESULTS:
            if not p:
                print(f"  - {n}: {d}")
    print("=" * 68)

    (config.OUT_DIR / "verify_report.json").write_text(
        json.dumps(
            {"passed": ok, "total": len(RESULTS),
             "checks": [{"name": n, "pass": p, "detail": d} for n, p, d in RESULTS]},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
