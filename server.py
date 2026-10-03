"""SkillNet-S1 Demo 服务端。

启动：
    python run.py                     # 默认 http://127.0.0.1:8848
    uvicorn server:app --port 8848

提供技能库浏览、三档检索对比、Fabric 路由、Agent 执行、实验结果读取等接口。
"""
from __future__ import annotations

import json
import logging
import os
import secrets
import re
import threading
import time
from urllib.parse import quote
from pathlib import Path
from typing import Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from skillnet import config, llm
from skillnet.adapters import export_all
from skillnet.agent import ResearchAgent, STYLE_BARE, STYLE_CARDS, STYLE_GUIDED
from skillnet.artifacts import (collect_execution_artifacts, generate_deliverables,
                                   render_bundle, save_bundle, task_slug)
from skillnet.executor import execute_step, pick_executable_step
from skillnet import pipeline
from skillnet.runtime import (BUS, STEP_DONE, STEP_FAILED, STATUS_BUDGET_EXCEEDED,
                              STATUS_CANCELLED, STATUS_COMPLETED, STATUS_FAILED,
                              STATUS_PARTIAL, Budget, Run, RunStore, TERMINAL,
                              new_run_id, now_ms, task_fingerprint)
from skillnet.bandit import SharedLinUCB
from skillnet.catalog import SkillLibrary
from skillnet.evolver import SkillEvolver
from skillnet.judge import reference_points_from_skills, score_plan
from skillnet.orchestrator import Orchestrator
from skillnet.retriever import MODE_FABRIC, MODES, Retriever, gold_overlap

