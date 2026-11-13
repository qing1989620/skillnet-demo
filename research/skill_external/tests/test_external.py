import json
from decimal import Decimal

import httpx
import pytest

from research.skill_external.community_runtime import reference
from research.skill_external.experiment import Judgment, Ledger, one, payload, upper_cost
from research.skill_external.materials import clip, obj_facts
from research.skill_quality.manifest import digest


def packet():
    return {
        "case_id": "opaque",
        "instruction": "Check all outputs",
        "trajectory": "step:1\nObserved output",
        "available_skills": "skill:a",
        "official_artifact_summary": "partial snapshot",
        "artifact_facts": "obj facts",
        "allowed_refs": ["instruction", "step:1", "obj-aggregate"],
    }


def test_no_gold_can_enter_payload():
    p = packet()
    original = payload(p, "artifact_packet")
    p.update(trajectory_label="pass", trajectory_reward=1, expected={"answer": 42})
    assert payload(p, "artifact_packet") == original
    assert "obj facts" not in json.dumps(payload(p, "standard"))


def test_explicit_bounded_head_tail():
    value = "A" * 300 + "B" * 300
    result = clip(value, 120)
    assert len(result) == 120 and result.startswith("A") and result.endswith("B")
    assert "TRUNCATION" in result


def test_obj_reports_indices_without_execution(tmp_path):
    p = tmp_path / "a.obj"
    p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\nf -3 -2 -1\n")
    fact = obj_facts(p)
    assert fact["vertices"] == 3 and fact["faces"] == 2 and fact["bad_vertex_references"] == 1


def test_budget_unknown_blocks_further_calls(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", cap="0.01", max_attempts=2)
    assert ledger.reserve("first", {})
    ledger.settle("first", None)
    assert not ledger.reserve("second", {})
    assert ledger.attempts == 1 and ledger.reserved


def test_budget_known_usage_settles(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", cap="1", max_attempts=1)
    assert ledger.reserve("one", {})
    ledger.settle("one", upper_cost(100, 10))
    assert ledger.actual == Decimal("0.000042") and not ledger.reserved
    assert not ledger.reserve("two", {})


def test_probabilities_and_schema_do_not_self_certify():
    with pytest.raises(ValueError):
        Judgment(p_success=0.9, decision="FAIL", reason="wrong", evidence_refs=[])
    with pytest.raises(ValueError):
        upper_cost(None, 10)


def test_exact_iqr_threshold_regression_has_hand_checkable_answer():
    case = {"rows": [["id", str(x), "group", "note"] for x in [0, 1, 2, 3, 4, 5, 6, 14]]}
    # q1=1.75, q3=5.25; upper fence is 10.5 or 15.75.
    assert reference(case, 1.5)["outlier_count"] == 1
    assert reference(case, 3.0)["outlier_count"] == 0


def test_null_policy_is_compatibility_not_universal_fault():
    case = {"rows": [["id", "NA", "  ", ""], ["id2", "1", "x", "note"]]}
    result = reference(case, 1.5)
    assert result["broad_nulls"] == {"id": 0, "value": 1, "group": 1, "note": 1}
    assert result["strict_nulls"] == {"id": 0, "value": 0, "group": 0, "note": 1}


def test_mock_call_has_usage_and_registered_refs(tmp_path):
    p = packet()
    request = payload(p, "standard")
    row = {
        "trial_id": "case-standard",
        "case_id": "opaque",
        "arm": "standard",
        "payload_sha256": digest(request),
    }
    response = {
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "p_success": 0.1,
                            "decision": "FAIL",
                            "reason": "Observed error",
                            "evidence_refs": ["step:1"],
                        }
                    )
                },
            }
        ],
    }
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))) as client:
        result = one(row, p, client, Ledger(tmp_path / "ledger.json"), tmp_path)
    assert result["schema_valid"] and result["locator_checks"] == [{"ref": "step:1", "supplied": True}]
