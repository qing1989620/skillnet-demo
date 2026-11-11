from __future__ import annotations

import copy
import csv
import io

import pytest

from research.skill_network.contracts import context_group
from research.skill_network.kernels import execute
from research.skill_network.oracle import reference, verify
from research.skill_network.planner import choose, eligible, enumerate_paths, evidence, metadata_path
from research.skill_network.registry import full_registry, public_nodes


def fixture():
    table = [
        ["sample_id", "subject_id", "split", "label", "score"],
        ["a", "shared", "train", "1", "0.5"],
        ["b", "shared", "test", "0", ""],
        ["c", "single", "train", "1", "0.5"],
        ["c", "single", "train", "0", "0.1"],
        ["d", "other", "test", "0", "0.2"],
    ]
    stream = io.StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(table)
    return stream.getvalue(), {"mask": 7, "threshold": "0.5"}


def request():
    return {
        "task_id": "unit",
        "intent": {"mask": 7, "threshold": "0.5"},
        "profile": {"quoted": False, "boundary": True},
        "query": "parse deduplicate exclude drop metrics",
    }


def test_independent_oracle_detects_wrong_order_and_threshold():
    raw, intent = fixture()
    expected = reference(raw, intent)
    for plan, correct in [
        (["p0", "d0", "x0", "m0", "t0"], True),
        (["p0", "b0", "t0"], True),
        (["p0", "b1", "t0"], False),
        (["p0", "b0", "t1"], False),
    ]:
        output = execute({"execution_id": "unit", "raw": raw, "intent": intent, "plan": plan})
        assert verify(output, expected)["passed"] is correct


def test_zero_exit_or_success_label_does_not_substitute_for_exact_artifact():
    raw, intent = fixture()
    target = reference(raw, intent)
    assert not verify({"error": None, "success": True}, target)["passed"]
    valid = execute({"execution_id": "unit", "raw": raw, "intent": intent, "plan": ["p0", "b0", "t0"]})
    assert verify(valid, target)["passed"]
    valid["error"] = "failed"
    assert not verify(valid, target)["passed"]


def test_context_evidence_is_dev_version_bound_and_unseen_is_not_certified():
    node = {"id": "node", "capability": "parse", "source_sha256": "v2"}
    r = request()
    records = [{"node_id": "node", "source_sha256": "v1", "group": "quoted=0", "passed": True}]
    assert evidence(node, r, records, True) == (0, 0)
    assert evidence(node, r, records, True, True) == (1, 1)
    records.append({"node_id": "alias", "source_sha256": "v2", "group": "quoted=1", "passed": False})
    assert evidence(node, r, records, True) == (0, 0)
    assert evidence(node, r, records, False) == (0, 1)


def test_public_selector_projection_contains_no_kernel_or_gold_labels():
    nodes = public_nodes(full_registry())
    assert len(nodes) == 18 and all(
        set(n) == {"id", "capability", "text", "source_sha256", "context_bytes"} for n in nodes
    )
    bad = copy.deepcopy(nodes)
    bad[0]["expected_artifact"] = {}
    with pytest.raises(AssertionError):
        choose(bad, request(), [], 100000, "conditional_evidence_path")


def test_native_shortest_path_matches_exhaustive_metadata_cost():
    nodes = eligible(public_nodes(full_registry()), request())
    exact = metadata_path(nodes, request())
    paths = enumerate_paths(nodes, request(), 100000)
    assert exact["status"] == "plan_found"
    assert exact["cost"] == min(cost for _, cost in paths)
    assert all(len(path) <= 5 for path, _ in paths)


def test_budget_is_enforced_before_execution_and_no_path_is_not_success():
    nodes = public_nodes(full_registry())
    r = request()
    for policy in ["metadata_shortest_path", "conditional_evidence_path", "mmr_top5"]:
        answer = choose(nodes, r, [], 1, policy)
        assert answer["plan"] == []
    for node in nodes:
        node["capability"] = "parse"
    assert choose(nodes, r, [], 10000, "conditional_evidence_path")["plan"] == []
    assert choose(nodes, r, [], 10000, "fixed_workflow", fixed_ids={"parse": nodes[0]["id"]})["plan"] == []


def test_test_answers_cannot_change_a_metadata_request_decision():
    nodes = public_nodes(full_registry())
    r = request()
    a = choose(nodes, r, [], 100000, "conditional_evidence_path")
    with pytest.raises(AssertionError):
        choose(nodes, {**r, "expected_artifact": {"rows": []}}, [], 100000, "conditional_evidence_path")
    assert choose(nodes, r, [], 100000, "conditional_evidence_path") == a


def test_worker_rejects_arbitrary_code_key_without_execution():
    raw, intent = fixture()
    result = execute({"execution_id": "unit", "raw": raw, "intent": intent, "plan": ['__import__("os")']})
    assert result["error"] == "unsupported_plan_or_call_limit" and result["calls"] == 0


def test_exact_rational_reference_catches_float_precision_shift():
    raw = "sample_id,subject_id,split,label,score\na,s,train,0,0.499999999999999999999999\n"
    intent = {"mask": 0, "threshold": "0.5"}
    expected = reference(raw, intent)
    assert verify(
        execute({"execution_id": "a", "raw": raw, "intent": intent, "plan": ["p0", "t0"]}), expected
    )["passed"]
    assert not verify(
        execute({"execution_id": "b", "raw": raw, "intent": intent, "plan": ["p0", "t2"]}), expected
    )["passed"]


def test_condition_groups_do_not_contain_test_metrics():
    r = request()
    assert context_group({"capability": "parse"}, r, True) == "quoted=0"
    assert context_group({"capability": "metrics"}, r, True) == "boundary=1"