logging.basicConfig(
    level=os.environ.get("SKILLNET_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("skillnet.server")

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"

app = FastAPI(
    title="SkillNet-S1",
    version="0.2.0",
    description="面向科研 Agent 的技能运维层：技能本体 / 混合检索 / 上下文老虎机 / 技能进化",
)

STATE: dict[str, Any] = {}
_STATE_LOCK = threading.RLock()

# 可选的访问令牌。默认不启用（本地演示）；一旦设置，消耗额度与写盘的接口需要带令牌。
ACCESS_TOKEN = os.environ.get("SKILLNET_TOKEN", "").strip()


@app.on_event("startup")
def _startup() -> None:
    # 技能库 = 种子技能（代码提供）+ 演化技能（落盘）+ 学习到的统计，三层叠加。
    # 不直接用 build_seed_skills()，否则每次重启都会丢掉已有的进化成果。
    lib = SkillLibrary.load()
    STATE["lib"] = lib
    STATE["retriever"] = Retriever(lib).build()
    STATE["orchestrator"] = Orchestrator(lib)
    STATE["agent"] = ResearchAgent(lib)

    st = lib.stats()
    log.info(
        "技能库就绪：%d 个技能 / %d 个领域 / %d 条关系边（演化产生 %d 个）",
        st["total"], st["domains"], st["edges"], st["evolved"],
    )
    if config.API_KEY:
        log.info("已接入模型：%s @ %s", config.MODEL, config.BASE_URL)
    else:
        log.warning(
            "未检测到 DEEPSEEK_API_KEY —— 技能浏览 / 检索对照 / 关系图 / 实验结果 / "
            "跨框架导出 可直接使用；路由 / 执行 / 进化 / 一键演示需要密钥。"
        )
    if ACCESS_TOKEN:
        log.info("已启用访问令牌保护（消耗额度与写盘的接口需带 X-SkillNet-Token）")


def lib() -> SkillLibrary:
    return STATE["lib"]


def refresh_runtime() -> None:
    """技能库变化后重建运行时对象，并**原子替换**引用。

    要点：构造新对象再整体替换，而不是就地改旧索引。
    正在处理的请求可能仍持有旧的 Retriever；就地重建会让并发搜索读到
    「新技能名配旧向量矩阵」的半成品状态，从而静默返回错误的技能。
    """
    with _STATE_LOCK:
        cur = STATE["lib"]
        STATE["retriever"] = Retriever(cur).build()
        STATE["orchestrator"] = Orchestrator(cur)
        STATE["agent"] = ResearchAgent(cur)
        # 策略层重建，但继承已积累的反馈（A/b 矩阵）——技能库刷新不能把学习清零
        old_b = STATE.get("bandit")
        if old_b is not None:
            nb = SharedLinUCB(cur, alpha=old_b.alpha)
            nb.A = old_b.A.copy()
            nb.b = old_b.b.copy()
            nb.n_updates = old_b.n_updates
            STATE["bandit"] = nb
        else:
            STATE["bandit"] = None


def persist_library() -> None:
    """技能库落盘。失败只记日志，不让请求失败。"""
    try:
        path = STATE["lib"].save()
        log.info("技能库已落盘（%d 个技能）-> %s", len(STATE["lib"]), path)
    except OSError as exc:
        log.error("技能库落盘失败：%s", exc)


def require_token(x_skillnet_token: str | None = Header(default=None)) -> None:
    """可选访问令牌。

    默认不启用；设置环境变量 `SKILLNET_TOKEN` 后，所有会消耗模型额度或写盘的接口
    都要求请求头 `X-SkillNet-Token` 与之匹配。用途很具体：防止把服务以
    `--host 0.0.0.0` 暴露到内网/公网后，被无限刷 API 额度并污染技能库。
    """
    if not ACCESS_TOKEN:
        return
    if not x_skillnet_token or not secrets.compare_digest(x_skillnet_token, ACCESS_TOKEN):
        raise HTTPException(401, "缺少或错误的 X-SkillNet-Token 请求头")


def require_llm() -> None:
    """需要大模型的接口在未配置密钥时给出明确错误，而不是静默返回空结果。

    静默降级只在「仍有意义」时才允许（例如 fabric 检索缺密钥时退化为无重排，
    结果依然可用）；而路由 / 执行 / 进化 / 一键演示这类没有模型就毫无意义的接口，
    必须明确报错，否则使用者会以为功能坏了。
    """
    if not config.API_KEY:
        raise HTTPException(
            503,
            "本功能需要调用大语言模型。请在 skillnet-demo/.env 中填入 DEEPSEEK_API_KEY"
            "（可从 .env.example 复制一份改名）。技能库浏览、检索对照、关系图、"
            "实验结果与跨框架导出不需要密钥，可直接使用。",
        )


# ======================================================================
# 基础资源
# ======================================================================
UI_VERSION_FILE = WEB_DIR / "briefing.html"


def _ui_version() -> str:
    """演示页版本戳：浏览器据此自愈缓存（改版后自动强制刷新一次）。"""
    try:
        txt = UI_VERSION_FILE.read_text(encoding="utf-8", errors="replace")
        import re as _re
        m = _re.search(r'const PAGE_VER = "([^"]+)"', txt)
        return m.group(1) if m else "0"
    except OSError:
        return "0"


@app.on_event("startup")
def _startup_sweep() -> None:
    """服务启动即清扫非终态 Run（进程重启留下的），避免"永远在跑"的假象。"""
    try:
        n = run_store().sweep_interrupted()
        if n:
            log.info("启动清扫：%d 个中断 Run 标记为 INTERRUPTED", n)
    except Exception as exc:      # 清扫失败不影响服务启动
        log.error("启动清扫失败：%s", exc)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """健康检查。除了存活，也暴露「是否需要密钥」「是否有未落盘的改动」这类运行状态。"""
    return {
        "ok": True,
        "version": app.version,
        "skills": len(lib()),
        "evolved": sum(1 for s in lib() if s.source != "seed"),
        "model": config.MODEL,
        "api_key_configured": bool(config.API_KEY),
        "token_required": bool(ACCESS_TOKEN),
        "ui_version": _ui_version(),
        "library_path": str(config.LIBRARY_FILE),
    }


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    return lib().stats()


@app.get("/api/skills")
def skills(domain: str | None = None, q: str | None = None) -> dict[str, Any]:
    items = lib().all()
    if domain:
        items = [s for s in items if s.domain == domain]
    if q:
        ql = q.lower()
        items = [
            s for s in items
            if ql in s.name.lower() or ql in s.description.lower()
            or any(ql in t.lower() for t in s.tags)
        ]
    return {
        "total": len(items),
        "items": [
            {
                "name": s.name, "domain": s.domain, "description": s.description,
                "tags": s.tags, "capability": s.capability,
                "inputs": s.inputs, "outputs": s.outputs, "use_when": s.use_when,
                "source": s.source, "generation": s.generation,
                "quality": s.quality, "relations": [list(r) for r in s.relations],
                "stats": s.stats,
            }
            for s in sorted(items, key=lambda x: (x.domain, x.name))
        ],
    }


@app.get("/api/skill/{name}")
def skill_detail(name: str) -> dict[str, Any]:
    s = lib().get(name)
    if not s:
        raise HTTPException(404, f"技能不存在: {name}")
    return {"skill": s.to_dict(), "markdown": s.to_skill_md()}


@app.get("/api/graph")
def graph() -> dict[str, Any]:
    nodes = [
        {
            "id": s.name, "domain": s.domain, "generation": s.generation,
            "source": s.source, "pulls": int(s.stats.get("pulls", 0)),
            "mean_reward": round(s.mean_reward, 3),
        }
        for s in lib()
    ]
    return {"nodes": nodes, "edges": lib().relation_edges()}


# ======================================================================
# 检索与路由
# ======================================================================
class SearchReq(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)
    modes: list[str] = Field(default_factory=lambda: list(MODES))


@app.post("/api/search")
def search(req: SearchReq) -> dict[str, Any]:
    r: Retriever = STATE["retriever"]
    unknown = [m for m in req.modes if m not in MODES]
    if unknown:
        raise HTTPException(422, f"不支持的检索模式 {unknown}；可选 {list(MODES)}")

    out: dict[str, Any] = {"query": req.query, "k": req.k, "by_mode": {}}
    for m in req.modes:
        # 每档单独记账：不再 reset 全局账本（并发下那会把别人的用量算进来）
        with llm.ledger_scope() as led:
            res = r.search(req.query, k=req.k, mode=m)

        detail = []
        for c in res.candidates[: max(req.k, 8)]:
            s = lib().get(c.name)
            detail.append({
                "name": c.name,
                "domain": s.domain if s else "",
                "capability": s.capability if s else "",
                "channels": c.channels, "score": c.score, "rank": c.rank,
            })
        out["by_mode"][m] = {
            **res.to_dict(),
            "cost_yuan": round(led.cost_yuan, 5),
            "detail": detail,
        }
    return out


class RouteReq(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=15)


@app.post("/api/route", dependencies=[Depends(require_token)])
def route(req: RouteReq) -> dict[str, Any]:
    require_llm()
    r: Retriever = STATE["retriever"]
    with llm.ledger_scope() as led:
        wiki = r.route_with_wiki(req.query, k=req.k)
        orch = STATE["orchestrator"].build_from_relations(wiki["skills"])
    return {
        **wiki,
        "workflow": wiki["workflow"] or orch["workflow"],
        "order": orch["skills"],
        "cost_yuan": round(led.cost_yuan, 5),
    }


# ======================================================================
# Agent 执行
# ======================================================================
RUN_MODES = ("bare", "cards", "hybrid", "fabric")


class RunReq(BaseModel):
    task: str = Field(min_length=1, max_length=6000)
    mode: str = "fabric"
    k: int = Field(default=5, ge=1, le=20)
    gold: list[str] = Field(default_factory=list, max_length=20)


@app.post("/api/run", dependencies=[Depends(require_token)])
def run_agent(req: RunReq) -> dict[str, Any]:
    require_llm()
    if req.mode not in RUN_MODES:
        raise HTTPException(422, f"mode 只能是 {list(RUN_MODES)}")
    r: Retriever = STATE["retriever"]
    agent: ResearchAgent = STATE["agent"]
    style = {"bare": STYLE_BARE, "cards": STYLE_CARDS}.get(req.mode, STYLE_GUIDED)

    with llm.ledger_scope() as led:
        skills = (
            [] if req.mode == "bare"
            else r.search(req.task, k=req.k, mode=req.mode).selected
        )
        run = agent.run(req.task, skills=skills, style=style)
        pts = reference_points_from_skills(lib(), req.gold) if req.gold else []
        j = score_plan(req.task, run.response, pts)
        first = agent.execute_first_step(run) if req.mode in ("hybrid", "fabric") else {}

    return {
        "task": req.task, "mode": req.mode, "skills": skills,
        "plan": run.response, "trajectory": run.trajectory,
        "judge": j, "first_step": first,
        # 一次算清：之前用 run_cost + LEDGER.cost_yuan 相加，而后者已包含前者 → 重复计费
        "cost_yuan": round(led.cost_yuan, 5),
        "tokens": led.prompt_tokens + led.completion_tokens,
    }


# ======================================================================
# 技能进化
# ======================================================================
EVOLVE_OPS = ("distill", "mutate", "crossover", "regenerate")


class EvolveReq(BaseModel):
    task: str = Field(min_length=1, max_length=6000)
    op: str = "distill"
    base_skill: str | None = Field(default=None, max_length=64)
    donor_skill: str | None = Field(default=None, max_length=64)
    negatives: list[str] = Field(default_factory=list, max_length=10)


@app.post("/api/evolve", dependencies=[Depends(require_token)])
def evolve(req: EvolveReq) -> dict[str, Any]:
    require_llm()
    if req.op not in EVOLVE_OPS:
        raise HTTPException(422, f"op 只能是 {list(EVOLVE_OPS)}")
    if req.op in ("mutate", "crossover") and not req.base_skill:
        raise HTTPException(422, f"{req.op} 需要提供 base_skill")
    if req.op == "crossover" and not req.donor_skill:
        raise HTTPException(422, "crossover 需要提供 donor_skill")

    agent: ResearchAgent = STATE["agent"]
    evolver = SkillEvolver(lib())

    with llm.ledger_scope() as led:
        # 先让 Agent 在无技能条件下跑一次，得到用于蒸馏的轨迹
        run = agent.run(req.task, skills=[], style=STYLE_BARE)
        score = score_plan(req.task, run.response)["weighted"] / 10.0

        new_skill = None
        if req.op == "distill":
            new_skill = evolver.distill(req.task, run.trajectory, score=score)
        elif req.op == "mutate":
            new_skill = evolver.mutate(
                req.base_skill, successes=[run.trajectory], failures=[]
            )
        elif req.op == "crossover":
            new_skill = evolver.crossover(req.base_skill, req.donor_skill, req.negatives)
        elif req.op == "regenerate":
            new_skill = evolver.regenerate(req.task, reference_traces=[run.trajectory])

    if new_skill:
        refresh_runtime()    # 原子替换运行时对象，避免并发读到半成品索引
        persist_library()    # 落盘，重启后演化成果不丢

    return {
        "op": req.op,
        "chat_score": score,
        "accepted": new_skill is not None,
        "new_skill": new_skill.to_dict() if new_skill else None,
        "markdown": new_skill.to_skill_md() if new_skill else None,
        "records": evolver.summary()["records"],
        "library_size": len(lib()),
        "cost_yuan": round(led.cost_yuan, 5),
    }


# ======================================================================
# 一键演示：把整条链路跑一遍
# ======================================================================
class DemoReq(BaseModel):
    task: str = Field(min_length=1, max_length=6000)
    gold: list[str] = Field(default_factory=list, max_length=20)
    k: int = Field(default=5, ge=1, le=15)


@app.post("/api/demo", dependencies=[Depends(require_token)])
def demo(req: DemoReq) -> dict[str, Any]:
    """检索对比 → Fabric 路由编排 → 技能驱动执行 → 独立盲评 → 技能蒸馏。

    一次调用跑完整条链路，用于演示与端到端冒烟。
    整个链路共用一个请求级账本，因此返回的成本数字就是这一次调用的真实开销。
    """
    require_llm()
    with llm.ledger_scope() as led:
        return _run_demo(req, led)


def run_store() -> RunStore:
    """Run 存储（不覆盖历史；落盘 out/runs/）。首次访问时清扫僵尸 Run。"""
    rs = STATE.get("run_store")
    if rs is None:
        rs = RunStore(config.OUT_DIR / "runs")
        swept = rs.sweep_interrupted()
        if swept:
            log.info("清扫 %d 个中断的 Run（非终态 -> INTERRUPTED）", swept)
        STATE["run_store"] = rs
    return rs


def _bandit() -> SharedLinUCB:
    """服务运行期共享的 LinUCB 单例：反馈在多次请求间持续累积。

    服务重启后从零开始（A=I, b=0），依赖探索机制重新积累——
    这是有意为之：策略参数不持久化，演示状态不污染正式库。
    """
    b = STATE.get("bandit")
    if b is None:
        b = SharedLinUCB(lib(), alpha=0.3)
        STATE["bandit"] = b
    return b


def _run_demo(req: DemoReq, led: llm.UsageLedger) -> dict[str, Any]:
    r: Retriever = STATE["retriever"]
    agent: ResearchAgent = STATE["agent"]
    stages: list[dict[str, Any]] = []

    # 1) 三档检索对比
    retrieval: dict[str, Any] = {}
    for m in ("bm25", "hybrid", "fabric"):
        res = r.search(req.task, k=req.k, mode=m)
        retrieval[m] = {
            "selected": res.selected,
            "recall": round(gold_overlap(res.selected, req.gold), 4) if req.gold else None,
            "trace": res.trace,
            "confidence": res.confidence,
            "raw_bm25_top": res.raw_bm25_top,
            "decision": res.decision,
            "decision_reason": res.decision_reason,
        }
    stages.append({"stage": "检索对比", "detail": retrieval})

    # 1.5) 策略选择：LinUCB 用历史反馈对候选池排序（任务条件化）
    bandit = _bandit()
    cand = list(dict.fromkeys((retrieval["fabric"]["selected"] or [])))[:10]
    before_rows = bandit.rank(req.task, cand) if cand else []
    stages.append(
        {
            "stage": "策略选择（LinUCB）",
            "detail": {
                "n_candidates": len(cand),
                "rows": [
                    {"name": n, "priority": round(p, 4), "exploit": round(e, 4), "explore": round(x, 4)}
                    for n, p, e, x in before_rows
                ],
                "note": "预测收益来自历史反馈（旧任务数据），探索奖励保证未被评估过的技能保留尝试机会",
            },
        }
    )

    # 2) Fabric 路由 + 编排
    wiki = r.route_with_wiki(req.task, k=req.k)
    orch = STATE["orchestrator"].build_from_relations(wiki["skills"])
    stages.append(
        {
            "stage": "任务级 Wiki 路由与编排",
            "detail": {
                "wiki_size": wiki["wiki_size"],
                "skills": wiki["skills"],
                "workflow": wiki["workflow"] or orch["workflow"],
                "order": orch["skills"],
                "reason": wiki["reason"],
            },
        }
    )

    # 3) 技能驱动执行 + 盲评
    skills = wiki["skills"] or retrieval["fabric"]["selected"]
    run = agent.run(req.task, skills=skills, style=STYLE_GUIDED)
    pts = reference_points_from_skills(lib(), req.gold) if req.gold else []
    j = score_plan(req.task, run.response, pts)
    stages.append(
        {
            "stage": "技能驱动执行与盲评",
            "detail": {
                "skills": skills,
                "steps": len(run.response.get("steps") or []),
                "adoption": round(run.adoption, 4),
                "judge": j,
                "plan": {
                    "approach": run.response.get("approach", ""),
                    "steps": run.response.get("steps") or [],
                    "risks": run.response.get("risks") or [],
                    "artifacts": run.response.get("artifacts") or [],
                },
            },
        }
    )

    # 3.2) 真实执行（沙箱）：挑选方案中最适合落地的一步，生成代码并真正运行它。
    # 这是本项目与「写方案的 LLM」的分水岭——产物是跑出来的，不是写出来的。
    sandbox_result: dict[str, Any] = {}
    try:
        idx = pick_executable_step(run.response)
        all_steps = run.response.get("steps") or []
        if idx >= 0:
            st = all_steps[idx] if isinstance(all_steps[idx], dict) else {"action": str(all_steps[idx])}
            sk_name = st.get("skill")
            sk = lib().get(sk_name) if sk_name else None
            sandbox_result = execute_step(
                req.task, st, sk,
                config.OUT_DIR / "demo_artifacts" / task_slug(req.task) / "run",
                max_fix=2, timeout=75)
            sandbox_result["step_index"] = idx
            sandbox_result["step_label"] = f"S{idx + 1}"
    except Exception as exc:                    # 执行失败不影响其余闭环
        log.error("沙箱执行失败：%s", exc)
        sandbox_result = {"final_ok": False, "error": f"{type(exc).__name__}: {exc}",
                          "attempts": [], "artifacts": [], "verification": []}
    stages.append({"stage": "真实执行（沙箱）", "detail": sandbox_result})

    # 3.5) 反馈写回：本次盲评奖励更新共享参数 θ——影响所有技能的下一次预测
    reward = j["weighted"] / 10.0
    adopted = [s for s in skills if s and s != "manual"]
    for s in adopted:
        bandit.update(req.task, s, reward)
    after_rows = bandit.rank(req.task, cand) if cand else []
    after_map = {r[0]: (r[2], r[3]) for r in after_rows}
    feedback = []
    for n, _p, e0, x0 in before_rows:
        e1, x1 = after_map.get(n, (e0, x0))
        feedback.append(
            {
                "name": n,
                "exploit_before": round(e0, 4),
                "exploit_after": round(e1, 4),
                "delta": round(e1 - e0, 4),
                "nudged": n in adopted,
            }
        )

    # 4) 从执行轨迹蒸馏新技能
    evolver = SkillEvolver(lib())
    before = len(lib())
    new_skill = evolver.distill(
        req.task, run.trajectory, score=j["weighted"] / 10.0, parent=skills[:1]
    )
    if new_skill:
        refresh_runtime()    # 原子替换运行时对象
        persist_library()    # 落盘，重启后演化成果不丢

    stages.append(
        {
            "stage": "反馈回流与轨迹蒸馏",
            "detail": {
                "feedback": feedback,
                "reward": round(reward, 4),
                "adopted": adopted,
                "accepted": new_skill is not None,
                "name": new_skill.name if new_skill else None,
                "generation": new_skill.generation if new_skill else None,
                "capability": new_skill.capability if new_skill else None,
                "library_size": len(lib()),
                "delta": len(lib()) - before,
                "records": evolver.summary()["records"],
            },
        }
    )

    # 5) 本次产出：把执行结果渲染为可预览/可下载的真实文件
    bundle = render_bundle(req.task, run.response, j, skills, run.adoption)

    # 5.0) 收集沙箱真实产物（图片/数据），平铺到产物目录供预览
    art_dir_pre = config.OUT_DIR / "demo_artifacts" / bundle["meta"]["slug"]
    try:
        for a in collect_execution_artifacts(
                sandbox_result, art_dir_pre,
                prefix=f"step{sandbox_result.get('step_index', 0) + 1}"):
            bundle["files"].append({
                "name": a["name"], "kind": a["kind"], "body": "", "bytes": a["bytes"],
                "_copy_only": True,          # 已由 collect 落盘，save_bundle 跳过写内容
            })
    except OSError as exc:
        log.error("收集执行产物失败：%s", exc)

    # 5.1) 兑现交付物清单：方案里声明的东西必须真的生成出来，否则它只是承诺
    deliv = generate_deliverables(req.task, run.response, skills)
    for f in deliv["files"]:
        bundle["files"].append({
            "name": f["name"], "kind": f["kind"], "body": f["body"], "bytes": f["bytes"],
            "note": f.get("note", ""), "declared_as": f.get("declared_as", ""),
        })

    art_dir = config.OUT_DIR / "demo_artifacts" / bundle["meta"]["slug"]
    try:
        manifest = save_bundle(bundle, art_dir)
        save_err = ""
    except OSError as exc:                     # 落盘失败不影响主链路
        log.error("产物落盘失败：%s", exc)
        manifest, save_err = [
            {"name": f["name"], "kind": f["kind"], "bytes": f["bytes"],
             "slug": bundle["meta"]["slug"], "inline": True}
            for f in bundle["files"]
        ], str(exc)
    stages.append(
        {
            "stage": "本次产出",
            "detail": {
                "slug": bundle["meta"]["slug"],
                "digest": bundle["meta"]["digest"],
                "artifacts": manifest,
                "saved": not save_err,
                "save_error": save_err,
                "declared": deliv["declared"],
                "generated": deliv["generated"],
                "deliverable_error": deliv["error"],
                "preview": {
                    f["name"]: f["body"][:20000] for f in bundle["files"]
                    if f["name"].endswith((".html", ".md"))
                },
            },
        }
    )

    return {
        "task": req.task,
        "stages": stages,
        "library_size": len(lib()),
        "cost_yuan": round(led.cost_yuan, 5),
        "tokens": led.prompt_tokens + led.completion_tokens,
        "usage_by_role": led.snapshot()["by_role"],
        "slug": bundle["meta"]["slug"],
    }


# ======================================================================
# 跨框架导出
# ======================================================================
@app.post("/api/adapters", dependencies=[Depends(require_token)])
def adapters() -> dict[str, Any]:
    out_dir = config.OUT_DIR / "adapters"
    try:
        info = export_all(lib(), out_dir)
    except OSError as exc:
        log.error("跨框架导出失败：%s", exc)
        raise HTTPException(500, f"导出失败（磁盘写入问题）：{exc}") from exc
    log.info("已导出 %d 个框架产物 -> %s", len(info), out_dir)
    return {"exports": info, "root": str(out_dir)}


# ======================================================================
# 实验结果
# ======================================================================
@app.get("/api/results")
def results() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in sorted(config.OUT_DIR.glob("exp*.json")):
        try:
            out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
    return out


BENCH_FILE = ROOT / "tasks" / "benchmark.json"


@app.get("/api/tasks")
def tasks() -> list[dict[str, Any]]:
    if not BENCH_FILE.exists():
        return []
    try:
        data = json.loads(BENCH_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.error("评测任务集读取失败：%s", exc)
        raise HTTPException(500, f"评测任务集无法解析：{exc}") from exc
    return data.get("tasks") or []


@app.get("/api/skills-index")
def skills_index() -> dict[str, Any]:
    """给前端用的轻量索引。"""
    return {
        "items": [
            {"name": s.name, "domain": s.domain, "capability": s.capability,
             "description": s.description, "generation": s.generation, "source": s.source}
            for s in lib()
        ]
    }


# ======================================================================
# 静态前端
# ======================================================================
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index() -> Any:
    """首页 = 产品主页（六幕叙事 + 对话式演示 + 运行中心入口）。

    页面地图（v0.7 融合后）：
      /           → briefing.html  产品主页（叙事 + 演示 + 运行中心入口）
      /runs       → app.html       运行中心（Run 历史列表，中文）
      /run?id=    → run.html       Live Run（SSE 实时三栏）
      /graph      → graph.html     交互式技能星图
      /dashboard  → index.html     完整面板（技能库/检索/实验/导出）
      /briefing   → briefing.html  （/ 的别名）
    """
    f = WEB_DIR / "briefing.html"
    if not f.exists():
        return JSONResponse({"error": "web/briefing.html 不存在"}, status_code=404)
    return FileResponse(str(f))


@app.get("/briefing")
def briefing_page() -> Any:
    f = WEB_DIR / "briefing.html"
    if not f.exists():
        raise HTTPException(404, "web/briefing.html 不存在")
    return FileResponse(str(f))


@app.get("/runs")
def runs_page() -> Any:
    """运行中心（Run 历史列表，中文）。"""
    f = WEB_DIR / "app.html"
    if not f.exists():
        raise HTTPException(404, "web/app.html 不存在")
    return FileResponse(str(f))


@app.get("/run")
def run_page() -> Any:
    """Live Run 页面（SSE 驱动，实时展示 DAG/时间线/Inspector）。"""
    f = WEB_DIR / "run.html"
    if not f.exists():
        raise HTTPException(404, "web/run.html 不存在")
    return FileResponse(str(f))


@app.get("/chat")
def chat_page() -> Any:
    """对话工作台：左栏会话历史（只记问题）+ 右栏提问与结果，支持追问上下文。"""
    f = WEB_DIR / "chat.html"
    if not f.exists():
        raise HTTPException(404, "web/chat.html 不存在")
    return FileResponse(str(f))


@app.get("/graph")
def graph_page() -> Any:
    """交互式技能星图（Canvas 力导向，可拖拽/缩放/悬停高亮）。"""
    f = WEB_DIR / "graph.html"
    if not f.exists():
        raise HTTPException(404, "web/graph.html 不存在")
    return FileResponse(str(f))


@app.get("/dashboard")
def dashboard() -> Any:
    f = WEB_DIR / "index.html"
    if not f.exists():
        return JSONResponse({"error": "web/index.html 不存在"}, status_code=404)
    return FileResponse(str(f))


class CompareReq(BaseModel):
    task: str = Field(min_length=1, max_length=6000)
    step: dict[str, Any] = Field(default_factory=dict)
    skill: str | None = None
    mode: str = Field(default="contract", pattern="^(contract|prompt|none)$")


@app.post("/api/execute_one", dependencies=[Depends(require_token)])
def execute_one(req: CompareReq) -> Any:
    """单步真实执行（可选技能约束）。

    用途有二：① 演示页对某一步做单独重跑；② **技能对照实验**——
    同一步骤分别在有/无技能约束下执行，对比产物，回答「技能到底带来什么差异」。
    """
    require_llm()
    led = llm.current_ledger()
    with llm.ledger_scope(led):
        sk = lib().get(req.skill) if (req.skill and req.mode != "none") else None
        step = req.step or {"action": req.task}
        slug = task_slug(f"{req.task}|{step.get('action', '')}|{req.skill or 'bare'}|{req.mode}")
        result = execute_step(
            req.task, step, sk,
            config.OUT_DIR / "demo_artifacts" / slug / "run",
            max_fix=2, timeout=75, mode=req.mode)
        result["slug"] = slug
        result["with_skill"] = bool(req.skill)
        # 落盘产物供前端预览
        art_dir = config.OUT_DIR / "demo_artifacts" / slug
        result["files"] = collect_execution_artifacts(result, art_dir, prefix="step")
        try:
            save_manifest = [{"name": f["name"], "kind": f["kind"], "bytes": f["bytes"], "slug": slug}
                             for f in result["files"]]
            result["artifacts_manifest"] = save_manifest
        except Exception:
            result["artifacts_manifest"] = []
    result["cost_yuan"] = round(led.cost_yuan, 5)
    return result


@app.post("/api/runs/{run_id}/perf")
def run_perf(run_id: str, ev: dict[str, Any] = Body(default={})) -> Any:
    """记录前端性能指标（TTFE/TTFM/TTFV），存入 Run.events 供审计。"""
    run = run_store().get(run_id)
    if run is None:
        raise HTTPException(404, "Run 不存在")
    ev = dict(ev or {})
    ev["type"] = "perf.frontend"
    ev["ts_ms"] = int(time.time() * 1000)
    run.events.append(runtime.TraceEvent(**{k: ev.get(k) for k in ("ts_ms", "type", "step", "data")}))
    run_store().save(run)
    return {"ok": True}


@app.get("/api/skill/{name}/raw")
def skill_raw(name: str) -> Any:
    """返回技能的 SKILL.md 原文（供演示页「查看生成的技能全文」）。"""
    s = lib().get(name)
    if s is None:
        raise HTTPException(404, f"技能不存在：{name}")
    f = config.SEED_DIR / "skills" / name / "SKILL.md"
    if f.exists():
        return {
            "name": name,
            "source": "disk",
            "content": f.read_text(encoding="utf-8", errors="replace"),
        }
    return {"name": name, "source": "library", "content": s.to_skill_md()}


@app.get("/api/artifact/{slug}/{fname}")
def artifact(slug: str, fname: str, download: int = 0) -> Any:
    """产物文件预览/下载。

    路径校验：slug 与文件名都只允许安全字符，且解析后必须落在产物目录内——
    防止 `../` 穿越读到仓库其他文件（与既有路径校验策略一致）。
    """
    if not re.fullmatch(r"[0-9a-f]{8}", slug):
        raise HTTPException(400, "非法的任务指纹")
    # 文件名允许中文（交付物名由模型生成，含中文是常态）；只禁止路径分隔符、
    # 控制字符与相对路径标记——真正的越界防护靠下面的 resolve 前缀校验。
    if (not fname or len(fname) > 80 or fname in (".", "..")
            or re.search(r"[/\\\x00-\x1f]", fname)):
        raise HTTPException(400, "非法的产物文件名")
    base = (config.OUT_DIR / "demo_artifacts" / slug).resolve()
    target = (base / fname).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "产物不存在")
    # 图片类产物必须按二进制读（先前的纯文本读取会把 PNG 读坏）
    if target.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".gif"):
        media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".svg": "image/svg+xml", ".gif": "image/gif"}[target.suffix.lower()]
        headers = {}
        if download:
            headers["Content-Disposition"] = (
                f"attachment; filename=\"{target.suffix.lstrip('.')}artifact\"; "
                f"filename*=UTF-8''{quote(fname)}")
        return Response(content=target.read_bytes(), media_type=media, headers=headers)
    media = ("text/html; charset=utf-8" if fname.endswith(".html")
             else "text/markdown; charset=utf-8" if fname.endswith(".md")
             else "text/plain; charset=utf-8")
    headers = {}
    if download:
        # 中文文件名必须用 RFC 5987 的 filename*，并且 ASCII 兜底名不能为空
        ascii_fallback = re.sub(r"[^A-Za-z0-9_.\-]", "_", fname) or "artifact"
        headers["Content-Disposition"] = (
            f"attachment; filename=\"{ascii_fallback}\"; "
            f"filename*=UTF-8''{quote(fname)}")
    return Response(content=target.read_text(encoding="utf-8", errors="replace"),
                    media_type=media, headers=headers)


