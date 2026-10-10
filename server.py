"""SkillNet-S1 Demo 服务端。

启动：
    python run.py                     # 默认 http://127.0.0.1:8848
    uvicorn server:app --port 8848

提供技能库浏览、三档检索对比、Fabric 路由、Agent 执行、实验结果读取等接口。
"""
from __future__ import annotations

import json
import hashlib
import asyncio
import logging
import mimetypes
import math
import os
import secrets
import re
import threading
import time
from urllib.parse import quote
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from skillnet import assessment, config, llm, runtime
from skillnet.integration import integration_manifest
from skillnet.adapters import export_all
from skillnet.agent import ResearchAgent, STYLE_BARE, STYLE_CARDS, STYLE_GUIDED
from skillnet.artifacts import (collect_execution_artifacts, generate_deliverables,
                                   render_bundle, save_bundle, task_slug)
from skillnet.executor import execute_step, pick_executable_step
from skillnet import pipeline
from skillnet.jobs import JobQueue
from skillnet.s1_identity import verify as verify_s1_identity
from skillnet.runtime import (BUS, STEP_DONE, STEP_FAILED, STATUS_BUDGET_EXCEEDED,
                              STATUS_CANCELLED, STATUS_COMPLETED, STATUS_FAILED,
                              STATUS_PARTIAL, Budget, Run, RunStore, TERMINAL,
                              BudgetExceeded, RunCancelled,
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

@asynccontextmanager
async def _lifespan(application: FastAPI):
    writer_lock = None
    if WORKER_MODE != 'external':
        from skillnet.worker import acquire_writer_lock
        config.OUT_DIR.mkdir(parents=True,exist_ok=True)
        writer_lock = acquire_writer_lock(config.OUT_DIR/'worker.lock')
    try:
        _startup()
        _startup_sweep()
        yield
    finally:
        if writer_lock is not None:
            writer_lock.close()


app = FastAPI(
    title="SkillNet-S1",
    version="0.9.0",
    description="面向科研 Agent 的技能运维层：技能本体 / 混合检索 / 上下文老虎机 / 技能进化",
    lifespan=_lifespan,
)

STATE: dict[str, Any] = {}
_STATE_LOCK = threading.RLock()

# 可选的访问令牌。默认不启用（本地演示）；一旦设置，消耗额度与写盘的接口需要带令牌。
ACCESS_TOKEN = os.environ.get("SKILLNET_TOKEN", "").strip()
MAX_ACTIVE_RUNS = max(1, min(32, int(os.environ.get("SKILLNET_MAX_ACTIVE_RUNS", "4"))))
_RUN_SLOTS = threading.BoundedSemaphore(MAX_ACTIVE_RUNS)
_RUN_THREADS: dict[str, threading.Thread] = {}
WORKER_MODE = os.environ.get('SKILLNET_WORKER_MODE', 'thread')
S1_SIGNING_KEY = os.environ.get('SKILLNET_S1_SIGNING_KEY', '')
if S1_SIGNING_KEY and len(S1_SIGNING_KEY) < 32:
    raise ValueError('SKILLNET_S1_SIGNING_KEY must contain at least 32 characters')


def job_queue() -> JobQueue:
    with _STATE_LOCK:
        if 'job_queue' not in STATE:
            STATE['job_queue'] = JobQueue(config.OUT_DIR / 'jobs.sqlite3')
        return STATE['job_queue']


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
        # 只刷新编码器，保留共享学习器对象；运行中请求持有的引用仍能更新它。
        old_b = STATE.get("bandit")
        if old_b is not None:
            old_b.rebind(cur)
        else:
            STATE["bandit"] = None


def persist_library() -> None:
    """技能库落盘。失败只记日志，不让请求失败。"""
    try:
        path = STATE["lib"].save()
        log.info("技能库已落盘（%d 个技能）-> %s", len(STATE["lib"]), path)
    except OSError as exc:
        log.error("技能库落盘失败：%s", exc)


def require_token(x_skillnet_token: str | None = Header(default=None),
                  authorization: str | None = Header(default=None)) -> None:
    """可选访问令牌。

    默认不启用；设置环境变量 `SKILLNET_TOKEN` 后，所有会消耗模型额度或写盘的接口
    都要求请求头 `X-SkillNet-Token` 与之匹配。用途很具体：防止把服务以
    `--host 0.0.0.0` 暴露到内网/公网后，被无限刷 API 额度并污染技能库。
    """
    if not ACCESS_TOKEN:
        return
    supplied = x_skillnet_token
    if not supplied and authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied or not secrets.compare_digest(supplied.encode("utf-8"), ACCESS_TOKEN.encode("utf-8")):
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


def _startup_sweep() -> None:
    """服务启动即清扫非终态 Run（进程重启留下的），避免"永远在跑"的假象。"""
    try:
        if WORKER_MODE == 'external':
            return  # Worker leases, not an API restart, determine interruption.
        n = run_store().sweep_interrupted()
        job_queue().interrupt_unfinished()
        if n:
            log.info("启动清扫：%d 个中断 Run 标记为 INTERRUPTED", n)
    except Exception as exc:      # 清扫失败不影响服务启动
        log.error("启动清扫失败：%s", exc)


@app.middleware("http")
async def s1_authorization(request: Request, call_next):
    if S1_SIGNING_KEY and (request.url.path.startswith('/api/runs') or request.url.path == '/api/candidates'):
        try:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 131072:
                    return JSONResponse(status_code=413, content={'detail':'请求体过大'})
            request._body = bytes(body)
            context = verify_s1_identity(S1_SIGNING_KEY, request.method, request.url.path,
                                         bytes(body), request.headers).to_dict()
        except ValueError:
            return JSONResponse(status_code=401, content={'detail':'S1 后端身份签名无效或已过期'})
        if request.method not in ('GET','HEAD','OPTIONS') and not job_queue().consume_nonce(request.headers['X-S1-Nonce']):
            return JSONResponse(status_code=409, content={'detail':'重复的 S1 签名请求，请使用新签名'})
        request.state.s1_identity = context
        match = re.match(r'^/api/runs/([A-Za-z0-9-]+)(?:/|$)', request.url.path)
        if match:
            existing = run_store().get(match[1])
            if existing is None or existing.staged.get('s1_identity') != context:
                return JSONResponse(status_code=404, content={'detail':'Run 不存在'})
    return await call_next(request)


@app.middleware("http")
async def _no_cache_html(request: Any, call_next: Any) -> Any:
    """HTML 页面一律禁缓存：改版后「刷新即新版」，不再依赖页面内自愈脚本。

    背景：曾出现「改了但用户看到的还是旧版」——因为 HTML 被浏览器缓存，
    页面内自愈脚本要等 boot() 执行才生效，首次加载仍可能是旧的。"""
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9_.\-]{1,80}", supplied_id) else secrets.token_hex(12)
    request.state.request_id = request_id
    started = time.perf_counter()
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = request_id
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code >= 500 or elapsed_ms > 5000:
        log.warning("request_id=%s method=%s path=%s status=%d duration_ms=%d",
                    request_id, request.method, request.url.path, resp.status_code, elapsed_ms)
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("text/html"):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
    return resp


