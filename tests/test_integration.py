"""Offline contracts for the service client and progressive-disclosure tools."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import httpx
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from skillnet.integration import (ClientConfig, IntegrationError, SkillNetClient,
                                 integration_manifest, skill_tools)


def client(handler, **config):
    return SkillNetClient(ClientConfig(**config), transport=httpx.MockTransport(handler))


def search_response():
    return {"query": "单细胞质控", "by_mode": {"hybrid": {
        "selected": ["scrna-qc-clustering"], "decision": "auto", "confidence": 1.0,
        "degraded": False, "detail": [
            {"name": "scrna-qc-clustering", "domain": "生物", "capability": "质控",
             "score": 0.98, "markdown": "must not leak into discovery"},
            {"name": "scientific-writing", "domain": "写作", "capability": "写作"},
        ],
    }}}


def test_discovery_uses_one_free_mode_and_returns_selected_l1_only():
    def handle(request):
        assert request.method == "POST"
        assert request.url.path == "/api/search"
        assert json.loads(request.content) == {"query": "单细胞质控", "k": 3, "modes": ["hybrid"]}
        return httpx.Response(200, json=search_response())
    with client(handle) as api:
        result = api.call_tool("search_skills", '{"query":"单细胞质控","k":3}')
    assert len(result["skills"]) == 1
    assert "markdown" not in result["skills"][0]
    assert result["confidence_kind"] == "heuristic_relevance_not_probability"


def test_tool_declarations_have_handlers_and_closed_schemas():
    tools = skill_tools()
    assert {tool["function"]["name"] for tool in tools} == {"search_skills", "load_skill"}
    for tool in tools:
        schema = tool["function"]["parameters"]
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        assert tool["function"]["strict"] is True


@pytest.mark.parametrize("name,arguments", [
    ("execute_run", {}), ("search_skills", {"query": "x", "mode": "fabric"}),
    ("load_skill", {"name": "../secret"}), ("load_skill", {"name": "A"}),
    ("search_skills", {"query": "  "}), ("search_skills", {"query": "x", "k": 0}),
    ("search_skills", {"query": "x", "k": "5"}), ("load_skill", "[]"),
    ("load_skill", "{invalid"),
])
def test_invalid_tools_never_reach_service(name, arguments):
    def forbidden(request):
        pytest.fail("Invalid inputs must be rejected before networking")
    with client(forbidden) as api, pytest.raises((ValueError, ValidationError)):
        api.call_tool(name, arguments)


def test_service_token_and_proxy_prefix_are_preserved():
    def handle(request):
        assert request.url.path == "/skillnet/api/skill/data-cleaning"
        assert request.headers["X-SkillNet-Token"] == "service-secret"
        return httpx.Response(200, json={"skill": {"name": "data-cleaning"}, "markdown": "# 清洗"})
    with client(handle, base_url="https://internal.example/skillnet", token="service-secret") as api:
        assert api.call_tool("load_skill", {"name": "data-cleaning"})["markdown"] == "# 清洗"
        assert "service-secret" not in repr(api.config)


@pytest.mark.parametrize("base_url", [
    "file:///secret", "https://user:password@example.org", "https://example.org?token=secret",
    "https://example.org/#fragment", "http://external.example", "https://example.org:bad",
])
def test_invalid_or_insecure_urls_are_rejected(base_url):
    with pytest.raises(ValueError):
        ClientConfig(base_url=base_url)


def test_explicit_trusted_http_network_is_allowed():
    assert ClientConfig(base_url="http://skillnet.internal:8848", allow_insecure_http=True)


@pytest.mark.parametrize("status,code", [(401, "unauthorized"), (404, "not_found"),
                                       (422, "invalid_request"), (429, "rate_limited"), (503, "unavailable")])
def test_errors_are_categorized_without_upstream_secret_or_prompt(status, code):
    def handle(request):
        return httpx.Response(status, json={"detail": "service-secret private task text"},
                              headers={"X-Request-ID": "trace-123"})
    with client(handle, token="service-secret") as api, pytest.raises(IntegrationError) as error:
        api.health()
    assert error.value.code == code
    assert error.value.status_code == status
    assert error.value.request_id == "trace-123"
    assert "service-secret" not in str(error.value)
    assert "private task" not in str(error.value)


def test_redirect_is_not_followed_with_credentials():
    calls = []
    def handle(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://other.example/"})
    with client(handle, token="secret") as api, pytest.raises(IntegrationError):
        api.health()
    assert len(calls) == 1


@pytest.mark.parametrize("body", [b"not JSON", b"[]", b'{"ok":"true"}'])
def test_invalid_health_contract_is_rejected(body):
    with client(lambda request: httpx.Response(200, content=body)) as api, pytest.raises(IntegrationError) as error:
        api.health()
    assert error.value.code == "invalid_response"


def test_mutation_timeout_is_not_automatically_retried():
    calls = []
    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret-token/private prompt", request=request)
    with client(handle) as api, pytest.raises(IntegrationError) as error:
        api.create_run("检查真实数据", max_cost_yuan=0.2, max_steps=2)
    assert len(calls) == 1
    assert error.value.code == "timeout"
    assert "outcome may be unknown" in str(error.value)
    assert "secret-token" not in str(error.value)


def test_explicit_run_budgets_and_state_queries():
    def handle(request):
        if request.method == "POST" and request.url.path == "/api/runs":
            body = json.loads(request.content)
            assert body["max_cost_yuan"] == 0.3 and body["max_seconds"] == 120
            assert body["max_steps"] == 2
            return httpx.Response(200, json={"run_id": "abc-20261007-001", "status": "CREATED"})
        assert request.url.path.startswith("/api/runs/abc-20261007-001")
        return httpx.Response(200, json={"run_id": "abc-20261007-001", "status": "COMPLETED"})
    with client(handle) as api:
        run = api.create_run("验证模型", max_cost_yuan=0.3, max_seconds=120, max_steps=2)
        assert api.get_run(run["run_id"])["status"] == "COMPLETED"
        assert api.cancel_run(run["run_id"])["status"] == "COMPLETED"


def test_sse_parses_multiline_events_and_reconnect_cursor():
    def handle(request):
        assert request.headers["Last-Event-ID"] == "12"
        return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, text=(
            ': heartbeat\n\nid: 13\ndata: {"kind":\ndata: "step.completed"}\n\n'
            'event: end\ndata: {}\n\n'
        ))
    with client(handle) as api:
        events = list(api.iter_run_events("abc-20261007-001", last_event_id="12"))
    assert events == [
        {"event": "message", "id": "13", "data": {"kind": "step.completed"}},
        {"event": "end", "id": "", "data": {}},
    ]


def test_sse_invalid_payload_and_content_type_are_rejected():
    for headers, body in [({"Content-Type": "application/json"}, "{}"),
                          ({"Content-Type": "text/event-stream"}, "data: []\n\n")]:
        with client(lambda request: httpx.Response(200, headers=headers, text=body)) as api:
            with pytest.raises(IntegrationError) as error:
                list(api.iter_run_events("abc-20261007-001"))
            assert error.value.code == "invalid_response"


def test_stream_and_download_timeouts_do_not_expose_token():
    def handle(request):
        raise httpx.ReadTimeout("service-secret from Authorization", request=request)
    with client(handle, token="service-secret") as api:
        for operation in [lambda: list(api.iter_run_events("abc")),
                          lambda: api.download_artifact("abc", "result.txt")]:
            with pytest.raises(IntegrationError) as error:
                operation()
            assert error.value.code == "timeout"
            assert "service-secret" not in str(error.value)
            assert "Authorization" not in str(error.value)


def test_abandoning_event_iterator_closes_http_stream():
    class Stream(httpx.SyncByteStream):
        closed = False
        def __iter__(self):
            yield b'data: {"type":"step.started"}\n\n'
        def close(self):
            self.closed = True
    stream = Stream()
    with client(lambda request: httpx.Response(200, headers={"Content-Type": "text/event-stream"}, stream=stream)) as api:
        events = api.iter_run_events("abc")
        assert next(events)["data"]["type"] == "step.started"
        events.close()
    assert stream.closed is True


def test_malformed_search_summaries_cannot_crash_tool_dispatch():
    response = search_response()
    response["by_mode"]["hybrid"]["detail"].extend([{"name": []}, {"name": {}}, 42])
    with client(lambda request: httpx.Response(200, json=response)) as api:
        result = api.call_tool("search_skills", {"query": "单细胞", "k": 3})
    assert len(result["skills"]) == 1


def test_artifact_size_and_digest_are_verified():
    content = "真实结果".encode()
    with client(lambda request: httpx.Response(200, content=content)) as api:
        digest = hashlib.sha256(content).hexdigest()
        assert api.download_artifact("abc", "结果.txt", expected_sha256=digest) == content
        with pytest.raises(IntegrationError) as error:
            api.download_artifact("abc", "结果.txt", expected_sha256="0" * 64)
        assert error.value.code == "digest_mismatch"
        with pytest.raises(IntegrationError) as error:
            api.download_artifact("abc", "结果.txt", max_bytes=2)
        assert error.value.code == "response_too_large"


@pytest.mark.parametrize("name", ["../secret", "..", "path/file", "path\\file", "evil\x00file"])
def test_artifact_paths_cannot_escape(name):
    with client(lambda request: pytest.fail("No request expected")) as api, pytest.raises(ValueError):
        api.download_artifact("abc", name)


def test_manifest_does_not_claim_a_production_s1_connection():
    manifest = integration_manifest()
    assert manifest["production_connection_verified"] is False
    assert manifest["status"] == "contract_ready"
    assert manifest["operations"]["search"]["default_mode"] == "hybrid"
