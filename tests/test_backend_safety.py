"""Regression checks for concurrency, budget boundaries, SSE recovery and artifact safety.

No provider calls are made: HTTP transports, planning and executable steps are controlled
at their real integration boundaries so request accounting and scheduling remain exercised.
"""
from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

import server
from skillnet import llm, pipeline, runtime
from skillnet.bandit import SharedLinUCB
from skillnet.catalog import SkillLibrary
from skillnet.schema import Skill
from skillnet.orchestrator import Orchestrator


@pytest.fixture
def api(tmp_path, monkeypatch):
    store = runtime.RunStore(tmp_path / "runs")
    monkeypatch.setattr(server, "STATE", {"lib": [], "run_store": store})
    monkeypatch.setattr(server, "ACCESS_TOKEN", "test-access-token")
    monkeypatch.setattr(server, "_RUN_THREADS", {})
    monkeypatch.setattr(server.config, "OUT_DIR", tmp_path)
    client = TestClient(server.app)
    yield client, store
    client.close()


def make_run(run_id="regression-run", **kwargs):
    return runtime.Run(run_id=run_id, task="计算示例数据均值", task_fp="regression", **kwargs)


def test_history_api_filters_paginates_and_preserves_legacy_runs_key(api):
    client, store = api
    for i in range(3):
        run = make_run(f"history-{i}", started_at_ms=100+i, status="COMPLETED" if i else "FAILED")
        store.save(run)
    page = client.get("/api/runs?limit=1&offset=1&status=COMPLETED&q=示例").json()
    assert page["total"] == 2 and page["runs"][0]["run_id"] == "history-1"
    assert page["summary"]["completed"] == 2 and not page["has_more"]
    assert len(client.get("/api/runs").json()["runs"]) == 3


def test_policy_proof_is_authenticated_and_does_not_expose_or_mutate_weights(api, monkeypatch):
    client,_ = api
    library = SkillLibrary([Skill('proof','test','data')])
    bandit = SharedLinUCB(library)
    monkeypatch.setattr(server,'_bandit',lambda:bandit)
    before = bandit.state_dict()
    assert client.get('/api/learning/policy').status_code == 401
    response = client.get('/api/learning/policy',headers={'X-SkillNet-Token':'test-access-token'})
    assert response.status_code == 200
    data = response.json()
    assert data['updates'] == 0 and len(data['state_sha256']) == 64
    assert data['single_run_updates_serving_policy'] is False
    assert 'A' not in data and 'b' not in data and bandit.state_dict() == before


def test_reward_policy_is_authenticated_versioned_and_uses_and_for_all_twelve_gates(api):
    from skillnet import reward_gates
    client,_=api
    assert client.get('/api/learning/reward-policy').status_code==401
    data=client.get('/api/learning/reward-policy',headers={'X-SkillNet-Token':'test-access-token'}).json()
    assert data['sha256']==reward_gates.policy_sha256()
    assert data['policy']['operator']=='AND' and data['policy']['unknown_blocks'] is True
    assert len(data['policy']['gates'])==12


@pytest.mark.parametrize("query", ["offset=-1", "offset=100001", "status=UNKNOWN", "q="+"x"*201])
def test_history_api_rejects_invalid_filters(api, query):
    client, _ = api
    assert client.get("/api/runs?"+query).status_code == 422


@pytest.mark.parametrize("execution,steps", [({"final_ok":False},1), ({"final_ok":True},3),
    ({"final_ok":True,"verification":[{"passed":False}]},1),
    ({"final_ok":"false"},1), ({"final_ok":True,"verification":[{"passed":"true"}]},1)])
def test_single_step_experiment_cannot_train_from_failed_or_incomplete_evidence(execution, steps):
    reward, reason = server._demo_learning_reward({"weighted":9,"score_valid":True}, execution, steps)
    assert reward is None and reason


def test_input_copy_failure_does_not_emit_false_provenance_or_call_model(tmp_path, monkeypatch):
    source = tmp_path / "artifacts"
    source.mkdir()
    (source / "step1_data.csv").write_text("x\n1\n", encoding="utf-8")
    run = make_run()
    run.artifacts = [runtime.Artifact(name="step1_data.csv", from_step=0)]
    step = runtime.RunStep(idx=1, action="read", depends_on=[0])
    monkeypatch.setattr(pipeline, "_copy_retry", lambda *a: False)
    monkeypatch.setattr(pipeline.llm, "chat", lambda *a, **k: pytest.fail("input failure consumed model budget"))
    with pytest.raises(OSError, match="无法复制上游产物"):
        pipeline.run_step(run, step, None, tmp_path, run.budget, ["step1_data.csv"])
    assert not step.input_artifacts and not any(e.type=="step.inputs" for e in run.events)