# ======================================================================
# Run Runtime：运行实体、事件流、取消、预算
# ======================================================================
class RunReq(BaseModel):
    task: str = Field(min_length=1, max_length=6000)
    k: int = Field(default=5, ge=1, le=15)
    max_steps: int = Field(default=3, ge=1, le=8)
    max_cost_yuan: float = Field(default=1.0, gt=0, le=20)
    max_seconds: int = Field(default=300, ge=30, le=1800)
    max_llm_calls: int = Field(default=40, ge=5, le=200)
    # 追问上下文：同一会话此前轮次的 [{q, a}]（a 为上一轮回复摘要）。
    # 只用于规划阶段与最终回复，不污染检索（检索必须用当前问题本身）。
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


def _artifact_digest(run: Any, limit_chars: int = 4200, per_file: int = 900) -> str:
    """产物**内容**摘录（回复能真正回答问题的关键素材）。

    只喂文件名等于没素材——首版回复沦为执行汇报，就是因为 LLM 手里没有产物内容。
    CSV 给表头+前几行，文本类给前 N 字符，图片只报元信息；总量封顶免爆 token。"""
    ws = config.OUT_DIR / "runs" / run.run_id / "artifacts"
    chunks: list[str] = []
    total = 0
    for a in list(run.artifacts)[:10]:
        p = ws / a.name
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in (".png", ".jpg", ".jpeg", ".svg", ".pdf"):
            chunks.append(f"- {a.name}（图件 {a.bytes / 1024:.1f}KB）")
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if ext == ".csv":
            body = "\n".join([l for l in text.splitlines() if l.strip()][:7])
        else:
            body = text[:per_file]
        snippet = body[:per_file]
        chunks.append(f"- {a.name}：\n{snippet}")
        total += len(snippet)
        if total >= limit_chars:
            break
    return "\n".join(chunks) or "（无文本类产物可摘录）"


