from __future__ import annotations

import json
from decimal import Decimal
from typing import Literal

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from research.skill_quality.manifest import canonical, redact
from research.skill_quality.openrouter_client import ClientFailure, CostLedger, OpenRouterClient, amount


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["unknown", "observed"]


def response(*, cost="0.01", status=200, finish="stop", content='{"verdict":"unknown"}', usage=True):
    value = {
        "id": "generation-fixture",
        "model": "fixture/model",
        "provider": "fixture-provider",
        "choices": [{"finish_reason": finish, "message": {"content": content}}],
    }
    if usage:
        value["usage"] = {"cost": cost, "prompt_tokens": 50, "completion_tokens": 10}
    return httpx.Response(status, json=value)


def client(handler, *, budget="0.10", path=None):
    ledger = CostLedger(budget, path)
    api = OpenRouterClient(
        ledger=ledger,
        model="fixture/model",
        provider="fixture-provider",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    return api, ledger


def complete(api, run_id="r", upper="0.02"):
    return api.complete(
        [{"role": "user", "content": "synthetic fixture"}], Verdict, run_id=run_id, upper_cost_usd=upper
    )


def test_zero_budget_and_unapproved_live_client_never_open_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No httpx client may be constructed for unapproved live calls")

    monkeypatch.setattr(httpx, "Client", forbidden)
    with pytest.raises(ClientFailure, match="not_approved"):
        OpenRouterClient(ledger=CostLedger("0"), model="x", provider="x")


def test_payload_requires_schema_and_fixed_provider():
    def handler(request):
        body = json.loads(request.content)
        assert body["provider"] == {
            "only": ["fixture-provider"],
            "allow_fallbacks": False,
            "require_parameters": True,
        }
        assert body["response_format"]["json_schema"]["strict"] is True
        assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
        return response()

    api, ledger = client(handler)
    assert complete(api).verdict == "unknown"
    assert ledger.spent == Decimal("0.01")
    api.close()


@pytest.mark.parametrize("status", [401, 403, 404])
def test_permanent_errors_not_retried(status):
    calls = []
    api, ledger = client(lambda request: calls.append(request) or response(cost="0", status=status))
    with pytest.raises(ClientFailure, match="http_" + str(status)):
        complete(api)
    assert len(calls) == 1 and len(ledger.events) == 2
    api.close()


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_each_failed_attempt_is_billed_and_preserved(status):
    replies = iter([response(status=status, cost="0.01"), response(cost="0.02")])
    api, ledger = client(lambda _: next(replies))
    complete(api)
    settled = [e for e in ledger.events if e["event"] == "settled"]
    assert ledger.spent == Decimal("0.03") and len(settled) == 2
    assert settled[0]["failure_kind"] == "http_" + str(status)
    assert settled[1]["schema_valid"]
    api.close()


def test_unknown_cost_freezes_further_calls(tmp_path):
    calls = []
    path = tmp_path / "ledger.jsonl"
    api, ledger = client(lambda request: calls.append(request) or response(usage=False), path=path)
    with pytest.raises(ClientFailure, match="unknown_billing"):
        complete(api)
    with pytest.raises(ClientFailure, match="unknown_or_pending"):
        complete(api, "other")
    assert len(calls) == 1 and ledger.events[-1]["billed_cost_usd"] is None
    api.close()
    recovered = CostLedger("0.10", path)
    with pytest.raises(ClientFailure, match="unknown_or_pending"):
        recovered.reserve("new:0", "0.02", {})
    recovered.close()


def test_pending_reservation_survives_process_restart(tmp_path):
    path = tmp_path / "ledger.jsonl"
    CostLedger("1", path).reserve("r:0", "0.1", {})
    with pytest.raises(ClientFailure, match="pending"):
        CostLedger("1", path).reserve("r:1", "0.1", {})


def test_timeout_is_not_a_free_request_and_never_echoes_secret(tmp_path):
    fake_key = "sk-" + "X" * 32

    def handler(request):
        raise httpx.ReadTimeout(fake_key, request=request)

    api, ledger = client(handler, path=tmp_path / "ledger.jsonl")
    with pytest.raises(ClientFailure, match="unknown_billing") as exc:
        complete(api)
    assert fake_key not in str(exc.value) and fake_key not in canonical(ledger.events).decode()
    assert ledger.events[-1]["failure_kind"] == "timeout"
    api.close()


@pytest.mark.parametrize(
    "finish,content",
    [
        ("length", '{"verdict":"unknown"}'),
        ("content_filter", "{}"),
        ("stop", '{"verdict":'),
        ("stop", '{"verdict":"unknown","invented":1}'),
    ],
)
def test_incomplete_or_invalid_json_is_not_repaired(finish, content):
    api, ledger = client(lambda _: response(finish=finish, content=content))
    with pytest.raises(ClientFailure):
        complete(api)
    assert not ledger.events[-1]["schema_valid"] and ledger.spent == Decimal("0.01")
    api.close()


def test_budget_check_precedes_retry_and_retains_first_bill():
    calls = []
    api, ledger = client(lambda request: calls.append(request) or response(status=500), budget="0.02")
    with pytest.raises(ClientFailure, match="budget_insufficient"):
        complete(api)
    assert len(calls) == 1 and ledger.spent == Decimal("0.01")
    api.close()


@pytest.mark.parametrize("value", [-1, float("inf"), float("nan"), True, "invalid"])
def test_invalid_usd_amount_is_rejected(value):
    with pytest.raises(ValueError):
        amount(value)


def test_decimal_precision_and_double_settlement(tmp_path):
    ledger = CostLedger("0.3", tmp_path / "ledger.jsonl")
    ledger.reserve("a", "0.1", {})
    ledger.settle("a", "0.1", {})
    ledger.reserve("b", "0.2", {})
    ledger.settle("b", "0.2", {})
    assert ledger.spent == Decimal("0.3")
    with pytest.raises(ClientFailure, match="duplicate"):
        ledger.settle("b", "0.2", {})
    assert "Bearer fake" not in str(redact({"Authorization": "Bearer fake", "x": "Bearer fake"}))


def test_closed_ledger_cannot_write_after_releasing_its_lock(tmp_path):
    ledger = CostLedger("1", tmp_path / "ledger.jsonl")
    ledger.close()
    with pytest.raises(ClientFailure, match="closed"):
        ledger.reserve("new", "0.1", {})


@pytest.mark.parametrize("key", ["event", "billed_cost_usd"])
def test_metadata_cannot_overwrite_accounting_fields(key):
    ledger = CostLedger("1")
    with pytest.raises(ClientFailure, match="reserved_metadata"):
        ledger.reserve("new", "0.1", {key: "forged"})


def test_actual_cost_above_reservation_is_preserved_and_stops():
    api, ledger = client(lambda _: response(cost="0.05"))
    with pytest.raises(ClientFailure, match="actual_cost_exceeds"):
        complete(api, upper="0.02")
    assert ledger.spent == Decimal("0.05")
    api.close()