def test_parallel_completion_order_does_not_select_input_versions(tmp_path, monkeypatch):
    seen = []
    run = make_run()
    run.steps = [runtime.RunStep(idx=0, action="root", status="done"),
                 runtime.RunStep(idx=1, action="derived", status="done", depends_on=[0]),
                 runtime.RunStep(idx=2, action="consume", depends_on=[0,1])]
    # Simulate later checkpoints appending older producer after newer producer.
    run.artifacts = [runtime.Artifact(name="step2_data.csv", from_step=1),
                     runtime.Artifact(name="step1_data.csv", from_step=0)]
    def fake_step(run, step, lib, workspace, budget, upstream, **kwargs):
        if step.idx==2:seen.extend(upstream)
        step.status="done"
    monkeypatch.setattr(pipeline, "run_step", fake_step)
    pipeline._run_steps_graph(run, tmp_path, None, run.budget)
    assert seen == ["step1_data.csv","step2_data.csv"]


def test_concurrent_persistence_has_no_shared_temporary_file(tmp_path):
    store = runtime.RunStore(tmp_path)
    run = make_run()
    barrier = threading.Barrier(8)
    def save_many(_):
        barrier.wait(timeout=5)
        for _ in range(8):
            store.save(run)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(save_many, range(8)))
    assert json.loads((tmp_path / f"{run.run_id}.json").read_text("utf-8"))["run_id"] == run.run_id
    assert not list(tmp_path.glob("*.tmp"))


def test_live_summary_overrides_stale_disk_and_budget_survives_restart(tmp_path):
    store = runtime.RunStore(tmp_path)
    run = make_run()
    run.budget = runtime.Budget(max_cost_yuan=0.25, max_llm_calls=7, max_seconds=90)
    run.cancel_requested = True
    store.save(run)
    run.status = runtime.STATUS_EXECUTING
    assert store.list_recent()[0]["status"] == runtime.STATUS_EXECUTING
    restored = runtime.RunStore(tmp_path).get(run.run_id)
    assert restored.budget.max_llm_calls == 7
    assert restored.budget.max_cost_yuan == 0.25
    assert restored.cancel_requested
    assert store.get("../outside") is None


def test_parallel_steps_keep_request_ledger_context(tmp_path, monkeypatch):
    llm.LEDGER.reset()
    ledger = llm.UsageLedger()
    def fake_chat(*args, **kwargs):
        llm.current_ledger().record("executor", 100, 25)
        return "print('ok')"
    monkeypatch.setattr(llm, "chat", fake_chat)
    monkeypatch.setattr(pipeline.sandbox, "available_stack", lambda: {})
    monkeypatch.setattr(pipeline.sandbox, "run_python", lambda *a, **k: {
        "ok": True, "stdout": "ok", "stderr": "", "duration": 0.01, "artifacts": []})
    run = make_run()
    plan = {"steps": [{"skill": s, "action": "计算数据"} for s in "ABCD"]}
    with llm.ledger_scope(ledger):
        pipeline.execute_run(run, None, tmp_path / "workspace", plan, max_steps=4,
                             workflow=[["A", "B"], ["A", "C"], ["B", "D"], ["C", "D"]])
    assert ledger.calls == run.llm_calls == 4
    assert run.tokens == 500
    assert llm.LEDGER.calls == 0
    assert len(run.steps) == 4
    assert [step.stages["llm_calls"] for step in run.steps] == [1, 1, 1, 1]


def test_artifact_inputs_follow_dependencies_and_exclude_sibling_branch(tmp_path, monkeypatch):
    class SerialPool(ThreadPoolExecutor):
        def __init__(self, **kwargs):
            super().__init__(max_workers=1)
    monkeypatch.setattr(pipeline, "ThreadPoolExecutor", SerialPool)
    seen = {}
    def fake_step(run, step, lib, workspace, budget, upstream, **kwargs):
        seen[step.idx] = upstream
        run.artifacts.append(runtime.Artifact(name=f"step{step.idx + 1}.csv", from_step=step.idx))
        step.status = runtime.STEP_DONE
    monkeypatch.setattr(pipeline, "run_step", fake_step)
    run = make_run()
    run.steps = [runtime.RunStep(idx=0, action="root"),
                 runtime.RunStep(idx=1, action="left", depends_on=[0]),
                 runtime.RunStep(idx=2, action="right", depends_on=[0]),
                 runtime.RunStep(idx=3, action="merge", depends_on=[1, 2])]
    pipeline._run_steps_graph(run, tmp_path, None, run.budget)
    assert seen[1] == seen[2] == ["step1.csv"]
    assert set(seen[3]) == {"step1.csv", "step2.csv", "step3.csv"}