@app.exception_handler(llm.LLMError)
async def _llm_failure(request: Request, exc: llm.LLMError) -> JSONResponse:
    log.warning("request_id=%s 模型调用失败：%s", getattr(request.state, "request_id", ""), exc)
    return JSONResponse(status_code=502, content={
        "detail": "模型服务暂时不可用，请稍后重试。",
        "request_id": getattr(request.state, "request_id", ""),
    })


@app.get("/api/health")
def health() -> dict[str, Any]:
    """健康检查。除了存活，也暴露「是否需要密钥」「是否有未落盘的改动」这类运行状态。"""
    return {
        "ok": True,
        "version": app.version,
        "skills": len(lib()),
        "evolved": lib().stats()['evolved'],
        "community_skills": lib().stats()['community'],
        "encoder": getattr(getattr(STATE.get('retriever'), 'vec', None), 'status', {}),
        "model": config.MODEL,
        "api_key_configured": bool(config.API_KEY),
        "token_required": bool(ACCESS_TOKEN),
        "ui_version": _ui_version(),
        "library_path": "data/library.json",
        "runtime": {"active_runs": _active_run_count(),
                    "max_active_runs": MAX_ACTIVE_RUNS, "deployment": WORKER_MODE,
                    "queue": job_queue().snapshot(), "isolation": os.environ.get('SKILLNET_SANDBOX', 'process')},
    }


@app.get("/api/stats")
def stats() -> dict[str, Any]:
    return lib().stats()


@app.get('/api/scenarios')
def business_scenarios():
    from skillnet.scenarios import scenarios
    from skillnet.research import research_scenario
    return {'items': [{k:r[k] for k in ('id','title','task','task_sha256')} for r in [research_scenario(), *scenarios()]]}