def _stdout_digest(run: Any, per_step: int = 800, limit: int = 3000) -> str:
    """每步成功执行的真实 stdout 尾部摘录——里面往往是结论与推理本身。"""
    out: list[str] = []
    for st in run.steps:
        ok = [a for a in st.attempts if a.ok]
        if not ok:
            continue
        tail = (ok[-1].stdout or "").strip()
        if tail:
            out.append(f"第{st.idx + 1}步（{st.skill or '通用'}）输出摘录：\n{tail[-per_step:]}")
    return "\n\n".join(out)[:limit] or "（无执行输出）"


def _skill_snapshot(lib_: Any) -> dict[str, dict[str, Any]]:
    """技能统计快照（任务开始/结束时各拍一次，差值即「本次任务对技能做了什么」）。"""
    out: dict[str, dict[str, Any]] = {}
    for s in lib_:
        out[s.name] = dict(s.stats or {})
    return out


def _skill_impact(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]],
                  used: list[str], new_skills: list[dict[str, Any]],
                  lib_before: int, lib_after: int,
                  evolved_before: int, evolved_after: int) -> dict[str, Any]:
    """本次任务的「技能资产影响账」：谁被调用了、统计怎么变的、新增了什么。

    这是「SkillNet 在此任务中扮演什么角色」的**真实数据来源**——
    全部来自技能 stats 的前后差值，不是文案。"""
    fields = ("pulls", "exec_total", "exec_ok", "exec_fix", "exec_fail", "reward_sum")
    touched: list[dict[str, Any]] = []
    for name, a in after.items():
        b = before.get(name)
        if b is None or b == a:
            continue
        delta = {f: round(float(a.get(f, 0)) - float(b.get(f, 0)), 4)
                 for f in fields if float(a.get(f, 0)) != float(b.get(f, 0))}
        if delta:
            touched.append({"name": name, "delta": delta,
                            "after": {f: a.get(f) for f in fields if f in a}})
    touched.sort(key=lambda x: (-abs(x["delta"].get("pulls", 0)), -abs(x["delta"].get("exec_total", 0))))
    return {
        "library_before": lib_before, "library_after": lib_after,
        "evolved_before": evolved_before, "evolved_after": evolved_after,
        "used": [s for s in (used or []) if s],
        "touched": touched[:12],
        "new_skills": new_skills,
        "summary": {
            "used_n": len([s for s in (used or []) if s]),
            "updated_n": len(touched),
            "added_n": len(new_skills),
            "library_delta": lib_after - lib_before,
        },
    }