def test_cancel_after_code_generation_prevents_execution(tmp_path, monkeypatch):
    run = make_run()
    def cancel_chat(*args, **kwargs):
        run.cancel_requested = True
        return "print('should not execute')"
    monkeypatch.setattr(llm, "chat", cancel_chat)
    monkeypatch.setattr(pipeline.sandbox, "available_stack", lambda: {})
    monkeypatch.setattr(pipeline.sandbox, "run_python", lambda *a, **k: pytest.fail("cancelled code executed"))
    with llm.ledger_scope(), pytest.raises(runtime.RunCancelled):
        pipeline.execute_run(run, None, tmp_path / "workspace", {"steps": [{"action": "计算数据"}]})
    assert run.status == runtime.STATUS_CANCELLED
    assert run.steps[0].status == runtime.STEP_SKIPPED


def test_cancelled_worker_persists_terminal_event_without_retrieval(api, monkeypatch):
    _, store = api
    run = make_run()
    run.cancel_requested = True
    store.save(run)
    server.STATE["retriever"] = SimpleNamespace(search=lambda *a, **k: pytest.fail("cancelled run retrieved"))
    server._run_worker(run.run_id, server.RunReq(task=run.task))
    loaded = store.load(run.run_id)
    assert loaded.status == runtime.STATUS_CANCELLED
    assert loaded.events[-1].type == "run.finished"
    assert loaded.events[-1].data["status"] == runtime.STATUS_CANCELLED


def mock_provider(monkeypatch, handler):
    client = httpx.Client(base_url="https://provider.test", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(llm.config, "API_KEY", "test-provider-key")
    monkeypatch.setattr(llm, "_get_client", lambda: client)
    return client


def provider_completion(content="ok"):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}],
                                    "usage": {"prompt_tokens": 100, "completion_tokens": 25}})


def test_worker_stops_at_cost_boundary_before_planning(api, monkeypatch):
    _, store = api
    run = make_run()
    run.budget.max_cost_yuan = 0.00001
    store.save(run)
    calls = []
    client = mock_provider(monkeypatch, lambda request: (calls.append(request) or provider_completion()))
    def search(*a, **k):
        llm.chat([{"role": "user", "content": "rerank"}])
        pytest.fail("budget guard did not interrupt retrieval")
    server.STATE["retriever"] = SimpleNamespace(search=search)
    try:
        server._run_worker(run.run_id, server.RunReq(task=run.task))
    finally:
        client.close()
    loaded = store.load(run.run_id)
    assert loaded.status == runtime.STATUS_BUDGET_EXCEEDED
    assert loaded.llm_calls == 1 and loaded.tokens == 125
    assert len(calls) == 1
    assert not loaded.plan and not loaded.evolution
    assert loaded.events[-1].type == "run.finished"


def test_final_report_is_included_in_run_cost(api, monkeypatch):
    _, store = api
    run = make_run()
    store.save(run)
    llm.LEDGER.reset()
    client = mock_provider(monkeypatch, lambda request: provider_completion("报告已生成"))
    class Retrieval:
        def to_dict(self):
            return {"selected": [], "trace": []}
    server.STATE.update({
        "retriever": SimpleNamespace(search=lambda *a, **k: Retrieval(),
                                      route_with_wiki=lambda *a, **k: {"skills": [], "workflow": []}),
        "orchestrator": SimpleNamespace(merge_workflow=lambda *a, **k: {"skills": [], "workflow": []}),
        "agent": SimpleNamespace(run=lambda *a, **k: SimpleNamespace(response={"steps": [{"action": "计算数据"}]}, trajectory=[])),
    })
    monkeypatch.setattr(server, "_bandit", lambda: SimpleNamespace(rank=lambda *a, **k: [], update=lambda *a: None))
    monkeypatch.setattr(server, "score_plan", lambda *a: {"weighted": 5})
    monkeypatch.setattr(server, "SkillEvolver", lambda *a: SimpleNamespace(distill=lambda *a, **k: None, summary=lambda: {"records": []}))
    def execute(run, *a, **k):
        run.steps = [runtime.RunStep(idx=0, action="计算数据", status=runtime.STEP_DONE)]
    monkeypatch.setattr(pipeline, "execute_run", execute)
    try:
        server._run_worker(run.run_id, server.RunReq(task=run.task))
    finally:
        client.close()
    loaded = store.load(run.run_id)
    assert loaded.status == runtime.STATUS_COMPLETED
    assert loaded.llm_calls == 1 and loaded.tokens == 125
    assert loaded.cost_yuan > 0
    assert loaded.staged["final_reply"] == "报告已生成"
    assert llm.LEDGER.calls == 0
    assert [e.type for e in loaded.events][-3:] == ["run.reply", "evaluation.gates_updated", "run.finished"]
    assert loaded.staged['reward_gates']['gates'][3]['evidence']['cost_yuan']==loaded.cost_yuan