@app.get('/api/candidates', dependencies=[Depends(require_token)])
def learning_candidates(request: Request):
    rows = []
    for path in sorted((config.OUT_DIR / 'candidates').glob('*.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        identity = getattr(request.state, 's1_identity', None)
        if identity:
            origin = run_store().get(record.get('origin_run_id',''))
            if origin is None or origin.staged.get('s1_identity') != identity:
                continue
        published = lib().get(record['skill']['name'])
        receipt = published.stats.get('verified_improvement_receipt') if published else None
        if receipt and receipt.get('candidate_sha256') != record['sha256']:
            receipt = None
        rows.append({'name':record['skill']['name'],'state':record['state'], 'sha256':record['sha256'],
                     'origin_run_id':record.get('origin_run_id'), 'promotion_policy':record.get('promotion_policy'),
                     'reward_receipt':receipt or record.get('reward_receipt'), 'reward_audit':record.get('reward_audit'),
                     'reward_committed':bool(receipt)})
    return {'items':rows, 'total':len(rows)}


@app.get('/api/learning/reward-policy', dependencies=[Depends(require_token)])
def reward_policy():
    from skillnet import reward_gates
    return dict(policy=reward_gates.policy(), sha256=reward_gates.policy_sha256())


@app.get("/api/auth/check", dependencies=[Depends(require_token)])
def auth_check() -> dict[str, Any]:
    """供连接设置验证令牌：只读，既不消耗模型额度也不改写数据。"""
    return {"ok": True, "token_required": bool(ACCESS_TOKEN)}


@app.get("/api/integrations/s1")
def s1_integration() -> dict[str, Any]:
    """公开可核查的 S1 接入契约与验证状态。"""
    return integration_manifest()


@app.get("/api/skills")
def skills(domain: str | None = None, q: str | None = None, source: str | None = None,
           offset: int = Query(default=0, ge=0), limit: int | None = Query(default=None, ge=1, le=500)) -> dict[str, Any]:
    items = lib().all()
    if domain:
        items = [s for s in items if s.domain == domain]
    if source:
        items = [s for s in items if (s.source == source if source != 'evolved' else s.generation > 0)]
    if q:
        ql = q.lower()
        items = [
            s for s in items
            if ql in s.name.lower() or ql in s.description.lower()
            or any(ql in t.lower() for t in s.tags)
        ]
    return {
        "total": len(items),
        "offset": offset, "limit": limit,
        "items": [
            {
                "name": s.name, "domain": s.domain, "description": s.description,
                "tags": s.tags, "capability": s.capability,
                "inputs": s.inputs, "outputs": s.outputs, "use_when": s.use_when,
                "source": s.source, "generation": s.generation,
                "quality": s.quality, "relations": [list(r) for r in s.relations],
                "stats": s.stats,
                "provenance": s.metadata if s.source == 'github' else {},
            }
            for s in sorted(items, key=lambda x: (x.domain, x.name))[offset:offset + limit if limit else None]
        ],
    }


@app.get("/api/skill/{name}")
def skill_detail(name: str) -> dict[str, Any]:
    s = lib().get(name)
    if not s:
        raise HTTPException(404, f"技能不存在: {name}")
    return {"skill": s.to_dict(), "markdown": s.to_skill_md()}


@app.get('/api/skill/{name}/package', dependencies=[Depends(require_token)])
def skill_package(name: str):
    from skillnet.resources import package_manifest, ResourceIntegrityError
    skill=lib().get(name)
    if skill is None:raise HTTPException(404,'技能不存在')
    try:return package_manifest(skill)
    except FileNotFoundError:raise HTTPException(404,'该技能没有已登记的社区资源包') from None
    except ResourceIntegrityError:raise HTTPException(409,'技能元数据与已登记资源包不一致') from None


@app.get('/api/skill/{name}/resource', dependencies=[Depends(require_token)])
def skill_resource(name: str, path: str = Query(min_length=1,max_length=400)):
    from skillnet.resources import read_resource, ResourceIntegrityError
    skill=lib().get(name)
    if skill is None:raise HTTPException(404,'技能不存在')
    try:raw=read_resource(skill,path)
    except FileNotFoundError:raise HTTPException(404,'资源未登记或不存在') from None
    except ResourceIntegrityError:raise HTTPException(409,'资源指纹不一致，已停止交付') from None
    except ValueError:raise HTTPException(422,'非法资源路径') from None
    return Response(content=raw,media_type='application/octet-stream',headers={
        'X-Content-Type-Options':'nosniff','Content-Security-Policy':"sandbox; default-src 'none'",
        'Content-Disposition':"attachment; filename*=UTF-8''"+quote(Path(path).name),
        'X-Content-SHA256':hashlib.sha256(raw).hexdigest()})


@app.get("/api/graph")
def graph() -> dict[str, Any]:
    nodes = [
        {
            "id": s.name, "domain": s.domain, "generation": s.generation,
            "source": s.source, "pulls": int(s.stats.get("pulls", 0)),
            "mean_reward": round(s.mean_reward, 3),
            "verified_improvement_points": s.stats.get('verified_improvement_points', 0),
        }
        for s in lib()
    ]
    return {"nodes": nodes, "edges": lib().relation_edges()}


# ======================================================================
# 检索与路由
# ======================================================================
class SearchReq(BaseModel):
    query: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    k: int = Field(default=5, ge=1, le=20)
    modes: list[str] = Field(default_factory=lambda: list(MODES), min_length=1, max_length=3)


@app.post("/api/search")
def search(req: SearchReq, x_skillnet_token: str | None = Header(default=None),
           authorization: str | None = Header(default=None)) -> dict[str, Any]:
    r: Retriever = STATE["retriever"]
    unknown = [m for m in req.modes if m not in MODES]
    if unknown:
        raise HTTPException(422, f"不支持的检索模式 {unknown}；可选 {list(MODES)}")
    if len(set(req.modes)) != len(req.modes):
        raise HTTPException(422, "检索模式不可重复")
    if MODE_FABRIC in req.modes:
        require_token(x_skillnet_token, authorization)

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
        orch = _resolve_orchestration(wiki)
    return {
        **wiki,
        "workflow": orch["workflow"],
        "order": orch["skills"],
        "cost_yuan": round(led.cost_yuan, 5),
    }


def _resolve_orchestration(wiki: dict[str, Any], fallback: list[str] | None = None) -> dict[str, Any]:
    """让路由响应、规划上下文与执行 DAG 使用同一组经过验证的依赖边。"""
    names = wiki.get("skills") or fallback or []
    return STATE["orchestrator"].merge_workflow(names, wiki.get("workflow"))


def _judge_evidence(evaluation: dict[str, Any]) -> dict[str, Any]:
    """覆盖率无效表示未知；兼容早期尚未包含 valid 标记的评审记录。"""
    result = dict(evaluation)
    if not result.get("coverage_valid", True):
        result["coverage"] = None
    return result


def _judge_reward(evaluation: dict[str, Any]) -> float | None:
    """评审降级不是实际的低奖励，不能用其占位分数训练或决定技能准入。"""
    if not evaluation.get("score_valid", True):
        return None
    return float(evaluation.get("weighted") or 0) / 10.0


def _demo_learning_reward(evaluation: dict[str, Any], execution: dict[str, Any],
                          planned_steps: int) -> tuple[float | None, str]:
    """Legacy plan comparison has no independent result reference."""
    return None, "方案模型评分仅供参考；演示缺少执行前独立结果判据，不分配学习奖励或更新正式网络"


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
        j = _judge_evidence(score_plan(req.task, run.response, pts))
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
    evolver.candidate_dir = config.OUT_DIR / 'candidates'
    evolver.evidence_context = dict(mode='unexecuted_proposal',
        origin_task_sha256=hashlib.sha256(req.task.strip().encode()).hexdigest(),
        causal_attribution=False, scope='方案提案；尚无真实执行或独立结果证据')

    with llm.ledger_scope() as led:
        # 先让 Agent 在无技能条件下跑一次，得到用于蒸馏的轨迹
        run = agent.run(req.task, skills=[], style=STYLE_BARE)
        evaluation = _judge_evidence(score_plan(req.task, run.response))
        score = _judge_reward(evaluation)

        new_skill = None
        if score is None:
            pass                        # 没有有效评审证据，不能把轨迹视为成功样本入库
        elif req.op == "distill":
            new_skill = evolver.distill(req.task, run.trajectory, score=None)
        elif req.op == "mutate":
            new_skill = evolver.mutate(
                req.base_skill, successes=[], failures=[]
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
        "evaluation": evaluation,
        "skip_reason": "评审不可用，未进行技能准入" if score is None else "仅生成未执行的候选提案，无独立结果证据，不准入正式库",
        "evidence_mode": "unexecuted_proposal",
        "score_role": "plan_advisory",
        "network_updated": False,
        "accepted": False,
        "candidate": new_skill is not None,
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
    with _STATE_LOCK:
        rs = STATE.get("run_store")
        if rs is None:
            rs = RunStore(config.OUT_DIR / "runs")
            swept = rs.sweep_interrupted() if WORKER_MODE != 'external' else 0
            if swept:
                log.info("清扫 %d 个中断的 Run（非终态 -> INTERRUPTED）", swept)
            STATE["run_store"] = rs
        return rs


def _bandit() -> SharedLinUCB:
    """Serving LinUCB. Live requests preview observations on detached copies.

    Weights start from identity/zero and are not deployed by single-run feedback
    or candidate promotion. Offline experiments retain the explicit update API.
    """
    with _STATE_LOCK:
        b = STATE.get("bandit")
        if b is None:
            b = SharedLinUCB(lib(), alpha=0.3)
            STATE["bandit"] = b
        return b


@app.get("/api/learning/policy", dependencies=[Depends(require_token)])
def learning_policy() -> dict[str, Any]:
    """Serving state digest for verification, without exposing raw parameters."""
    state = _bandit().state_dict()
    return dict(mode='shadow', single_run_updates_serving_policy=False,
                policy=state['policy'], updates=state['n_updates'],
                state_sha256=assessment.digest(state), assessment_version=assessment.VERSION,
                release_scope='held-out task suite only; candidate promotion does not deploy ranking weights')


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
    orch = _resolve_orchestration(wiki, retrieval["fabric"]["selected"])
    stages.append(
        {
            "stage": "任务级 Wiki 路由与编排",
            "detail": {
                "wiki_size": wiki["wiki_size"],
                "skills": wiki["skills"],
                "workflow": orch["workflow"],
                "order": orch["skills"],
                "reason": wiki["reason"],
            },
        }
    )

    # 3) 技能驱动执行 + 盲评
    skills = orch["skills"]
    run = agent.run(req.task, skills=skills, style=STYLE_GUIDED)
    pts = reference_points_from_skills(lib(), req.gold) if req.gold else []
    j = _judge_evidence(score_plan(req.task, run.response, pts))
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

    # 3.5) 记录观察：模型的方案评分不能训练正式排序参数。
    reward, learning_skip = _demo_learning_reward(j, sandbox_result, len(run.response.get("steps") or []))
    # Research comparison executes only one step. Selected but unexecuted
    # skills must not receive that step's reward or become its parents.
    executed_skill = sandbox_result.get("skill")
    adopted = [executed_skill] if isinstance(executed_skill, str) and executed_skill in skills else []
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
                "nudged": reward is not None and n in adopted,
                "skip_reason": learning_skip,
            }
        )

    # 4) 从执行轨迹蒸馏新技能
    evolver = SkillEvolver(lib())
    evolver.candidate_dir = config.OUT_DIR / 'candidates'
    before = len(lib())
    new_skill = (evolver.distill(req.task, run.trajectory, score=reward, parent=adopted[:1])
                 if reward is not None else None)
    if new_skill:
        refresh_runtime()    # 原子替换运行时对象
    if new_skill or adopted:
        persist_library()    # 落盘，重启后演化成果不丢

    stages.append(
        {
            "stage": "反馈回流与轨迹蒸馏",
            "detail": {
                "feedback": feedback,
                "reward": round(reward, 4) if reward is not None else None,
                "mode": "observation_only",
                "network_updated": False,
                "skip_reason": learning_skip,
                "adopted": adopted,
                "accepted": False,
        "candidate": new_skill is not None,
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
    for f in sorted([*config.OUT_DIR.glob("exp*.json"), *config.OUT_DIR.glob('execution-benchmark-[0-9]*.json')]):
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


class PerfReq(BaseModel):
    data: dict[str, float] = Field(default_factory=dict, max_length=12)


@app.post("/api/runs/{run_id}/perf", dependencies=[Depends(require_token)])
def run_perf(run_id: str, ev: PerfReq) -> Any:
    """记录前端性能指标（TTFE/TTFM/TTFV），存入 Run.events 供审计。"""
    run = run_store().get(run_id)
    if run is None:
        raise HTTPException(404, "Run 不存在")
    if (len(json.dumps(ev.data)) > 2048
            or any(not re.fullmatch(r"[A-Za-z0-9_]{1,32}", k) for k in ev.data)
            or any(not math.isfinite(v) or v < 0 or v > 1e9 for v in ev.data.values())):
        raise HTTPException(422, "非法的性能指标")
    if sum(e.type == "perf.frontend" for e in run.events) >= 12:
        return {"ok": True, "note": "本次运行的性能采样已完成"}
    BUS.publish(run, "perf.frontend", **ev.data)
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


def _artifact_response(target: Path, name: str, download: bool = False) -> Response:
    media = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if target.suffix.lower() == ".md":
        media = "text/markdown"
    headers = {"X-Content-Type-Options": "nosniff",
               "Content-Security-Policy": "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:;"}
    # 生成的 HTML/SVG 可包含任意脚本。独立 opaque origin + 禁止脚本/连接，
    # 防止预览产物读取主站存储、带令牌请求 API 或跳转父页面。
    if download:
        fallback = re.sub(r"[^A-Za-z0-9_.\-]", "_", name) or "artifact"
        headers["Content-Disposition"] = f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(name)}'
    return FileResponse(target, media_type=media, headers=headers)


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
            or re.search(r"[/\\:\x00-\x1f\x7f]", fname)):
        raise HTTPException(400, "非法的产物文件名")
    base = (config.OUT_DIR / "demo_artifacts" / slug).resolve()
    target = (base / fname).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "产物不存在")
    return _artifact_response(target, fname, bool(download))


# ======================================================================
# Run Runtime：运行实体、事件流、取消、预算
# ======================================================================
class HistoryTurn(BaseModel):
    q: str = Field(min_length=1, max_length=6000, pattern=r"\S")
    a: str = Field(default="", max_length=8000)
    run_id: str = Field(default='', max_length=96, pattern=r'^[A-Za-z0-9-]*$')


class ArtifactRef(BaseModel):
    run_id: str = Field(max_length=96, pattern=r'^[A-Za-z0-9-]+$')
    name: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class RunReq(BaseModel):
    task: str = Field(min_length=1, max_length=6000, pattern=r"\S")
    k: int = Field(default=5, ge=1, le=15)
    max_steps: int = Field(default=3, ge=1, le=8)
    max_cost_yuan: float = Field(default=1.0, gt=0, le=20)
    max_seconds: int = Field(default=300, ge=30, le=1800)
    max_llm_calls: int = Field(default=40, ge=5, le=200)
    # 追问上下文：同一会话此前轮次的 [{q, a}]（a 为上一轮回复摘要）。
    # 只用于规划阶段与最终回复，不污染检索（检索必须用当前问题本身）。
    history: list[HistoryTurn] = Field(default_factory=list, max_length=20)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list, max_length=16)


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
    judged = (f"方案盲评加权 {float(run.judge.get('weighted') or 0):.1f}/10（评价方案，不证明产物正确）"
              if isinstance(run.judge, dict) and run.judge.get("weighted") is not None
              and run.judge.get("score_valid", True)
              else "未获得有效评分，未用于反馈或技能准入")
    cp = (run.staged or {}).get("critical_path") or {}
    cp_line = (f"关键路径 {' → '.join('步骤' + str(i + 1) for i in cp.get('steps', []))}"
               f"（{cp.get('ms', 0) / 1000:.1f}s）" if cp.get("steps") else "未计算")
    evo = run.evolution or {}
    semantic = [v for s in run.steps for v in s.verifications]
    semantic_line = (f"产物语义复核 {sum(v.passed for v in semantic)}/{len(semantic)} 通过；"
                     f"未确认项：{'；'.join(v.item for v in semantic if not v.passed) or '无'}")
    gate = (run.staged or {}).get("learning_gate") or {}
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
- 正文不要报告总成本、总 Token 或总耗时：下方累计值尚未包含本次报告生成，最终值由界面的结构化运行指标展示。

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
【产物语义复核】{semantic_line}
【独立结果判断及边界】{json.dumps((run.staged or {}).get('quality_assessment') or {'overall_verdict':'unconfirmed'}, ensure_ascii=False)[:12000]}
模型方案评分不是学习奖励。整体满意度、报告洞察、技能因果贡献和网络整体提升均未被证实；不得声称问一次就优化了网络。独立判据通过只支持已测范围。
【学习准入】{gate.get('reason') or gate.get('skip_reason') or '未记录'}。必须如实说明未确认项；程序运行完成不等于全部验收通过。
【报告生成前累计（不是最终运行总额）】耗时 {run.duration_ms / 1000:.1f}s · 成本 ¥{float(run.cost_yuan or 0):.3f} · Token {run.tokens} · 步骤结果：完成 {sum(1 for s in run.steps if s.status == 'done')} · 失败 {sum(1 for s in run.steps if s.status == 'failed')} · 跳过 {sum(1 for s in run.steps if s.status == 'skipped')}
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
    run._checkpoint_writer = lambda: store.save(run)
    lib_before_snapshot: dict[str, dict[str, Any]] = {}
    lib_size_before = 0
    evolved_before = 0
    new_skill_records: list[dict[str, Any]] = []
    def checkpoint() -> None:
        pipeline.sync_usage(run, led)
        if WORKER_MODE == 'external' and job_queue().cancelled(run_id):
            run.cancel_requested = True
        store.save(run)
        runtime.check_budget(run)
    try:
        lib_before_snapshot = _skill_snapshot(lib())
        lib_size_before = len(lib())
        evolved_before = sum(1 for s in lib() if s.generation > 0)
        with llm.ledger_scope(led), llm.guard_scope(checkpoint):
            checkpoint()
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
                        modes={m: {key: run.retrieval[m].get(key) for key in
                                   ("selected", "components", "decision", "decision_reason",
                                    "degraded", "degraded_reason", "confidence_kind")}
                               for m in MODES},
                        duration_ms=run.staged["retrieval_ms"])
            pipeline.sync_usage(run, led)
            checkpoint()
            store.save(run)

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
                        top=run.ranking[0]["name"] if run.ranking else None,
                        entries=run.ranking, duration_ms=run.staged["ranking_ms"])

            # 3) 编排
            t0 = time.time()
            run.status = "ORCHESTRATING"
            wiki = r.route_with_wiki(run.task, k=req.k)
            orch = _resolve_orchestration(wiki, fabric_selected)
            run.skills = orch["skills"]
            run.staged["orchestration"] = {
                "order": run.skills, "workflow": orch["workflow"],
                "source": wiki.get("source", orch.get("source", "")),
                "degraded": bool(wiki.get("degraded") or orch.get("degraded")),
                "reason": wiki.get('reason',''), "decisions": wiki.get('decisions',[]),
            }
            run.staged["orchestration_ms"] = int((time.time() - t0) * 1000)
            BUS.publish(run, "orchestration.completed",
                        skills=run.skills, order=orch.get("skills") or [],
                        workflow=len(orch.get("workflow") or []),
                        edges=orch["workflow"],
                        source=run.staged["orchestration"]["source"],
                        reason=wiki.get('reason',''),decisions=wiki.get('decisions',[]),
                        degraded=run.staged["orchestration"]["degraded"],
                        duration_ms=run.staged["orchestration_ms"])
            checkpoint()
            store.save(run)

            # 4) 方案
            t0 = time.time()
            agent = STATE["agent"]
            # 追问上下文：把此前轮次的问题与上一轮回复摘要拼进规划输入（检索仍只用当前问题）
            plan_task = run.task
            hist = [h.model_dump() for h in req.history]
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
            if req.artifact_refs:
                plan_task += '\n已携带上一轮的真实文件版本，禁止重新生成原始数据：\n' + '\n'.join(
                    f"{a.logical_name} (SHA-256 {a.sha256})" for a in run.artifacts if a.kind == '跨轮输入')
            arun = agent.run(plan_task, skills=run.skills, style=STYLE_GUIDED, max_steps=req.max_steps)
            run.plan = arun.response or {}
            from skillnet.governance import fingerprint
            run.staged['skill_versions'] = {name: {'sha256': fingerprint(lib().get(name)),
                'source': lib().get(name).source} for name in run.skills if lib().get(name)}
            run.staged["evaluation_contract"] = assessment.prepare_contract(run.task)
            BUS.publish(run, "evaluation.prepared", contract=run.staged["evaluation_contract"])
            run.status = "EXECUTING"
            run.staged["planning_ms"] = int((time.time() - t0) * 1000)
            pipeline.sync_usage(run, led)
            BUS.publish(run, "plan.created", steps=len(run.plan.get("steps") or []),
                        approach=(run.plan.get("approach") or "")[:200],
                        duration_ms=run.staged["planning_ms"])
            checkpoint()
            store.save(run)

            # 5) 多步真实执行（编排 workflow = 权威执行图，DAG = Runtime）
            t0 = time.time()
            workspace = config.OUT_DIR / "runs" / run.run_id
            pipeline.execute_run(run, lib(), workspace, run.plan,
                                 max_steps=req.max_steps,
                                 workflow=orch.get("workflow") or None)
            run.staged["execution_ms"] = int((time.time() - t0) * 1000)
            checkpoint()
            store.save(run)

            # 6) 独立结果核验 + 影子观察；方案模型评分只作为建议。
            t0 = time.time()
            quality = assessment.assess(run, workspace, lib())
            shadow = assessment.shadow_feedback(b, run.task, quality)
            run.staged["quality_assessment"] = quality
            from skillnet import reward_gates
            gates = reward_gates.observation_gates(run, quality)
            run.staged["reward_gates"] = gates
            run.staged["shadow_feedback"] = shadow
            run.feedback = shadow["rows"]
            BUS.publish(run, "evaluation.completed", assessment=quality, shadow=shadow, reward_gates=gates)
            j = _judge_evidence(score_plan(run.task, run.plan, []))
            run.judge = j
            reward = None
            learning_skip = assessment.NETWORK_REASON
            candidate_score = quality["candidate_score"]
            run.staged["learning_gate"] = {"eligible": False, "mode": "shadow",
                "network_updated": False, "candidate_eligible": quality["candidate_eligible"],
                "reward_eligible": gates['eligible'], "reward_points": 0, "blockers": gates['blockers'],
                "evidence_sha256": quality["evidence_sha256"], "skip_reason": learning_skip}
            adopted = sorted({s.skill for s in run.steps if s.skill and s.status == runtime.STEP_DONE})
            BUS.publish(run, "judge.completed", weighted=j.get("weighted") if j.get("score_valid", True) else None,
                        coverage=j.get("coverage"), reward=round(reward, 4) if reward is not None else None,
                        score_valid=j.get("score_valid", True), coverage_valid=j.get("coverage_valid", True),
                        learning_eligible=False, role="plan_advisory", mode="shadow", skip_reason=learning_skip)
            run.status = "EVOLVING"
            evolver = SkillEvolver(lib())
            evolver.candidate_dir = config.OUT_DIR / 'candidates'
            evolver.origin_run_id = run.run_id
            from skillnet.governance import known_training_tasks
            training_tasks = known_training_tasks(lib(), adopted)
            training_tasks.add(quality['task_sha256'])
            training_tasks.update(hashlib.sha256(str(h.get('q', '')).strip().encode()).hexdigest() for h in hist)
            for artifact in run.artifacts:
                origin = store.get(artifact.source_run_id) if artifact.source_run_id else None
                if origin:training_tasks.add(hashlib.sha256(origin.task.strip().encode()).hexdigest())
            evolver.evidence_context = dict(assessment_version=quality['version'],
                reward_policy_sha256=gates['policy_sha256'],
                origin_task_sha256=quality['task_sha256'], evidence_sha256=quality['evidence_sha256'],
                training_task_sha256=sorted(training_tasks), scope=quality['scope'], causal_attribution=False)
            execution_trajectory = json.dumps({'task': run.task, 'steps': [
                {'idx':s.idx,'action':s.action,'skill':s.skill,'contract':s.contract,
                 'status':s.status,'repairs':[a.repair_reason for a in s.attempts if a.repair_reason],
                 'checks':[c.to_dict() for c in s.checks if c.required],
                 'semantic':[v.to_dict() for v in s.verifications],
                 'files':[{'name':a.logical_name or a.name,'sha256':a.sha256} for a in s.artifacts]}
                for s in run.steps],
                'acceptance': pipeline.contracts.acceptance(run),
                'independent_assessment': quality}, ensure_ascii=False)
            measured_parents = [row['skill'] for row in quality['observations']
                                if row['skill'] and row['observed_score'] is not None]
            new_skill = (evolver.distill(run.task, execution_trajectory,
                                         score=candidate_score, parent=measured_parents[:1])
                         if candidate_score is not None else None)
            is_candidate = bool(new_skill and getattr(new_skill, 'metadata', {}).get('governance_status') == 'candidate')
            if new_skill and not is_candidate:
                refresh_runtime()
            # 执行次数等事实统计仍需落盘；正式排序参数未更新。
            if new_skill or adopted:
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
                "accepted": new_skill is not None and not is_candidate,
                "candidate": {"name": new_skill.name, "state": "pending_frozen_evaluation"} if is_candidate else None,
                "name": getattr(new_skill, "name", None),
                "generation": getattr(new_skill, "generation", 0),
                "capability": (getattr(new_skill, "capability", "") or "")[:200],
                "library_size": len(lib()),
                "records": evolver.summary().get("records", []),
                "skipped": candidate_score is None,
                "skip_reason": "缺少独立合格的完整执行证据，只保留观察" if candidate_score is None else "候选仅隔离保存，尚未证明跨任务增益",
            }
            BUS.publish(run, "evolution.proposed", accepted=run.evolution["accepted"],
                        candidate=run.evolution.get("candidate"),
                        name=run.evolution["name"], library_size=run.evolution["library_size"],
                        generation=run.evolution["generation"], feedback=run.feedback,
                        skipped=run.evolution["skipped"], skip_reason=run.evolution["skip_reason"])
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
                sum(1 for s in lib() if s.generation > 0))
        except Exception as exc:
            run.staged["skill_impact_error"] = f"{type(exc).__name__}: {exc}"

        # 8) Agent 最终回复（真实 LLM 生成，读真实运行事实；失败不影响终态）
        # 注意：必须在 finalize_status **之前**发布 run.reply —— 否则 Run 已成终态，
        # SSE 流会在"终态且事件发完"时立即 end，回复事件永远送不到前端（实测踩过）。
        try:
            # 报告阶段也要留在本 Run 的账本与守卫里；否则 reporter 成本会记进
            # 进程级默认账本，且取消/预算耗尽后仍产生额外模型请求。
            with llm.ledger_scope(led), llm.guard_scope(checkpoint):
                checkpoint()
                reply = _compose_final_reply(run, led)
            if reply:
                run.staged["final_reply"] = reply
                BUS.publish(run, "run.reply", text=reply)
        except BudgetExceeded:
            raise
        except Exception as exc:
            run.staged["final_reply_error"] = f"{type(exc).__name__}: {exc}"
        pipeline.sync_usage(run, led)
        checkpoint()
        pipeline.finalize_status(run)
    except BudgetExceeded as exc:
        run.status = STATUS_CANCELLED if isinstance(exc, RunCancelled) else STATUS_BUDGET_EXCEEDED
        run.error = str(exc)
        run.ended_at_ms = now_ms()
        BUS.publish(run, "run.cancelled" if isinstance(exc, RunCancelled) else "run.budget_exceeded",
                    reason=run.error, cost=run.cost_yuan)
    except Exception as exc:                       # 任何异常都要落到 Run 上
        log.exception("run_id=%s 后台执行失败", run.run_id)
        run.status = STATUS_FAILED
        run.error = f"{type(exc).__name__}: {exc}"
        run.ended_at_ms = int(time.time() * 1000)
        BUS.publish(run, "run.error", error=run.error[:400])
    finally:
        # 兜底必须自身绝对安全：任何一行抛错都会让 Run 永久停在非终态（实测踩过）
        try:
            pipeline.sync_usage(run, led)
            for art in run.artifacts:
                art.url = f"/api/runs/{run.run_id}/artifacts/{quote(art.name)}"
        except Exception:
            pass
        try:
            if run.status not in TERMINAL:
                pipeline.finalize_status(run)
            if not run.error and run.status == STATUS_FAILED:
                run.error = "运行异常终止（见服务日志）"
        except Exception as exc:            # 落盘都失败时，至少把错误写进内存对象
            run.error = f"收尾失败：{type(exc).__name__}: {exc}"
        try:
            if run.staged.get('quality_assessment'):
                from skillnet import reward_gates
                gates = reward_gates.observation_gates(run,run.staged['quality_assessment'])
                run.staged['reward_gates'] = gates
                run.staged['learning_gate']['blockers'] = gates['blockers']
                BUS.publish(run,'evaluation.gates_updated',reward_gates=gates)
        except Exception:
            log.exception("run_id=%s 奖励门禁收尾核验失败",run.run_id)
        try:
            BUS.publish(run, "run.finished", status=run.status, duration_ms=run.duration_ms,
                        cost=run.cost_yuan, tokens=run.tokens,
                        steps=run.step_stats(), artifacts=len(run.artifacts))
            store.save(run)          # run.finished 必须一并持久化，重启后仍可正确回放
        except Exception:
            log.exception("run_id=%s 运行终态保存失败", run.run_id)


