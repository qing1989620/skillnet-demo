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
import threading
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from skillnet import config, llm
from skillnet.adapters import export_all
from skillnet.agent import ResearchAgent, STYLE_BARE, STYLE_CARDS, STYLE_GUIDED
from skillnet.bandit import SharedLinUCB
from skillnet.catalog import SkillLibrary
from skillnet.evolver import SkillEvolver
from skillnet.judge import reference_points_from_skills, score_plan
from skillnet.orchestrator import Orchestrator
from skillnet.retriever import MODES, Retriever, gold_overlap

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

    return {
        "task": req.task,
        "stages": stages,
        "library_size": len(lib()),
        "cost_yuan": round(led.cost_yuan, 5),
        "tokens": led.prompt_tokens + led.completion_tokens,
        "usage_by_role": led.snapshot()["by_role"],
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
    """首页即汇报演示页；完整 Dashboard 移至 /dashboard。

    演示与日常使用共用一个入口，避免「两个前端地址」造成困惑：
    briefing.html 右上角可进 /dashboard，dashboard 顶栏可返回 /。
    """
    f = WEB_DIR / "briefing.html"
    if not f.exists():
        legacy = WEB_DIR / "index.html"
        if legacy.exists():
            return FileResponse(str(legacy))
        return JSONResponse({"error": "web/briefing.html 不存在"}, status_code=404)
    return FileResponse(str(f))


@app.get("/dashboard")
def dashboard() -> Any:
    f = WEB_DIR / "index.html"
    if not f.exists():
        return JSONResponse({"error": "web/index.html 不存在"}, status_code=404)
    return FileResponse(str(f))


@app.get("/api/config")
def api_config() -> dict[str, Any]:
    return {
        "model": config.MODEL,
        "price_in": config.PRICE_IN,
        "price_out": config.PRICE_OUT,
        "domains": sorted({s.domain for s in lib()}),
        "modes": ["bm25", "hybrid", "fabric"],
    }