def test_sse_reconnect_uses_persisted_cursor_after_event_truncation(api):
    client, store = api
    run = make_run(status=runtime.STATUS_COMPLETED)
    for _ in range(450):
        runtime.BUS.publish(run, "progress")
    store.save(run)
    server.STATE["run_store"] = runtime.RunStore(store.root)
    response = client.get(f"/api/runs/{run.run_id}/stream", headers={"Last-Event-ID": "449"})
    assert response.status_code == 200
    assert "id: 450\n" in response.text and "id: 449\n" not in response.text
    assert response.text.count("data: ") == 2   # one new event plus terminal end
    assert "event: end" in response.text
    assert client.get(f"/api/runs/{run.run_id}/stream", headers={"Last-Event-ID": "invalid"}).status_code == 400


def test_sse_publishing_during_replay_loses_no_event(api):
    _, store = api
    run = make_run()
    store.put(run)
    runtime.BUS.publish(run, "first")
    class Request:
        headers = {}
        async def is_disconnected(self):
            return False
    async def consume():
        response = await server.stream_run(run.run_id, Request(), after=0)
        it = response.body_iterator
        first = await anext(it)
        runtime.BUS.publish(run, "second")
        second = await anext(it)
        run.status = runtime.STATUS_COMPLETED
        runtime.BUS.publish(run, "run.finished")
        third = await anext(it)
        end = await anext(it)
        await it.aclose()
        return first, second, third, end
    chunks = asyncio.run(consume())
    assert [f"id: {n}" in chunks[n - 1] for n in (1, 2, 3)] == [True] * 3
    assert "event: end" in chunks[3]


def test_paid_search_requires_token_but_local_search_remains_available(api):
    client, _ = api
    result = SimpleNamespace(candidates=[], to_dict=lambda: {"selected": []})
    server.STATE["retriever"] = SimpleNamespace(search=lambda *a, **k: result)
    request = {"query": "数据分析", "modes": ["fabric"]}
    assert client.post("/api/search", json=request).status_code == 401
    assert client.post("/api/search", json=request, headers={"Authorization": "Bearer test-access-token"}).status_code == 200
    request["modes"] = ["bm25", "hybrid"]
    assert client.post("/api/search", json=request).status_code == 200