def _compose_final_reply(run: Any, led: Any) -> str:
    """用**真实运行事实 + 产物内容**生成「Agent 最终回复」。

    两条硬性设计：
      1. 回复必须先**直接回答用户的问题本身**（解释类任务=讲解知识；
         分析类任务=给出结论），再汇报执行与证据——只汇报流程等于没回答；
      2. prompt 里只放已发生的事（含产物内容摘录与执行输出），
         并明确禁止编造；失败/跳过如实说明。调用失败由调用方兜底。"""
    st_map = {"done": "完成", "failed": "失败", "skipped": "跳过（上游失败阻断）",
              "running": "执行中", "pending": "等待"}
    step_lines = []
    for st in run.steps:
        fixed = "（前几次失败，已自动修复）" if (st.status == "done" and st.n_attempts > 1) else ""
        chk = (f"{sum(1 for c in st.checks if c.passed)}/{len(st.checks)}"
               if st.checks else "该步无程序化检查")
        arts = "、".join(a.name for a in st.artifacts) or "无"
        if st.status == "skipped" and st.verify_skip_reason:
            fixed += f"，原因：{st.verify_skip_reason[:60]}"
        if st.status == "failed" and st.error:
            fixed += f"，错误：{str(st.error)[:100]}"
        step_lines.append(
            f"- 第{st.idx + 1}步｜技能 {st.skill or '通用'}｜动作：{st.action[:70]}｜"
            f"{st_map.get(st.status, st.status)}{fixed}｜{st.n_attempts} 次尝试｜"
            f"{st.duration_ms / 1000:.1f}s｜验收 {chk}｜产物 {arts}")
    arts_line = "、".join(f"{a.name}（{a.bytes / 1024:.1f}KB）" for a in run.artifacts) or "无"
    judged = (f"语义评审加权 {float(run.judge.get('weighted') or 0):.1f}/10"
              if isinstance(run.judge, dict) and run.judge.get("weighted") is not None else "未产生评审分")
    cp = (run.staged or {}).get("critical_path") or {}
    cp_line = (f"关键路径 {' → '.join('步骤' + str(i + 1) for i in cp.get('steps', []))}"
               f"（{cp.get('ms', 0) / 1000:.1f}s）" if cp.get("steps") else "未计算")
    evo = run.evolution or {}
    evo_line = (f"已蒸馏出新技能 {evo.get('name')}（第 {evo.get('generation')} 代，库规模 {evo.get('library_size')}）"
                if evo.get("accepted") else "本次未产生通过准入的新技能")
    prompt = f"""你是 SkillNet 的科研 Agent。下面是一次**刚刚真实完成**的任务运行的全部事实记录
（含每一步的真实执行输出摘录与产物内容摘录）。请写「最终回复」交给用户。

结构（必须按此顺序，Markdown）：

## 直接回答
这是回复的主体（占一半以上篇幅）：**用下面的真实素材，把用户问的问题本身讲清楚**。
- 若任务是在问「是什么/为什么/怎么做」（解释、调研、分析类）：完整讲清概念、关键事实、
  原理与边界，让没背景的人读完就懂；可以用小标题、列表、表格组织。
- 若任务是数据/建模类：给出明确结论、关键数字与不确定性，不要只描述流程。
- 只允许使用给出的素材与常识性定义，**禁止编造数字、结论、文献或未发生的步骤**。

## 执行与证据
简明汇报：每步做了什么与结果、验收情况（含失败-修复/跳过，如实写）、产物清单（文件名+大小）。

## 下一步建议
1~3 条具体、可执行的建议（含可复用的技能或可扩展方向）。

硬性要求：
- 中文，专业直接，禁止客套开场（不要"好的/很高兴/没问题"）
- 总长 600~1500 字；信息密度高，不要凑字数（内容需要时可更长）
- 提到产物文件时**用反引号包裹文件名**（如 `result.csv`）——前端会渲染成可点击的产物芯片，
  让读者能直接打开核对（没有这一步，读者只能看到文件名文字，点不开）
- 提到产物文件时**用反引号包裹文件名**（如 `result.csv`）——前端会渲染成可点击的产物芯片，
  让读者能直接打开核对（没有这一步，读者只能看到文件名文字，点不开）
- 不要复述 prompt 结构名以外的元信息（如"本次运行状态"这类流程词可少用）

【任务】{run.task}

【采用技能】{'、'.join([s for s in (run.skills or []) if s][:8]) or '无（通用执行）'}

【执行图（权威依赖图）】
{chr(10).join(step_lines) or '- 无可执行步骤'}

【每步真实执行输出摘录（务必用作回答素材）】
{_stdout_digest(run)}

【产物内容摘录（务必用作回答素材）】
{_artifact_digest(run)}

【关键路径】{cp_line}
【交付产物】{arts_line}
【验收与评审】{judged}
【运行事实】总时长 {run.duration_ms / 1000:.1f}s · 成本 ¥{float(run.cost_yuan or 0):.3f} · Token {run.tokens} · 步骤结果：完成 {sum(1 for s in run.steps if s.status == 'done')} · 失败 {sum(1 for s in run.steps if s.status == 'failed')} · 跳过 {sum(1 for s in run.steps if s.status == 'skipped')}
（注意：此刻 Run 的终态判定尚未执行，不要在回复里写具体终态词，按上述步骤结果如实描述）
【能力沉淀】{evo_line}
"""
    raw = llm.chat(
        [{"role": "system", "content": "你是严谨的科研 Agent。只基于给定事实与常识性定义写作，不编造数字、文献与结论；解释类任务要把知识本身讲清楚。"},
         {"role": "user", "content": prompt}],
        role="reporter", temperature=0.35, max_tokens=2200)
    return (raw or "").strip()


