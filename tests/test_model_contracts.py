"""Malformed model JSON cannot pollute the skill library or fabricate rewards."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from skillnet.catalog import SkillLibrary
from skillnet.evolver import SkillEvolver
from skillnet.judge import RUBRIC, score_plan


def skill_candidate():
    return {
        "name": "stable-numerical-report", "description": "生成可复核的数值稳定性报告",
        "domain": "数值分析", "capability": "分析误差并输出计算记录",
        "steps": ["读取 JSON 数值参数并检查范围", "使用 Python math 计算误差",
                  "输出 JSON 检查记录并比对误差阈值"],
        "verification": ["检查 JSON 结果中数值误差不超过阈值"],
    }


@pytest.mark.parametrize("field,value", [
    ("steps", "abcd"), ("steps", {"step": "执行计算"}), ("steps", ["a", {}, "b"]),
    ("tags", "数学"), ("use_when", 42), ("inputs", True), ("outputs", None),
    ("pitfalls", [{"text": "错误"}]), ("verification", [123]),
    ("relations", "a->b"), ("relations", [None]), ("relations", [{"target": []}]),
    ("name", ["fake"]), ("description", {"text": "fake"}), ("domain", 42),
])
def test_bad_skill_field_is_rejected_without_mutating_library(field, value):
    library = SkillLibrary([])
    evolver = SkillEvolver(library)
    candidate = skill_candidate()
    candidate[field] = value
    assert evolver._admit(candidate, "distill", []) is None
    assert len(library) == 0
    assert evolver.records[-1].accepted is False
    assert "结构校验失败" in evolver.records[-1].reason


@pytest.mark.parametrize("candidate", [None, [], "not an object"])
def test_non_object_skill_is_rejected_observably(candidate):
    evolver = SkillEvolver(SkillLibrary([]))
    assert evolver._admit(candidate, "distill", []) is None
    assert evolver.records[-1].accepted is False


@pytest.mark.parametrize("field,value", [
    ("name", "a" * 65), ("description", ""), ("description", "x" * 1025),
    ("steps", ["重复步骤", "重复步骤", "不同步骤"]),
])
def test_skill_contract_limits_and_distinct_steps_are_enforced(field, value):
    library = SkillLibrary([])
    evolver = SkillEvolver(library)
    candidate = skill_candidate()
    candidate[field] = value
    assert evolver._admit(candidate, "distill", []) is None
    assert not len(library)
    assert evolver.records[-1].reason


def test_valid_structured_skill_still_enters_library():
    library = SkillLibrary([])
    evolver = SkillEvolver(library)
    skill = evolver._admit(skill_candidate(), "distill", [])
    assert skill is not None
    assert library.get(skill.name) is skill
    assert skill.steps == skill_candidate()["steps"]
    assert evolver.records[-1].accepted is True


def evaluation():
    return {**{key: 8 for key in RUBRIC}, "covered": [1, 2, 1], "comment": "方法清晰"}


def test_valid_judge_result_preserves_scores_and_deduplicates_coverage(monkeypatch):
    monkeypatch.setattr("skillnet.judge.chat_json", lambda *args, **kwargs: evaluation())
    result = score_plan("分析", {"steps": []}, ["检查输入", "检查输出"])
    assert result["weighted"] == 8.0
    assert result["coverage"] == 1.0
    assert result["covered"] == [1, 2]
    assert result["degraded"] is False
    assert result["score_valid"] is True
    assert result["coverage_valid"] is True


@pytest.mark.parametrize("output", [None, [], "invalid", 42, {}])
def test_invalid_judge_response_is_degraded_and_json_serializable(monkeypatch, output):
    monkeypatch.setattr("skillnet.judge.chat_json", lambda *args, **kwargs: output)
    result = score_plan("分析", {"steps": []}, ["检查输入"])
    assert result["score_valid"] is False
    assert result["degraded"] is True
    assert result["weighted"] == 0
    assert result["degraded_reason"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value", [-1, 11, float("nan"), float("inf"), True,
                                   "8", {}, [], None, 10 ** 500])
def test_invalid_rubric_score_cannot_inflate_reward_or_break_json(monkeypatch, value):
    output = evaluation()
    output["skill_grounding"] = value
    monkeypatch.setattr("skillnet.judge.chat_json", lambda *args, **kwargs: output)
    result = score_plan("分析", {"steps": []}, ["检查输入", "检查输出"])
    assert result["scores"]["skill_grounding"] == 0
    assert result["score_valid"] is False
    assert "skill_grounding" in result["invalid_fields"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("covered", ["12", {}, None, [True, "2", 3], [1.0]])
def test_invalid_coverage_does_not_count_strings_or_booleans(monkeypatch, covered):
    output = evaluation()
    output["covered"] = covered
    monkeypatch.setattr("skillnet.judge.chat_json", lambda *args, **kwargs: output)
    result = score_plan("分析", {"steps": []}, ["检查输入", "检查输出"])
    assert result["coverage_valid"] is False
    assert result["coverage"] == 0
    assert result["score_valid"] is True
    assert result["degraded"] is True


@pytest.mark.parametrize("plan", [None, [], {"steps": "abc"}, {"steps": [], "risks": 42},
                                  {"steps": [{"key_params": "limit=3"}]}])
def test_invalid_plan_does_not_spend_judge_budget(monkeypatch, plan):
    monkeypatch.setattr("skillnet.judge.chat_json", lambda *args, **kwargs: pytest.fail("Must not call a model"))
    result = score_plan("分析", plan)
    assert result["score_valid"] is False
    assert result["degraded"] is True