def test_capacity_rejects_before_starting_new_worker(api, monkeypatch):
    client, store = api
    slots = threading.BoundedSemaphore(1)
    slots.acquire()
    monkeypatch.setattr(server, "_RUN_SLOTS", slots)
    monkeypatch.setattr(server, "require_llm", lambda: None)
    response = client.post("/api/runs", json={"task": "计算数据"}, headers={"X-SkillNet-Token": "test-access-token"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "10"
    assert response.headers["x-request-id"]
    assert not store.list_recent()


def test_performance_write_requires_token_and_valid_numeric_metrics(api):
    client, store = api
    run = make_run()
    store.save(run)
    path = f"/api/runs/{run.run_id}/perf"
    assert client.post(path, json={"data": {"ttfe": 25}}).status_code == 401
    auth = {"X-SkillNet-Token": "test-access-token"}
    assert client.post(path, json={"data": {"ttfe": -1}}, headers=auth).status_code == 422
    assert client.post(path, json={"data": {"ttfe": {"nested": 1}}}, headers=auth).status_code == 422
    assert client.post(path, json={"data": {"ttfe": 25}}, headers=auth).status_code == 200
    assert store.load(run.run_id).events[-1].seq == 1


def test_artifact_binary_download_and_active_content_sandbox(api, tmp_path):
    client, _ = api
    directory = tmp_path / "runs" / "regression-run" / "artifacts"
    directory.mkdir(parents=True)
    binary = b"PK\x03\x04\xff\x00\x81test-binary"
    (directory / "step1_report.xlsx").write_bytes(binary)
    (directory / "step1_preview.html").write_text("<script>fetch('/api/runs')</script>", encoding="utf-8")
    base = "/api/runs/regression-run/artifacts"
    response = client.get(f"{base}/report.xlsx?download=1")
    assert response.content == binary
    assert "attachment" in response.headers["content-disposition"]
    response = client.get(f"{base}/preview.html")
    assert "sandbox;" in response.headers["content-security-policy"]
    assert "allow-scripts" not in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get(f"{base}/*").status_code == 404


def test_llm_does_not_retry_invalid_credentials(monkeypatch):
    calls = []
    client = mock_provider(monkeypatch, lambda request: (calls.append(request) or httpx.Response(401, text="secret upstream body")))
    try:
        with pytest.raises(llm.LLMError, match="HTTP 401") as exc:
            llm.chat([{"role": "user", "content": "test"}])
    finally:
        client.close()
    assert len(calls) == 1
    assert "secret upstream" not in str(exc.value)


def test_llm_guard_cancels_before_network_without_retry(monkeypatch):
    client = mock_provider(monkeypatch, lambda request: pytest.fail("cancelled request reached provider"))
    def cancel():
        raise runtime.RunCancelled("cancelled")
    try:
        with llm.guard_scope(cancel), pytest.raises(runtime.RunCancelled):
            llm.chat([{"role": "user", "content": "test"}])
    finally:
        client.close()


def test_invalid_history_payload_is_rejected_before_work(api):
    client, _ = api
    response = client.post("/api/runs", json={"task": "计算数据", "history": [{"q": {"nested": "large"}}]},
                           headers={"X-SkillNet-Token": "test-access-token"})
    assert response.status_code == 422


def test_run_list_page_size_is_bounded(api):
    client, _ = api
    assert client.get("/api/runs?limit=0").status_code == 422
    assert client.get("/api/runs?limit=201").status_code == 422


def test_readonly_token_check_supports_both_header_formats(api):
    client, store = api
    assert client.get("/api/auth/check").status_code == 401
    assert client.get("/api/auth/check", headers={"X-SkillNet-Token": "wrong"}).status_code == 401
    for auth in ({"X-SkillNet-Token": "test-access-token"}, {"Authorization": "Bearer test-access-token"}):
        response = client.get("/api/auth/check", headers=auth)
        assert response.status_code == 200 and response.json() == {"ok": True, "token_required": True}
    assert not store.list_recent()


def test_blank_tasks_and_repeated_search_modes_are_rejected(api):
    client, _ = api
    server.STATE["retriever"] = object()
    auth = {"X-SkillNet-Token": "test-access-token"}
    assert client.post("/api/runs", json={"task": "  \n  "}, headers=auth).status_code == 422
    assert client.post("/api/search", json={"query": "数据", "modes": ["fabric"] * 4}, headers=auth).status_code == 422
    assert client.post("/api/search", json={"query": "数据", "modes": ["fabric"] * 2}, headers=auth).status_code == 422


def test_concurrent_policy_feedback_preserves_all_updates():
    library = SkillLibrary([Skill(name="sample-analysis", description="计算均值", domain="统计")])
    concurrent = SharedLinUCB(library)
    serial = SharedLinUCB(SkillLibrary([Skill(name="sample-analysis", description="计算均值", domain="统计")]))
    barrier = threading.Barrier(8)
    def update(_):
        barrier.wait(timeout=5)
        for _ in range(5):
            concurrent.update("计算数据均值", "sample-analysis", 0.75)
            concurrent.score("计算数据均值", "sample-analysis")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(update, range(8)))
    for _ in range(40):
        serial.update("计算数据均值", "sample-analysis", 0.75)
    assert concurrent.n_updates == 40
    assert library.get("sample-analysis").stats["pulls"] == 40
    assert np.allclose(concurrent.A, serial.A)
    assert np.allclose(concurrent.b, serial.b)


def test_runtime_refresh_keeps_policy_reference_and_inflight_feedback(monkeypatch):
    library = SkillLibrary([Skill(name="sample-analysis", description="计算均值", domain="统计")])
    policy = SharedLinUCB(library)
    policy.update("计算数据均值", "sample-analysis", 0.5)
    monkeypatch.setattr(server, "STATE", {"lib": library, "bandit": policy})
    monkeypatch.setattr(server, "Retriever", lambda lib: SimpleNamespace(build=lambda: "new-retriever"))
    monkeypatch.setattr(server, "Orchestrator", lambda lib: object())
    monkeypatch.setattr(server, "ResearchAgent", lambda lib: object())
    server.refresh_runtime()
    policy.update("计算数据均值", "sample-analysis", 0.75)  # reference held before refresh
    assert server.STATE["bandit"] is policy
    assert server.STATE["bandit"].n_updates == 2


def test_concurrent_library_saves_remain_atomic(tmp_path):
    library = SkillLibrary([Skill(name="sample-analysis", description="计算均值", domain="统计", source="distill")])
    target = tmp_path / "library.json"
    barrier = threading.Barrier(6)
    def save(_):
        barrier.wait(timeout=5)
        for _ in range(4):
            library.save(target)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(save, range(6)))
    assert json.loads(target.read_text("utf-8"))["evolved"][0]["name"] == "sample-analysis"
    assert not list(tmp_path.glob("*.tmp"))