def _run_worker(run_id: str, req: "RunReq") -> None:
    """后台执行一个 Run：检索 → 策略排序 → 编排 → 多步执行 → 蒸馏 → 落盘。"""
    store = run_store()
    run = store.get(run_id)
    if run is None:
        return
    led = llm.UsageLedger()
    lib_before_snapshot = _skill_snapshot(lib())
    lib_size_before = len(lib())
    evolved_before = sum(1 for s in lib() if s.source != "seed")
    new_skill_records: list[dict[str, Any]] = []
    try:
        with llm.ledger_scope(led):
            r = STATE["retriever"]
            # 1) 检索（三档对照，取 fabric 作为主链路）
            t0 = time.time()
            run.status = "RETRIEVING"
            BUS.publish(run, "run.started", task=run.task[:120])
            # 三档同题对照（与原七阶段演示对齐）：bm25/hybrid/fabric 各自留存
            run.retrieval = {}
            for m in MODES:
                _r = r.search(run.task, k=req.k, mode=m)
                run.retrieval[m] = _r.to_dict()
            res = run.retrieval[MODE_FABRIC]
            res.setdefault("trace", []).append(f"三档对照完成：bm25 {len(run.retrieval['bm25']['selected'])} / hybrid {len(run.retrieval['hybrid']['selected'])} / fabric {len(res['selected'])}")
            run.staged["retrieval_ms"] = int((time.time() - t0) * 1000)
            # 注意：retrieval 存的是 to_dict()，必须用键访问——
            # 此前的属性访问让 /api/runs 在检索完成瞬间必崩（被误诊为"LLM 瞬时问题"）
            BUS.publish(run, "retrieval.completed",
                        selected=res.get("selected") or [], decision=res.get("decision"),
                        confidence=res.get("confidence"), raw_bm25_top=res.get("raw_bm25_top"),
                        duration_ms=run.staged["retrieval_ms"])
            pipeline.sync_usage(run, led)

            # 2) 策略排序
            t0 = time.time()
            b = _bandit()
            fabric_selected = res.get("selected") or []
            run.ranking = [
                {"name": n, "priority": round(p, 4), "exploit": round(e, 4), "explore": round(x, 4)}
                for n, p, e, x in b.rank(run.task, fabric_selected)
            ]
            run.staged["ranking_ms"] = int((time.time() - t0) * 1000)
            BUS.publish(run, "ranking.completed", rows=len(run.ranking),
                        top=run.ranking[0]["name"] if run.ranking else None)

            # 3) 编排
            t0 = time.time()
            wiki = r.route_with_wiki(run.task, k=req.k)
            orch = STATE["orchestrator"].build_from_relations(wiki["skills"])
            run.status = "ORCHESTRATING"
            run.skills = wiki["skills"] or fabric_selected
            run.staged["orchestration_ms"] = int((time.time() - t0) * 1000)
            BUS.publish(run, "orchestration.completed",
                        skills=run.skills, order=orch.get("skills") or [],
                        workflow=len(orch.get("workflow") or []),
                        duration_ms=run.staged["orchestration_ms"])

            # 4) 方案
            t0 = time.time()
            agent = STATE["agent"]
            # 追问上下文：把此前轮次的问题与上一轮回复摘要拼进规划输入（检索仍只用当前问题）
            plan_task = run.task
            hist = [h for h in (req.history or []) if isinstance(h, dict) and h.get("q")]
            if hist:
                tail = hist[-3:]
                ctx_lines = []
                for h in tail:
                    ctx_lines.append(f"用户：{str(h.get('q'))[:300]}")
                    if h.get("a"):
                        ctx_lines.append(f"你上一轮的回答摘要：{str(h.get('a'))[:400]}")
                plan_task = (run.task + "\n\n【这是同一会话的后续追问，前文如下（请结合前文回答，"
                             "但研究步骤只针对当前问题）】\n" + "\n".join(ctx_lines))
            run.staged["history_turns"] = len(hist)
            arun = agent.run(plan_task, skills=run.skills, style=STYLE_GUIDED)
            run.plan = arun.response or {}
            run.status = "EXECUTING"
            run.staged["planning_ms"] = int((time.time() - t0) * 1000)
            pipeline.sync_usage(run, led)
            BUS.publish(run, "plan.created", steps=len(run.plan.get("steps") or []),
                        approach=(run.plan.get("approach") or "")[:200],
                        duration_ms=run.staged["planning_ms"])

            # 5) 多步真实执行（编排 workflow = 权威执行图，DAG = Runtime）
            t0 = time.time()
            workspace = config.OUT_DIR / "runs" / run.run_id
            pipeline.execute_run(run, lib(), workspace, run.plan,
                                 max_steps=req.max_steps,
                                 workflow=orch.get("workflow") or None)
            run.staged["execution_ms"] = int((time.time() - t0) * 1000)

            # 6) 盲评 + 反馈回流 + 蒸馏
            t0 = time.time()
            j = score_plan(run.task, run.plan, [])
            run.judge = j
            reward = float(j.get("weighted") or 0) / 10.0
            adopted = [s for s in run.skills if s]
            before_rows = {x["name"]: x["exploit"] for x in run.ranking}
            for s in adopted:
                try:
                    b.update(run.task, s, reward)
                except Exception:
                    pass
            after = {n: e for n, _p, e, _x in b.rank(run.task, adopted)}
            run.feedback = [
                {"name": n, "exploit_before": before_rows.get(n, 0.0),
                 "exploit_after": after.get(n, before_rows.get(n, 0.0)),
                 "delta": round(after.get(n, before_rows.get(n, 0.0)) - before_rows.get(n, 0.0), 4),
                 "nudged": n in adopted}
                for n in adopted
            ]
            BUS.publish(run, "judge.completed", weighted=j.get("weighted"),
                        coverage=j.get("coverage"), reward=round(reward, 4))
            run.status = "EVOLVING"
            evolver = SkillEvolver(lib())
            new_skill = evolver.distill(run.task, getattr(arun, "trajectory", []) or [],
                                        score=reward, parent=adopted[:1])
            if new_skill:
                refresh_runtime()
                persist_library()
            if new_skill is not None:
                new_skill_records.append({
                    "name": getattr(new_skill, "name", ""),
                    "generation": getattr(new_skill, "generation", 0),
                    "parents": list(getattr(new_skill, "parent", []) or []),
                    "domain": getattr(new_skill, "domain", ""),
                    "capability": (getattr(new_skill, "capability", "") or "")[:220],
                    "origin_task": (getattr(new_skill, "origin_task", "") or "")[:200],
                })
            run.evolution = {
                "accepted": new_skill is not None,
                "name": getattr(new_skill, "name", None),
                "generation": getattr(new_skill, "generation", 0),
                "capability": (getattr(new_skill, "capability", "") or "")[:200],
                "library_size": len(lib()),
                "records": evolver.summary().get("records", []),
            }
            BUS.publish(run, "evolution.proposed", accepted=run.evolution["accepted"],
                        name=run.evolution["name"], library_size=run.evolution["library_size"])
            run.staged["judge_evolve_ms"] = int((time.time() - t0) * 1000)
            pipeline.sync_usage(run, led)

        # 7) 收尾：产物 URL + **统一终态判定**（唯一权威处）
        for st in run.steps:
            for a in st.artifacts:
                a.url = f"/api/runs/{run.run_id}/artifacts/{a.name}"
        if len(run.steps) == 0:
            run.error = "没有可执行步骤"

        # 7.5) 本次任务的「技能资产影响账」——供前端『本次任务总结』与回复共用
        try:
            run.staged["skill_impact"] = _skill_impact(
                lib_before_snapshot, _skill_snapshot(lib()),
                list(run.skills or []), new_skill_records,
                lib_size_before, len(lib()), evolved_before,
                sum(1 for s in lib() if s.source != "seed"))
        except Exception as exc:
            run.staged["skill_impact_error"] = f"{type(exc).__name__}: {exc}"

        # 8) Agent 最终回复（真实 LLM 生成，读真实运行事实；失败不影响终态）
        # 注意：必须在 finalize_status **之前**发布 run.reply —— 否则 Run 已成终态，
        # SSE 流会在"终态且事件发完"时立即 end，回复事件永远送不到前端（实测踩过）。
        try:
            reply = _compose_final_reply(run, led)
            if reply:
                run.staged["final_reply"] = reply
                BUS.publish(run, "run.reply", text=reply)
        except Exception as exc:
            run.staged["final_reply_error"] = f"{type(exc).__name__}: {exc}"
        pipeline.sync_usage(run, led)
        pipeline.finalize_status(run)
    except Exception as exc:                       # 任何异常都要落到 Run 上
        run.status = STATUS_FAILED
        run.error = f"{type(exc).__name__}: {exc}"
        run.ended_at_ms = int(time.time() * 1000)
        BUS.publish(run, "run.error", error=run.error[:400])
    finally:
        # 兜底必须自身绝对安全：任何一行抛错都会让 Run 永久停在非终态（实测踩过）
        try:
            pipeline.sync_usage(run, led)
        except Exception:
            pass
        try:
            if run.status not in TERMINAL:
                pipeline.finalize_status(run)
            if not run.error and run.status == STATUS_FAILED:
                run.error = "运行异常终止（见服务日志）"
            store.save(run)
        except Exception as exc:            # 落盘都失败时，至少把错误写进内存对象
            run.error = f"收尾失败：{type(exc).__name__}: {exc}"
        try:
            BUS.publish(run, "run.finished", status=run.status, duration_ms=run.duration_ms,
                        cost=run.cost_yuan, tokens=run.tokens,
                        steps=run.step_stats(), artifacts=len(run.artifacts))
        except Exception:
            pass


