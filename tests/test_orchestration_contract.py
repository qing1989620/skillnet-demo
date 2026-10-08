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
def library():
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