@pytest.fixture
def routed_workflow(api):
    client, store = api
    library = SkillLibrary([
        Skill(name="input-data", description="生成数据", domain="统计"),
        Skill(name="z-analyze", description="分析数据", domain="统计", relations=[("depend_on", "input-data")]),
        Skill(name="a-report", description="输出报告", domain="统计"),
    ])
    workflow = [["input-data", "z-analyze"], ["z-analyze", "a-report"]]
    wiki = {"skills": ["a-report", "z-analyze", "input-data"],
            "workflow": workflow, "order": ["input-data", "z-analyze", "a-report"],
            "source": "relations+llm", "degraded": False}
    class Retrieval:
        def to_dict(self):
            return {"selected": wiki["skills"], "trace": []}
    server.STATE.update({"lib": library, "orchestrator": Orchestrator(library),
                         "retriever": SimpleNamespace(search=lambda *a, **k: Retrieval(),
                                                       route_with_wiki=lambda *a, **k: dict(wiki))})
    return client, store, wiki


def test_route_order_respects_validated_wiki_edges(routed_workflow, monkeypatch):
    client, _, wiki = routed_workflow
    monkeypatch.setattr(server, "require_llm", lambda: None)
    response = client.post("/api/route", json={"query": "生成、分析数据并输出报告"},
                           headers={"X-SkillNet-Token": "test-access-token"})
    assert response.status_code == 200
    assert set(map(tuple, response.json()["workflow"])) == set(map(tuple, wiki["workflow"]))
    assert response.json()["order"] == wiki["order"]


def test_worker_executes_wiki_workflow_and_uses_its_order(routed_workflow, monkeypatch):
    _, store, wiki = routed_workflow
    run = make_run()
    store.save(run)
    planned_skills = []
    executed_workflow = []
    def plan(task, *, skills, **kwargs):
        planned_skills.extend(skills)
        return SimpleNamespace(response={"steps": [{"action": "计算数据", "skill": name} for name in skills]}, trajectory=[])
    server.STATE["agent"] = SimpleNamespace(run=plan)
    monkeypatch.setattr(server, "_bandit", lambda: SimpleNamespace(rank=lambda *a, **k: [], update=lambda *a: None))
    monkeypatch.setattr(server, "score_plan", lambda *a: {"weighted": 5})
    monkeypatch.setattr(server, "SkillEvolver", lambda *a: SimpleNamespace(distill=lambda *a, **k: None, summary=lambda: {"records": []}))
    monkeypatch.setattr(server, "persist_library", lambda: None)
    monkeypatch.setattr(server, "_compose_final_reply", lambda *a: "已完成")
    def execute(run, lib, workspace, plan, *, workflow, **kwargs):
        executed_workflow.extend(workflow)
        run.steps = pipeline.build_steps(plan, workflow)
        for step in run.steps:
            step.status = runtime.STEP_DONE
    monkeypatch.setattr(pipeline, "execute_run", execute)
    server._run_worker(run.run_id, server.RunReq(task=run.task))
    loaded = store.load(run.run_id)
    assert loaded.status == runtime.STATUS_COMPLETED
    assert planned_skills == loaded.skills == wiki["order"]
    assert set(map(tuple, executed_workflow)) == set(map(tuple, wiki["workflow"]))
    assert [step.depends_on for step in loaded.steps] == [[], [0], [1]]
    assert loaded.staged["orchestration"]["order"] == wiki["order"]
    event = next(e for e in loaded.events if e.type == "orchestration.completed")
    assert event.data["order"] == wiki["order"]
    assert set(map(tuple, event.data["edges"])) == set(map(tuple, wiki["workflow"]))


