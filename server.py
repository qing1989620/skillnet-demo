"""SkillNet-S1 Demo 服务端。

启动：
    python run.py                     # 默认 http://127.0.0.1:8848
    uvicorn server:app --port 8848

提供技能库浏览、三档检索对比、Fabric 路由、Agent 执行、实验结果读取等接口。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from skillnet import config, llm
from skillnet.adapters import export_all
from skillnet.agent import ResearchAgent, STYLE_CARDS, STYLE_GUIDED
from skillnet.catalog import SkillLibrary, build_seed_skills
from skillnet.evolver import SkillEvolver
from skillnet.judge import reference_points_from_skills, score_plan
from skillnet.orchestrator import Orchestrator
from skillnet.retriever import Retriever, gold_overlap

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="SkillNet-S1", version="0.1.0")

STATE: dict[str, Any] = {}


@app.on_event("startup")
def _startup() -> None:
    lib = SkillLibrary(build_seed_skills())
    STATE["lib"] = lib
    STATE["retriever"] = Retriever(lib).build()
    STATE["orchestrator"] = Orchestrator(lib)
    STATE["agent"] = ResearchAgent(lib)
    print(f"[server] 技能库就绪：{len(lib)} 个技能 / {len(lib.by_domain())} 个领域，"
          f"{len(lib.relation_edges())} 条关系边")
    if config.API_KEY:
        print(f"[server] 已接入模型：{config.MODEL} @ {config.BASE_URL}")
    else:
        print("[server] 未检测到 DEEPSEEK_API_KEY —— 技能浏览 / 检索对照 / 关系图 / "
              "实验结果 / 跨框架导出 可直接使用；路由 / 执行 / 进化 / 一键演示需要密钥。")


def lib() -> SkillLibrary:
    return STATE["lib"]


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
    return {"ok": True, "skills": len(lib()), "model": config.MODEL,
            "api_key_configured": bool(config.API_KEY)}


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
    query: str
    k: int = 5
    modes: list[str] = Field(default_factory=lambda: ["bm25", "hybrid", "fabric"])


@app.post("/api/search")
def search(req: SearchReq) -> dict[str, Any]:
    r: Retriever = STATE["retriever"]
    out: dict[str, Any] = {"query": req.query, "k": req.k, "by_mode": {}}
    for m in req.modes:
        llm.LEDGER.reset()
        res = r.search(req.query, k=req.k, mode=m)
        out["by_mode"][m] = {
            **res.to_dict(),
            "cost_yuan": round(llm.LEDGER.cost_yuan, 5),
            "detail": [
                {
                    "name": c.name,
                    "domain": (lib().get(c.name).domain if lib().get(c.name) else ""),
                    "capability": (lib().get(c.name).capability if lib().get(c.name) else ""),
                    "channels": c.channels, "score": c.score, "rank": c.rank,
                }
                for c in res.candidates[: max(req.k, 8)]
            ],
        }
    return out


class RouteReq(BaseModel):
    query: str
    k: int = 5


@app.post("/api/route")
def route(req: RouteReq) -> dict[str, Any]:
    require_llm()
    r: Retriever = STATE["retriever"]
    llm.LEDGER.reset()
    wiki = r.route_with_wiki(req.query, k=req.k)
    orch = STATE["orchestrator"].build_from_relations(wiki["skills"])
    return {
        **wiki,
        "workflow": wiki["workflow"] or orch["workflow"],
        "order": orch["skills"],
        "cost_yuan": round(llm.LEDGER.cost_yuan, 5),
    }


# ======================================================================
# Agent 执行
# ======================================================================
class RunReq(BaseModel):
    task: str
    mode: str = "fabric"          # bare | cards | hybrid | fabric
    k: int = 5
    gold: list[str] = Field(default_factory=list)


@app.post("/api/run")
def run_agent(req: RunReq) -> dict[str, Any]:
    require_llm()
    r: Retriever = STATE["retriever"]
    agent: ResearchAgent = STATE["agent"]
    llm.LEDGER.reset()
    style = {"bare": "bare", "cards": "cards"}.get(req.mode, STYLE_GUIDED)
    skills = (
        [] if req.mode == "bare"
        else r.search(req.task, k=req.k, mode=req.mode).selected
    )
    run = agent.run(req.task, skills=skills, style=style)
    run_cost = llm.LEDGER.cost_yuan
    pts = reference_points_from_skills(lib(), req.gold) if req.gold else []
    j = score_plan(req.task, run.response, pts)
    first = agent.execute_first_step(run) if req.mode in ("hybrid", "fabric") else {}
    return {
        "task": req.task, "mode": req.mode, "skills": skills,
        "plan": run.response, "trajectory": run.trajectory,
        "judge": j, "first_step": first,
        "cost_yuan": round(run_cost + llm.LEDGER.cost_yuan, 5),
        "tokens": llm.LEDGER.prompt_tokens + llm.LEDGER.completion_tokens,
    }


# ======================================================================
# 技能进化
# ======================================================================
class EvolveReq(BaseModel):
    task: str
    op: str = "distill"          # distill | mutate | crossover | regenerate
    base_skill: str | None = None
    donor_skill: str | None = None
    negatives: list[str] = Field(default_factory=list)


@app.post("/api/evolve")
def evolve(req: EvolveReq) -> dict[str, Any]:
    require_llm()
    agent: ResearchAgent = STATE["agent"]
    evolver = SkillEvolver(lib())
    llm.LEDGER.reset()

    # 先让 Agent 在无技能条件下跑一次，得到用于蒸馏的轨迹
    run = agent.run(req.task, skills=[], style="bare")
    score = score_plan(req.task, run.response)["weighted"] / 10.0

    new_skill = None
    if req.op == "distill":
        new_skill = evolver.distill(req.task, run.trajectory, score=score)
    elif req.op == "mutate" and req.base_skill:
        new_skill = evolver.mutate(
            req.base_skill, successes=[run.trajectory], failures=[]
        )
    elif req.op == "crossover" and req.base_skill and req.donor_skill:
        new_skill = evolver.crossover(req.base_skill, req.donor_skill, req.negatives)
    elif req.op == "regenerate":
        new_skill = evolver.regenerate(req.task, reference_traces=[run.trajectory])

    if new_skill:
        STATE["retriever"].refresh()
    return {
        "op": req.op,
        "chat_score": score,
        "accepted": new_skill is not None,
        "new_skill": new_skill.to_dict() if new_skill else None,
        "markdown": new_skill.to_skill_md() if new_skill else None,
        "records": evolver.summary()["records"],
        "library_size": len(lib()),
        "cost_yuan": round(llm.LEDGER.cost_yuan, 5),
    }


# ======================================================================
# 一键演示：把整条链路跑一遍
# ======================================================================
class DemoReq(BaseModel):
    task: str
    gold: list[str] = Field(default_factory=list)
    k: int = 5


@app.post("/api/demo")
def demo(req: DemoReq) -> dict[str, Any]:
    """检索对比 → Fabric 路由编排 → 技能驱动执行 → 独立盲评 → 技能蒸馏。

    一次调用跑完整条链路，用于演示与端到端冒烟。
    """
    require_llm()
    r: Retriever = STATE["retriever"]
    agent: ResearchAgent = STATE["agent"]
    llm.LEDGER.reset()
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
            },
        }
    )

    # 4) 从执行轨迹蒸馏新技能
    evolver = SkillEvolver(lib())
    before = len(lib())
    new_skill = evolver.distill(
        req.task, run.trajectory, score=j["weighted"] / 10.0, parent=skills[:1]
    )
    if new_skill:
        STATE["retriever"].refresh()
    stages.append(
        {
            "stage": "轨迹蒸馏",
            "detail": {
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
        "cost_yuan": round(llm.LEDGER.cost_yuan, 5),
        "tokens": llm.LEDGER.prompt_tokens + llm.LEDGER.completion_tokens,
        "usage_by_role": llm.LEDGER.snapshot()["by_role"],
    }


# ======================================================================
# 跨框架导出
# ======================================================================
@app.post("/api/adapters")
def adapters() -> dict[str, Any]:
    out_dir = config.OUT_DIR / "adapters"
    info = export_all(lib(), out_dir)
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
    data = json.loads(BENCH_FILE.read_text(encoding="utf-8"))
    return data["tasks"]


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