def _active_run_count() -> int:
    with _STATE_LOCK:
        return sum(t.is_alive() for t in _RUN_THREADS.values())


def _bounded_run_worker(run_id: str, req: RunReq) -> None:
    try:
        from skillnet.worker import execute_job
        owner = f'{os.getpid()}-{secrets.token_hex(6)}'
        job = job_queue().claim(owner, run_id=run_id)
        if job:
            job['worker_owner'] = owner
            execute_job(job_queue(), job, lambda rid, payload: _run_worker(rid, RunReq.model_validate(payload)))
    finally:
        with _STATE_LOCK:
            _RUN_THREADS.pop(run_id, None)
        _RUN_SLOTS.release()


@app.post("/api/runs", dependencies=[Depends(require_token)])
def create_run(req: RunReq, request: Request = None) -> Any:
    """创建并**后台执行**一个 Run，立即返回 run_id（前端随后订阅事件流）。"""
    require_llm()
    if WORKER_MODE != 'external' and not _RUN_SLOTS.acquire(blocking=False):
        raise HTTPException(429, "当前运行已达到并发上限，请稍后提交。", headers={"Retry-After": "10"})
    fp = task_fingerprint(req.task)
    run = Run(run_id=new_run_id(fp), task=req.task, task_fp=fp, model=config.MODEL)
    identity = getattr(request.state, 's1_identity', None) if request else None
    if identity:
        run.staged['s1_identity'] = identity
    run.budget = Budget(max_cost_yuan=req.max_cost_yuan, max_llm_calls=req.max_llm_calls,
                        max_seconds=req.max_seconds, max_attempts_per_step=3)
    try:
        refs = list(req.artifact_refs)
        if not refs and req.history and req.history[-1].run_id:
            previous = run_store().get(req.history[-1].run_id)
            if previous is None or identity and previous.staged.get('s1_identity') != identity:
                raise HTTPException(404, '上一轮运行不存在或无权访问')
            if previous:
                latest = {}
                for artifact in sorted(previous.artifacts, key=lambda a:(a.version,a.from_step if a.from_step is not None else -1,a.name)):
                    if artifact.kind != '跨轮输入' and artifact.sha256:
                        latest[artifact.logical_name or artifact.name] = artifact
                refs = [ArtifactRef(run_id=previous.run_id, name=a.name, sha256=a.sha256)
                        for a in latest.values()][:16]
        seen_destinations = set()
        for ref in refs:
            previous = run_store().get(ref.run_id)
            if identity and (previous is None or previous.staged.get('s1_identity') != identity):
                raise HTTPException(404, '跨轮文件不存在')
            artifact = next((a for a in previous.artifacts if a.name == ref.name), None) if previous else None
            if not artifact or artifact.sha256 != ref.sha256:
                raise HTTPException(409, '跨轮文件版本已变化或不存在')
            origin = config.OUT_DIR / 'runs' / ref.run_id / 'artifacts' / ref.name
            if not origin.resolve().is_relative_to((config.OUT_DIR / 'runs' / ref.run_id / 'artifacts').resolve()):
                raise HTTPException(400, '非法的文件引用')
            if not origin.is_file() or pipeline._sha256_file(origin) != ref.sha256:
                raise HTTPException(409, '跨轮文件内容校验失败')
            history_name = 'history_' + ref.run_id[-8:] + '_' + ref.name
            logical = artifact.logical_name or re.sub(r'^step\d+_', '', artifact.name)
            if logical in seen_destinations:
                raise HTTPException(409, '同一逻辑文件存在多个历史版本，请明确选择一个版本')
            seen_destinations.add(logical)
            destination = config.OUT_DIR / 'runs' / run.run_id / 'artifacts' / history_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(origin, destination)
            run.artifacts.append(runtime.Artifact(name=destination.name, kind='跨轮输入', bytes=artifact.bytes,
                sha256=artifact.sha256, logical_name=logical,
                source_run_id=ref.run_id, version=artifact.version))
        req.artifact_refs = refs
        run.staged['history_artifacts'] = [r.model_dump() for r in refs]
        run_store().save(run)
        job_queue().enqueue(run.run_id, req.model_dump())
        if WORKER_MODE == 'external':
            return {"run_id": run.run_id, "status": runtime.STATUS_CREATED, "task_fp": fp, "queued": True}
        thread = threading.Thread(target=_bounded_run_worker, args=(run.run_id, req),
                                  name=f"run-{run.run_id}", daemon=True)
        with _STATE_LOCK:
            _RUN_THREADS[run.run_id] = thread
        thread.start()
    except Exception:
        with _STATE_LOCK:
            _RUN_THREADS.pop(run.run_id, None)
        if WORKER_MODE != 'external':
            _RUN_SLOTS.release()
        raise
    return {"run_id": run.run_id, "status": runtime.STATUS_CREATED, "task_fp": fp}