def test_lifespan_runs_existing_startup_and_recovery_in_order(monkeypatch,tmp_path):
    calls = []
    monkeypatch.setattr(server.config,'OUT_DIR',tmp_path)
    monkeypatch.setattr(server, "_startup", lambda: calls.append("startup"))
    monkeypatch.setattr(server, "_startup_sweep", lambda: calls.append("recovery"))
    with TestClient(server.app):
        assert calls == ["startup", "recovery"]
    assert calls == ["startup", "recovery"]


def test_report_prompt_distinguishes_pre_report_usage_from_final_metrics(monkeypatch):
    captured = []
    def chat(messages, **kwargs):
        captured.append(messages[1]["content"])
        return "报告"
    monkeypatch.setattr(llm, "chat", chat)
    run = make_run()
    run.cost_yuan = 0.09
    run.tokens = 125
    assert server._compose_final_reply(run, None) == "报告"
    assert "报告生成前累计（不是最终运行总额）" in captured[0]
    assert "正文不要报告总成本、总 Token 或总耗时" in captured[0]
    assert "最终值由界面的结构化运行指标展示" in captured[0]


@pytest.mark.parametrize("evaluation, expected_reward, expected_coverage", [
    ({"weighted": 0.0, "score_valid": False, "coverage": 0.0, "coverage_valid": False}, None, None),
    ({"weighted": 8.0, "score_valid": True, "coverage": 0.0, "coverage_valid": False}, None, None),
    ({"weighted": 8.0, "coverage": 0.75}, None, 0.75),
])
def test_worker_keeps_plan_advice_but_never_learns_unmeasured_results(
        routed_workflow, monkeypatch, evaluation, expected_reward, expected_coverage):
    _, store, wiki = routed_workflow
    run = make_run()
    store.save(run)
    updates, admissions = [], []
    server.STATE["agent"] = SimpleNamespace(run=lambda *a, **k: SimpleNamespace(
        response={"steps": [{"action": "计算数据", "skill": "input-data"}]}, trajectory=[]))
    monkeypatch.setattr(server, "_bandit", lambda: SimpleNamespace(
        rank=lambda task, names: [(name, 1.0, 0.5, 0.5) for name in names],
        update=lambda task, name, reward: updates.append((name, reward))))
    monkeypatch.setattr(server, "score_plan", lambda *a: dict(evaluation))
    def distill(*args, **kwargs):
        admissions.append(kwargs["score"])
        return None
    monkeypatch.setattr(server, "SkillEvolver", lambda *a: SimpleNamespace(
        distill=distill, summary=lambda: {"records": []}))
    monkeypatch.setattr(server, "persist_library", lambda: None)
    monkeypatch.setattr(server, "_compose_final_reply", lambda *a: "完成")
    def execute(run, *args, **kwargs):
        run.steps = [runtime.RunStep(idx=0, action="计算数据", skill="input-data", status=runtime.STEP_DONE)]
    monkeypatch.setattr(pipeline, "execute_run", execute)
    server._run_worker(run.run_id, server.RunReq(task=run.task))
    loaded = store.load(run.run_id)
    assert loaded.status == runtime.STATUS_COMPLETED
    assert loaded.judge["coverage"] == expected_coverage
    event = next(e for e in loaded.events if e.type == "judge.completed")
    assert event.data["coverage"] == expected_coverage
    assert event.data["reward"] == expected_reward
    if expected_reward is None:
        assert updates == admissions == []
        assert all(not row["nudged"] and row["skip_reason"] for row in loaded.feedback)
        assert loaded.evolution["skipped"] and loaded.evolution["skip_reason"]
        assert event.data["weighted"] == (evaluation['weighted'] if evaluation.get('score_valid', True) else None)
    assert loaded.staged['learning_gate']['mode'] == 'shadow'
    assert loaded.staged['quality_assessment']['scope_verdict'] == 'unknown'
    assert loaded.staged['quality_assessment']['overall_verdict'] == 'unconfirmed'


