"""Model-output defenses and dependency invariants; no real LLM calls."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from skillnet.catalog import SkillLibrary
from skillnet.orchestrator import Orchestrator
from skillnet.retriever import Retriever
from skillnet.schema import Skill


@pytest.fixture
def library(monkeypatch):
    # Routing invariants must also hold on clean installs without an ONNX model.
    monkeypatch.setenv("SKILLNET_ENCODER", "lexical")
    return SkillLibrary([
        Skill(name="input-data", description="单细胞输入数据与质量控制", domain="生物", capability="单细胞输入数据"),
        Skill(name="analyze-data", description="单细胞分析模型", domain="生物", capability="单细胞分析",
              relations=[("depend_on", "input-data")]),
        Skill(name="write-report", description="分析报告", domain="写作", capability="撰写分析报告"),
    ])


@pytest.mark.parametrize("output", [[], None, "broken", {"workflow": "a->b"},
                                      {"workflow": [["input-data"], None, 123, [[], {}]]}])
def test_malformed_llm_output_keeps_relation_order(library, monkeypatch, output):
    monkeypatch.setattr("skillnet.orchestrator.chat_json", lambda *args, **kwargs: output)
    result = Orchestrator(library).build_with_llm("单细胞分析", ["analyze-data", "input-data"])
    assert result["skills"] == ["input-data", "analyze-data"]
    assert result["workflow"] == [["input-data", "analyze-data"]]
    assert result["degraded"] is True


def test_model_cycle_cannot_displace_known_prerequisite(library):
    result = Orchestrator(library).merge_workflow(["analyze-data", "input-data"], [
        ["analyze-data", "input-data"], ["input-data", "analyze-data"],
        ["missing", "input-data"], ["input-data", "input-data"],
    ])
    assert result["workflow"] == [["input-data", "analyze-data"]]
    assert result["cycles_broken"] == [["analyze-data", "input-data"]]
    assert result["invalid_edges"] == 2


def test_valid_new_model_edge_changes_topological_order(library):
    result = Orchestrator(library).merge_workflow(["input-data", "analyze-data", "write-report"], [
        ["analyze-data", "write-report"], ["analyze-data", "write-report"],
    ])
    assert result["skills"] == ["input-data", "analyze-data", "write-report"]
    assert result["degraded"] is False
    assert len(result["workflow"]) == 2


@pytest.mark.parametrize("output", [None, [], "broken", {"skills": [[], {}, 123, "unknown"]}])
def test_explorer_invalid_output_falls_back_observably(library, monkeypatch, output):
    monkeypatch.setattr("skillnet.retriever.chat_json", lambda *args, **kwargs: output)
    result = Retriever(library).build().route_with_wiki("单细胞分析", k=2)
    assert result["skills"] and len(result["skills"]) <= 2
    assert all(isinstance(name, str) and library.get(name) for name in result["skills"])
    assert result["degraded"] is True
    assert result["degraded_reason"]


def test_explorer_edges_only_reference_selected_skills(library, monkeypatch):
    monkeypatch.setattr("skillnet.retriever.chat_json", lambda *args, **kwargs: {
        "skills": ["input-data", "analyze-data", "input-data"],
        "workflow": [["analyze-data", "write-report"], ["analyze-data", "input-data"]],
        "reason": ["invalid reason type"],
        "decisions": [None, {"name": []}, {"name": {}}, {"name": "unknown", "reason": "invalid"},
                      {"name": "input-data", "reason": "读取源数据"}],
    })
    result = Retriever(library).build().route_with_wiki("单细胞分析报告", k=2)
    assert result["skills"] == ["input-data", "analyze-data"]
    assert result["order"] == ["input-data", "analyze-data"]
    assert result["workflow"] == [["input-data", "analyze-data"]]
    assert result["reason"] == ""
    assert result["decisions"] == [{"name": "input-data", "selected": True, "reason": "读取源数据"}]
    assert result["degraded"] is True


def test_bm25_does_not_claim_unexecuted_retrieval_channels(library):
    result = Retriever(library).build().search("单细胞", mode="bm25")
    assert all(candidate.channels == ["bm25"] for candidate in result.candidates)
    assert result.to_dict()["confidence_kind"] == "heuristic_relevance_not_probability"


def test_utility_selection_does_not_refill_rejected_skills(library, monkeypatch):
    monkeypatch.setattr("skillnet.retriever.config.API_KEY", "test")
    monkeypatch.setattr("skillnet.retriever.chat_json", lambda *a, **k: {
        "skills": ["input-data", "input-data"],
        "decisions": [{"name":"input-data", "reason":"只需读取源数据"},
                      {"name":"write-report", "reason":"本题没有报告交付要求"}],
    })
    result = Retriever(library).build().search("读取单细胞输入数据", k=2)
    assert result.selected == ["input-data"]
    assert len(result.candidates) > len(result.selected)
    assert result.selection["method"] == "task_utility"
    assert result.selection["library_size"] == 3
    assert not result.selection["abstained"]
    card = next(c for c in result.to_dict()["candidates"] if c["name"] == "input-data")
    assert card["capability"] == "单细胞输入数据"
    assert card["note"] == "只需读取源数据"


def test_explicit_utility_abstention_preserves_candidates(library, monkeypatch):
    monkeypatch.setattr("skillnet.retriever.config.API_KEY", "test")
    monkeypatch.setattr("skillnet.retriever.chat_json", lambda *a, **k: {"skills":[], "decisions":[]})
    result = Retriever(library).build().search("读取单细胞输入数据", k=2)
    assert result.selected == []
    assert result.candidates
    assert result.selection["abstained"]
    assert result.components["llm_rerank"]
    assert result.decision == "direct"


@pytest.mark.parametrize("output", [None, {}, [], {"skills":"input-data"}, {"skills":["unknown"]}, {"skills":[{}]}])
def test_malformed_utility_call_is_fallback_not_abstention(library, monkeypatch, output):
    monkeypatch.setattr("skillnet.retriever.config.API_KEY", "test")
    monkeypatch.setattr("skillnet.retriever.chat_json", lambda *a, **k: output)
    result = Retriever(library).build().search("读取单细胞输入数据", k=2)
    assert len(result.selected) == 2
    assert result.selection["method"] == "score_fallback"
    assert not result.selection["abstained"]
    assert result.degraded


def test_wiki_reuses_frozen_pool_and_honors_zero_selection(library, monkeypatch):
    monkeypatch.setattr("skillnet.retriever.chat_json", lambda *a, **k: {"skills":[], "workflow":[], "reason":"不需要"})
    router = Retriever(library)
    monkeypatch.setattr(router, "search", lambda *a, **k: pytest.fail("must not perform another retrieval"))
    result = router.route_with_wiki("当前问题", candidate_names=["input-data","unknown","input-data"], k=2)
    assert result["candidate_names"] == ["input-data"]
    assert result["skills"] == []
    assert result["order"] == []
    assert not result["degraded"]


def test_server_does_not_replace_explicit_empty_selection(library, monkeypatch):
    import server
    monkeypatch.setitem(server.STATE, "orchestrator", Orchestrator(library))
    assert server._resolve_orchestration({"skills":[]}, ["input-data"])["skills"] == []
    assert server._resolve_orchestration({}, ["input-data"])["skills"] == ["input-data"]