@app.get("/api/runs")
def list_runs(request: Request, limit: int = Query(default=50, ge=1, le=200),
              task_fp: str | None = Query(default=None, max_length=64),
              offset: int = Query(default=0, ge=0, le=100000),
              q: str = Query(default="", max_length=200),
              status: str | None = Query(default=None, max_length=32)) -> Any:
    """Run 列表（不覆盖历史；同任务用 task_fp 分组）。"""
    if status and status not in {runtime.STATUS_CREATED, runtime.STATUS_RETRIEVING,
                                runtime.STATUS_ORCHESTRATING, runtime.STATUS_EXECUTING,
                                runtime.STATUS_VERIFYING, runtime.STATUS_EVOLVING, *TERMINAL}:
        raise HTTPException(422, "未知的运行状态")
    return run_store().list_page(limit=limit, offset=offset, task_fp=task_fp, q=q, status=status,
                                identity=getattr(request.state, 's1_identity', None))


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
    job_queue().cancel(run_id)
    BUS.publish(run, "run.cancel_requested")
    if run.status == runtime.STATUS_CREATED:
        run.status = STATUS_CANCELLED
        run.ended_at_ms = now_ms()
        BUS.publish(run, 'run.cancelled', reason='队列中取消，未执行模型调用')
    run_store().save(run)
    return {"run_id": run_id, "status": "CANCEL_REQUESTED"}