@pytest.mark.parametrize("gate", ["execution", "checks", "semantic"])
def test_valid_plan_score_cannot_reward_failed_or_rejected_execution(routed_workflow, monkeypatch, gate):
    _, store, _ = routed_workflow
    run = make_run()
    store.save(run)
    updates, admissions = [], []
    server.STATE["agent"] = SimpleNamespace(run=lambda *a, **k: SimpleNamespace(
        response={"steps": [{"action": "compute", "skill": "input-data"}]}, trajectory=[]))
    monkeypatch.setattr(server, "_bandit", lambda: SimpleNamespace(
        rank=lambda task, names: [(name, 1., .5, .5) for name in names],
        update=lambda *args: updates.append(args)))
    monkeypatch.setattr(server, "score_plan", lambda *a: {
        "weighted": 9., "score_valid": True, "coverage_valid": False})
    monkeypatch.setattr(server, "SkillEvolver", lambda *a: SimpleNamespace(
        distill=lambda *a, **k: admissions.append(k), summary=lambda: {"records": []}))
    monkeypatch.setattr(server, "persist_library", lambda: None)
    monkeypatch.setattr(server, "_compose_final_reply", lambda *a: "public demo")

    def execute(run, *args, **kwargs):
        step = runtime.RunStep(idx=0, action="compute", skill="input-data", status=runtime.STEP_DONE)
        if gate == "execution":
            step.status = runtime.STEP_FAILED
        elif gate == "checks":
            step.checks = [runtime.ProgrammaticCheck("CSV schema", False, "missing column")]
        else:
            step.verifications = [runtime.VerificationResult("required report", False, "missing evidence")]
        run.steps = [step]

    monkeypatch.setattr(pipeline, "execute_run", execute)
    server._run_worker(run.run_id, server.RunReq(task=run.task))
    result = store.load(run.run_id)
    assert not updates and not admissions
    assert result.judge["weighted"] == 9., "plan evaluation remains valid and independently visible"
    assert result.evolution["skipped"] and not result.evolution["accepted"]
    assert result.staged["learning_gate"]["eligible"] is False
    assert all(not f["nudged"] for f in result.feedback)
    event = next(e for e in result.events if e.type == "judge.completed")
    assert event.data["weighted"] == 9. and event.data["reward"] is None


def test_explicit_evolution_does_not_admit_unrated_trajectory(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(server, "require_llm", lambda: None)
    server.STATE["agent"] = SimpleNamespace(run=lambda *a, **k: SimpleNamespace(response={}, trajectory=[]))
    monkeypatch.setattr(server, "score_plan", lambda *a: {"weighted": 0.0, "score_valid": False})
    monkeypatch.setattr(server, "SkillEvolver", lambda *a: SimpleNamespace(
        distill=lambda *a, **k: pytest.fail("invalid evaluation entered skill admission"),
        summary=lambda: {"records": []}))
    response = client.post("/api/evolve", json={"task": "分析数据", "op": "distill"},
                           headers={"X-SkillNet-Token": "test-access-token"})
    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert response.json()["chat_score"] is None
    assert response.json()["skip_reason"]


def test_explicit_evolution_labels_a_plan_as_unexecuted_proposal(api, monkeypatch):
    client,_ = api
    monkeypatch.setattr(server,'require_llm',lambda:None)
    server.STATE['agent'] = SimpleNamespace(run=lambda *a,**k:SimpleNamespace(response={},trajectory='plan only'))
    monkeypatch.setattr(server,'score_plan',lambda *a:{'weighted':9.,'score_valid':True})
    seen=[]
    evolver=SimpleNamespace(distill=lambda *a,**k:seen.append(k),summary=lambda:{'records':[]})
    monkeypatch.setattr(server,'SkillEvolver',lambda *a:evolver)
    response=client.post('/api/evolve',json={'task':'生成方法提案','op':'distill'},
        headers={'X-SkillNet-Token':'test-access-token'})
    assert response.status_code==200
    data=response.json()
    assert data['chat_score']==.9 and data['score_role']=='plan_advisory'
    assert data['evidence_mode']=='unexecuted_proposal' and not data['network_updated']
    assert seen==[dict(score=None)]
    assert evolver.evidence_context['mode']=='unexecuted_proposal'
    assert not data['accepted']


def test_report_does_not_present_invalid_evaluation_as_real_low_score(monkeypatch):
    captured = []
    def chat(messages, **kwargs):
        captured.append(messages[1]["content"])
        return "报告"
    monkeypatch.setattr(llm, "chat", chat)
    run = make_run()
    run.judge = {"weighted": 0.0, "score_valid": False}
    server._compose_final_reply(run, None)
    assert "未获得有效评分，未用于反馈或技能准入" in captured[0]
    assert "语义评审加权 0.0/10" not in captured[0]
