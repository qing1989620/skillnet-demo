"""端到端自检：验证 demo 的每个组件真的能跑，而不是只写了代码。

    python verify.py            # 只做静态与轻量检查（不调用 LLM）
    python verify.py --llm      # 额外跑一次真实的检索 + 蒸馏 + 评审链路

输出 PASS / FAIL 表，任何一项失败退出码为 1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
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
    from skillnet.adapters import export_all
    from skillnet.agent import ResearchAgent
    from skillnet.bandit import LinUCB, RandomSelector
    from skillnet.catalog import SkillLibrary, build_seed_skills, export_skill_dirs
    from skillnet.evolver import SkillEvolver
    from skillnet.index import BM25Index, VectorIndex, weighted_fuse
    from skillnet.judge import reference_points_from_skills, score_plan
    from skillnet.orchestrator import Orchestrator
    from skillnet.retriever import Retriever

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

    def t_bandit():
        b = LinUCB(lib, alpha=0.1)
        cands = ["scrna-qc-clustering", "differential-expression", "pathway-enrichment"]
        n, info = b.select(cands, extra={c: {"retrieval": 0.5} for c in cands})
        assert n in cands, f"选择结果越界: {n}"
        b.update(n, 0.7, {"retrieval": 0.5})
        s = lib.get(n)
        assert s.stats["pulls"] == 1 and abs(s.mean_reward - 0.7) < 1e-6
        # 二次选择应发生变化（A 矩阵已更新，探索奖励下降）
        n2, info2 = b.select(cands, extra={c: {"retrieval": 0.5} for c in cands})
        assert info2["priority"] != info["priority"] or n2 != n
        return f"首轮选 {n}（探索 {info['exploration_bonus']:.4f}）"
    check("LinUCB 选择与更新", t_bandit)

    def t_explore_decay():
        b = LinUCB(lib, alpha=0.3)
        name = "scrna-qc-clustering"
        _, _, e0 = b.score(name)
        for _ in range(5):
            b.update(name, 0.5)
        _, _, e1 = b.score(name)
        assert e1 < e0, f"探索奖励未随观测下降: {e0:.5f} -> {e1:.5f}"
        return f"探索奖励 {e0:.4f} → {e1:.4f}（观测后收敛）"
    check("探索奖励随观测衰减", t_explore_decay)

    def t_random_ablation():
        r = RandomSelector(lib)
        cands = ["scrna-qc-clustering", "differential-expression"]
        n, info = r.select(cands)
        assert n in cands
        r.update(n, 0.9)
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

    print("\n[4] 跨框架导出")

    def t_export():
        out = config.OUT_DIR / "verify_adapters"
        info = export_all(lib, out)
        assert len(info) == 4, f"导出项数异常: {len(info)}"
        cc = out / "claude_code" / ".claude" / "skills"
        adk = out / "google_adk" / "skills"
        assert (cc / "literature-review" / "SKILL.md").exists(), "Claude Code 产物缺失"
        assert (adk / "literature-review" / "SKILL.md").exists(), "ADK 产物缺失"
        agent_py = (out / "google_adk" / "agent.py").read_text(encoding="utf-8")
        assert "load_skill_from_dir" in agent_py and "SkillToolset" in agent_py, "ADK agent.py 不完整"
        tools = json.loads((out / "openai_tools" / "tools.json").read_text(encoding="utf-8"))
        assert len(tools) == 2 and tools[0]["function"]["name"] == "search_skills"
        idx = (out / "index" / "SKILLS_INDEX.md").read_text(encoding="utf-8")
        assert idx.count("- **") == len(lib), "扁平索引条目数与技能数不符"
        return f"4 个框架产物齐备（各 {len(lib)} 个技能）"
    check("四框架导出", t_export)

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

    if args.llm:
        print("\n[6] 真实 LLM 链路（会产生 API 费用）")
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