@app.get('/api/runs/{run_id}/evidence', dependencies=[Depends(require_token)])
def run_evidence(run_id: str):
    from skillnet.evidence import capsule
    run = run_store().get(run_id)
    if run is None:
        raise HTTPException(404, 'Run 不存在')
    return capsule(run, config.OUT_DIR/'runs'/run_id)


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request,
                     after: int = Query(default=0, ge=0)) -> Any:
    """SSE 事件流：实时推送该 Run 的 TraceEvent（支持断线重连回放已落盘事件）。"""
    store = run_store()
    run = store.get(run_id)
    if run is None:
        raise HTTPException(404, "Run 不存在")
    last_id = request.headers.get("Last-Event-ID", "")
    if last_id:
        if not last_id.isdigit() or len(last_id) > 12:
            raise HTTPException(400, "非法的事件游标")
        after = max(after, int(last_id))

    async def gen():
        cursor = after
        current = run
        heartbeat_at = time.monotonic()
        while True:
            if WORKER_MODE == 'external':
                refreshed = store.load(run_id)
                if refreshed is not None:
                    # The worker owns mutations; the API observes atomic checkpoints.
                    current = refreshed
            # 回放与实时均使用同一游标快照：发布发生在 yield 期间，也会在下次
            # 轮询补上；无「回放完成 → 注册订阅」之间的事件丢失窗口。
            for ev in BUS.replay(current, cursor):
                yield f"id: {ev.seq}\ndata: {json.dumps(ev.to_dict(), ensure_ascii=False)}\n\n"
                cursor = ev.seq
            with _STATE_LOCK:
                worker_alive = run_id in _RUN_THREADS
            if current.status in TERMINAL and not BUS.replay(current, cursor):
                if not worker_alive or any(e.type == "run.finished" and e.seq <= cursor for e in current.events):
                    yield "event: end\ndata: {}\n\n"
                    break
            if await request.is_disconnected():
                break
            if time.monotonic() - heartbeat_at >= 15:
                yield ": keep-alive\n\n"
                heartbeat_at = time.monotonic()
            await asyncio.sleep(0.15)             # 长连接不占用同步请求线程池

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})


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
    from skillnet.schema import QUALITY_DIMENSIONS, Skill

    # The capability proof performs a synthetic feedback update. Use detached
    # skills so reading this endpoint cannot train or dirty the live library.
    lib_ = SkillLibrary([Skill.from_dict(s.to_dict()) for s in lib()])
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
    if not name or len(name) > 120 or name in (".", "..") or re.search(r"[/\\:\x00-\x1f\x7f]", name):
        raise HTTPException(400, "非法的文件名")
    base = (config.OUT_DIR / "runs" / run_id / "artifacts").resolve()
    target = (base / name).resolve()
    if base not in target.parents or not target.is_file():
        if base.is_dir():
            stem = re.sub(r"^step\d+_", "", name)
            for cand in sorted(base.iterdir()):
                if (re.sub(r"^step\d+_", "", cand.name) == stem
                        and cand.is_file() and base in cand.resolve().parents):
                    target = cand.resolve()
                    break
    if base not in target.parents or not target.is_file():
        avail = sorted(p.name for p in base.glob("*"))[:20] if base.is_dir() else []
        hint = f"；可用产物：{avail}" if avail else "；该 Run 没有落盘产物"
        raise HTTPException(404, f"产物不存在（请求名 {name}）{hint}")
    return _artifact_response(target, target.name, bool(download))


@app.get("/api/config")
def api_config() -> dict[str, Any]:
    return {
        "model": config.MODEL,
        "price_in": config.PRICE_IN,
        "price_out": config.PRICE_OUT,
        "domains": sorted({s.domain for s in lib()}),
        "modes": ["bm25", "hybrid", "fabric"],
    }