@app.post("/api/runs", dependencies=[Depends(require_token)])
def create_run(req: RunReq) -> Any:
    """创建并**后台执行**一个 Run，立即返回 run_id（前端随后订阅事件流）。"""
    require_llm()
    fp = task_fingerprint(req.task)
    run = Run(run_id=new_run_id(fp), task=req.task, task_fp=fp, model=config.MODEL)
    run.budget = Budget(max_cost_yuan=req.max_cost_yuan, max_llm_calls=req.max_llm_calls,
                        max_seconds=req.max_seconds, max_attempts_per_step=3)
    run_store().save(run)
    threading.Thread(target=_run_worker, args=(run.run_id, req), daemon=True).start()
    return {"run_id": run.run_id, "status": run.status, "task_fp": fp}


@app.get("/api/runs")
def list_runs(limit: int = 50, task_fp: str | None = None) -> Any:
    """Run 列表（不覆盖历史；同任务用 task_fp 分组）。"""
    return {"runs": run_store().list_recent(limit=limit, task_fp=task_fp)}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> Any:
    run = run_store().get(run_id)
    if run is None:
        raise HTTPException(404, "Run 不存在")
    return run.to_dict()


@app.post("/api/runs/{run_id}/cancel", dependencies=[Depends(require_token)])
def cancel_run(run_id: str) -> Any:
    """请求取消：执行循环会在下一个检查点退出（不会硬杀，保证已产物与状态一致）。"""
    run = run_store().get(run_id)
    if run is None:
        raise HTTPException(404, "Run 不存在")
    if run.status in TERMINAL:
        return {"run_id": run_id, "status": run.status, "note": "已终止，无需取消"}
    run.cancel_requested = True
    BUS.publish(run, "run.cancel_requested")
    return {"run_id": run_id, "status": "CANCEL_REQUESTED"}


