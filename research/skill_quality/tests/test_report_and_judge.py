from __future__ import annotations

import json

import httpx
import pytest

from research.skill_quality.audit_static import audit
from research.skill_quality.datasets import deduplicate, prepare_splits
from research.skill_quality.judge import JudgeResponse, judge, messages
from research.skill_quality.label_export import blind_document
from research.skill_quality.manifest import freeze_files, read_jsonl, verify_files, write_once
from research.skill_quality.openrouter_client import ClientFailure, CostLedger, OpenRouterClient
from research.skill_quality.report import inventory_metrics, render_report
from research.skill_quality.schemas import Evidence, validate_evidence

from .conftest import make_rating


def test_assessor_cannot_invent_verified_or_static_evidence(snapshot):
    for kind in ("static_check", "execution_verified", "paired_contribution", "human_label"):
        evidence = Evidence(
            evidence_id="e1",
            skill_uid=snapshot.skill_uid,
            kind=kind,
            source_sha256=snapshot.document_sha256,
            run_id="model-invented-run",
            validity="observed",
            reason="fabricated by an untrusted assessor",
        )
        with pytest.raises(ValueError, match="manufacture"):
            validate_evidence(make_rating(snapshot, observed=1), (evidence,), snapshot)


def test_judge_mock_returns_unknown_without_fabricating_labels(snapshot):
    payload = JudgeResponse(rating=make_rating(snapshot), evidence=()).model_dump(mode="json")

    def handler(request):
        body = json.loads(request.content)
        assert "Trusted rubric" in body["messages"][0]["content"]
        assert "static_executability" in body["messages"][0]["content"]
        assert body["messages"][1]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "model": "fixture/model",
                "id": "mock",
                "usage": {"cost": 0},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(payload)}}],
            },
        )

    client = OpenRouterClient(
        ledger=CostLedger("0.1"),
        model="fixture/model",
        provider="fixture-provider",
        transport=httpx.MockTransport(handler),
    )
    result = judge(snapshot, client, run_id="fixture", upper_cost_usd="0.01")
    assert all(dim.score is None for dim in result.rating.dimensions)
    client.close()


def test_external_document_cannot_replace_system_rubric(snapshot):
    prompt = messages(snapshot)
    assert prompt[0]["role"] == "system" and prompt[1]["role"] == "user"
    assert json.loads(prompt[1]["content"])["boundary"] == "UNTRUSTED_DOCUMENT_DATA"
    assert "historical_scores" not in json.loads(prompt[1]["content"])


def test_blinding_preserves_source_line_numbers():
    document = "# Example\n## 质量评估\n| safety | Good |\n## Steps\nCheck row count.\n"
    blinded = blind_document(document)
    assert blinded.splitlines()[4] == "Check row count."
    assert len(blinded.splitlines()) == len(document.splitlines())


def test_reports_recompute_counts_without_assuming_missing_quality_is_bad(snapshot, tmp_path):
    dedup = deduplicate([snapshot])
    split = prepare_splits([snapshot], dedup, target=1)
    recomputed = {
        dim: {"level": "Good"}
        for dim in ("safety", "completeness", "executability", "maintainability", "cost_awareness")
    }
    raw = [
        {
            "skill_uid": snapshot.skill_uid,
            "stored_quality": {},
            "stored_score": 0.6,
            "recomputed_quality": recomputed,
            "recomputed_score": 1.0,
        }
    ]
    write_once(tmp_path / "raw.jsonl", raw, jsonl=True)
    metrics = inventory_metrics(
        [snapshot], read_jsonl(tmp_path / "raw.jsonl"), [audit(snapshot)], split, dedup
    )
    assert metrics["stored_quality_absent_skills"] == 1
    assert metrics["stored_vs_recomputed_grade_disagreements"] == 0
    assert metrics["P1"]["mae"] is None and metrics["P2"]["delta_pp"] is None
    assert "not_run" in render_report(metrics)
    manifest = freeze_files(tmp_path, [tmp_path / "raw.jsonl"])
    verify_files(tmp_path, manifest)
    (tmp_path / "raw.jsonl").write_text("tampered\n")
    with pytest.raises(ValueError, match="SHA mismatch"):
        verify_files(tmp_path, manifest)


def test_durable_ledger_allows_only_one_writer(tmp_path):
    path = tmp_path / "ledger.jsonl"
    first = CostLedger("1", path)
    with pytest.raises(ClientFailure, match="already_in_use"):
        CostLedger("1", path)
    first.close()
    second = CostLedger("1", path)
    second.close()