@app.get("/api/runs/{run_id}/stream")
def stream_run(run_id: str) -> Any:
    """SSE 事件流：实时推送该 Run 的 TraceEvent（支持断线重连回放已落盘事件）。"""
    store = run_store()
    run = store.get(run_id)
    if run is None:
        raise HTTPException(404, "Run 不存在")

    def gen():
        import json as _json
        sent = 0
        # 先回放已落盘事件（重连场景）
        for ev in list(run.events):
            yield f"data: {_json.dumps(ev.to_dict(), ensure_ascii=False)}\n\n"
            sent += 1
        q = BUS.subscribe(run_id)
        try:
            idle = 0
            while True:
                if q:
                    ev = q.pop(0)
                    yield f"data: {_json.dumps(ev.to_dict(), ensure_ascii=False)}\n\n"
                    sent += 1
                    idle = 0
                    continue
                cur = store.get(run_id)
                if cur is not None and cur.status in TERMINAL and len(cur.events) <= sent:
                    yield "event: end\ndata: {}\n\n"
                    break
                time.sleep(0.15)
                idle += 1
                if idle % 200 == 0:              # 心跳，防代理超时断开
                    yield ": keep-alive\n\n"
                if idle > 4000:                  # 兜底：10 分钟无事件则结束
                    yield "event: end\ndata: {}\n\n"
                    break
        finally:
            BUS.unsubscribe(run_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/capabilities")
def capabilities() -> dict[str, Any]:
    """能力自证端点：把对照表里承诺的每一项能力用**可计算的实时值**回答。

    设计目的：审阅者可以 curl 这个端点自行核对，而不是只能相信页面文案。
    这里不写死任何数字——库规模、泛化倍数、阈值、算子清单全部现场计算/读取。
    """
    from collections import defaultdict

    from skillnet import adapters
    from skillnet.retriever import (AUTO_EXECUTE_THRESHOLD,
                                    MANUAL_CONFIRM_THRESHOLD)
    from skillnet.schema import QUALITY_DIMENSIONS

    lib_ = lib()
    groups: dict[str, list[str]] = defaultdict(list)
    for s in lib_:
        groups[s.domain].append(s.name)
    dom = max(groups, key=lambda d: len(groups[d]))
    a, b = groups[dom][0], groups[dom][1]
    far = next(s.name for s in lib_ if s.domain != dom)
    bandit = SharedLinUCB(lib_, alpha=0.25, seed=17)
    task = lib_.get(a).capability or f"{dom} 领域的典型任务"
    before = {n: bandit.score(task, n)[1] for n in (a, b, far)}
    bandit.update(task, a, reward=0.95)
    after = {n: bandit.score(task, n)[1] for n in (a, b, far)}
    d_near = abs(after[b] - before[b])
    d_far = abs(after[far] - before[far])
    seed_n = sum(1 for s in lib_ if s.source == "seed")
    evo_n = len(lib_) - seed_n
    return {
        "library": {
            "skills": len(lib_), "domains": len(groups),
            "edges": sum(len(s.relations) for s in lib_),
            "seed": seed_n, "evolved": evo_n,
            "source": "/api/health · /api/graph（同一实时数据源）",
        },
        "linucb": {
            "generalization_ratio": round(d_near / max(d_far, 1e-9), 2),
            "near_delta": round(d_near, 6), "far_delta": round(d_far, 6),
            "method": "SharedLinUCB.update 后同领域未评估技能的预测值变化 / 异领域变化",
            "tests": "tests/test_bandit.py::test_bandit_cross_skill_generalization",
        },
        "confidence_gating": {
            "auto_execute_threshold": AUTO_EXECUTE_THRESHOLD,
            "manual_confirm_threshold": MANUAL_CONFIRM_THRESHOLD,
            "calibration": "42 条查询实测分布标定（见 skillnet/retriever.py 常量注释）",
            "tests": "tests/test_retrieval_policy.py（无关查询不误判 auto、真实任务不误判 direct）",
        },
        "quality_dimensions": list(QUALITY_DIMENSIONS),
        "evolver_operators": ["distill", "mutate", "crossover", "regenerate"],
        "framework_targets": {k: v for k, v in sorted(adapters.SKILLS_DIRS.items())},
        "ledger": {
            "scope": "请求级 contextvar 账本（llm.ledger_scope），跨线程用 copy_context 传播",
            "fields": ["cost_yuan", "prompt_tokens", "completion_tokens", "by_role.calls"],
            "tests": "tests/test_runtime_pipeline.py::test_budget_exceeded_on_cost",
        },
        "statistics": {
            "paired_bootstrap": "bench/run_bench.py::paired_bootstrap（均值差 95% 置信区间）",
            "note": "CI 跨 0 即如实标注『未证明显著提升』",
        },
        "reproducibility": {
            "selfcheck": "python verify.py → 31 项交付自检",
            "tests": "python -m pytest tests/ -q（不联网、确定性）",
            "manifest": "out/bench/*.json 内含 git_commit / library_hash / dataset_hash / model",
        },
    }


@app.get("/api/runs/{run_id}/artifacts/{name}")
def run_artifact(run_id: str, name: str, download: int = 0) -> Any:
    """Run 产物访问（工作区 artifacts 目录）。

    名字解析顺序：① 精确匹配登记名（stepN_前缀）；② 裸名别名——界面与上游
    代码都按原始文件名引用（figure.png），而登记名带 stepN_ 前缀；
    ③ 仍找不到 → 404 并列出实际可用的产物名（可诊断，不是黑盒报错）。"""
    if not re.fullmatch(r"[A-Za-z0-9\-]{8,64}", run_id) and not re.fullmatch(r"[0-9a-zA-Z\-]{10,64}", run_id):
        raise HTTPException(400, "非法的 run_id")
    if not name or len(name) > 120 or re.search(r"[/\\\x00-\x1f]", name):
        raise HTTPException(400, "非法的文件名")
    base = (config.OUT_DIR / "runs" / run_id / "artifacts").resolve()
    target = (base / name).resolve()
    if base not in target.parents or not target.is_file():
        if base.is_dir():
            stem = re.sub(r"^step\d+_", "", name)
            for cand in sorted(base.glob(f"*_{stem}")):
                if cand.is_file() and base in cand.resolve().parents:
                    target = cand.resolve()
                    break
    if base not in target.parents or not target.is_file():
        avail = sorted(p.name for p in base.glob("*"))[:20] if base.is_dir() else []
        hint = f"；可用产物：{avail}" if avail else "；该 Run 没有落盘产物"
        raise HTTPException(404, f"产物不存在（请求名 {name}）{hint}")
    if target.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"):
        media = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".svg": "image/svg+xml"}[target.suffix.lower()]
        return Response(content=target.read_bytes(), media_type=media)
    media = ("text/html; charset=utf-8" if target.suffix == ".html"
             else "text/markdown; charset=utf-8" if target.suffix in (".md", ".csv")
             else "text/plain; charset=utf-8")
    headers = {}
    if download:
        ascii_fallback = re.sub(r"[^A-Za-z0-9_.\-]", "_", name) or "artifact"
        headers["Content-Disposition"] = (f"attachment; filename=\"{ascii_fallback}\"; "
                                          f"filename*=UTF-8''{quote(name)}")
    return Response(content=target.read_text(encoding="utf-8", errors="replace"),
                    media_type=media, headers=headers)


@app.get("/api/config")
def api_config() -> dict[str, Any]:
    return {
        "model": config.MODEL,
        "price_in": config.PRICE_IN,
        "price_out": config.PRICE_OUT,
        "domains": sorted({s.domain for s in lib()}),
        "modes": ["bm25", "hybrid", "fabric"],
    }
