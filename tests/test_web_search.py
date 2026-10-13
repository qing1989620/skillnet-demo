from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from skillnet import web_search


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv("SKILLNET_WEB_ENABLED", "true")


@pytest.fixture
def transport(monkeypatch):
    original_client = httpx.Client
    calls, options = [], []

    def install(handler):
        def wrapped(request):
            calls.append(request)
            return handler(request)

        def client(**kwargs):
            options.append(kwargs.copy())
            assert kwargs["trust_env"] is False
            assert kwargs["follow_redirects"] is False
            assert 0 < kwargs["timeout"] <= 60
            return original_client(transport=httpx.MockTransport(wrapped), **kwargs)

        monkeypatch.setattr(web_search.httpx, "Client", client)
        return calls, options

    return install


def result(url="https://example.org/research", **extra):
    return {"title": "Research result", "url": url, "content": "Public source text", **extra}


def test_keyless_search_uses_official_fixed_endpoint_and_unmodified_query(transport):
    calls, _ = transport(lambda request: httpx.Response(200, json={"results": [result()]}))
    report = web_search.search("科研 same name", limit=2)
    assert report["state"] == "success" and report["keyless"] is True
    assert report["results"] == [{"title": "Research result", "url": "https://example.org/research",
        "snippet": "Public source text", "provider": "tavily"}]
    assert len(calls) == 1
    request = calls[0]
    assert str(request.url) == "https://api.tavily.com/search" and request.method == "POST"
    assert request.headers["X-Tavily-Access-Mode"] == "keyless"
    assert request.headers["X-Client-Source"] == "tavily-python-keyless"
    assert "authorization" not in request.headers
    assert json.loads(request.content) == {"query": "科研 same name", "max_results": 2,
        "include_answer": False, "include_raw_content": False}
    assert report["attempts"] == [{"provider": "tavily", "status_code": 200,
        "state": "success", "reason": "live_provider_response"}]


def test_configured_key_replaces_keyless_mode_and_never_enters_report(transport, monkeypatch):
    secret = "tvly-private-test-value"
    monkeypatch.setenv("TAVILY_API_KEY", secret)
    calls, _ = transport(lambda request: httpx.Response(401, json={"detail": secret}))
    report = web_search.search("public question")
    assert calls[0].headers["Authorization"] == "Bearer " + secret
    assert "X-Tavily-Access-Mode" not in calls[0].headers
    assert report["state"] == "unavailable" and report["keyless"] is False
    assert secret not in json.dumps(report)
    assert report["attempts"][0]["state"] == "authentication_required"


@pytest.mark.parametrize("status,body,headers,expected,retry", [
    (429, {"error": {"code": "KEYLESS_LIMIT", "message": "secret text", "retry_after_seconds": 7}}, {}, "rate_limited", 7),
    (429, {}, {"Retry-After": "12"}, "rate_limited", 12),
    (200, {"error": {"code": "keyless_quota_exceeded", "message": "secret text", "retry_after_seconds": 3}}, {}, "rate_limited", 3),
    (403, {"detail": "secret text"}, {}, "access_denied", None),
    (503, {"detail": "secret text"}, {}, "unavailable", None),
    (200, {"error": {"code": "error", "message": "secret text"}}, {}, "unavailable", None),
])
def test_provider_failures_are_explicit_redacted_and_never_retried(transport, status, body, headers, expected, retry):
    calls, _ = transport(lambda request: httpx.Response(status, json=body, headers=headers))
    report = web_search.search("public question")
    assert report["state"] == "unavailable" and report["results"] == []
    assert len(calls) == 1
    attempt = report["attempts"][0]
    assert attempt["state"] == expected and attempt["status_code"] == status
    assert attempt.get("retry_after_seconds") == retry
    assert "secret text" not in json.dumps(report)


def test_real_zero_results_is_distinct_from_missing_or_malformed_response(transport):
    transport(lambda request: httpx.Response(200, json={"results": []}))
    report = web_search.search("unmatched")
    assert report["state"] == "empty"
    assert report["attempts"][0]["reason"] == "live_provider_returned_zero_results"


@pytest.mark.parametrize("body", [{}, {"results": None}, {"results": {}}, ["unexpected"]])
def test_missing_results_are_not_reported_as_a_successful_empty_search(transport, body):
    transport(lambda request: httpx.Response(200, json=body))
    report = web_search.search("public question")
    assert report["state"] == "unavailable"
    assert report["attempts"][0]["state"] == "invalid_response"


def test_html_challenge_is_not_a_search_result(transport):
    transport(lambda request: httpx.Response(202, text="<html>captcha required</html>"))
    report = web_search.search("public question")
    assert report["state"] == "unavailable" and report["results"] == []
    assert report["attempts"][0]["reason"] == "expected_json_object"


def test_redirect_is_not_followed_to_another_provider_host(transport):
    calls, _ = transport(lambda request: httpx.Response(302, headers={"Location": "http://127.0.0.1/secret"}))
    report = web_search.search("public question")
    assert len(calls) == 1 and report["state"] == "unavailable"
    assert report["attempts"][0]["reason"] == "provider_redirect_not_followed"


def test_request_exception_never_exposes_request_or_proxy_details(transport):
    def handler(request):
        raise httpx.ReadTimeout("secret https://api.tavily.com?api_key=private", request=request)
    calls, _ = transport(handler)
    report = web_search.search("public question")
    assert len(calls) == 1 and report["attempts"][0]["state"] == "timeout"
    assert "api_key" not in json.dumps(report) and "secret" not in json.dumps(report)


def test_oversized_response_is_bounded_before_json_or_result_use(transport):
    transport(lambda request: httpx.Response(200, content=b"x" * (web_search.MAX_RESPONSE_BYTES + 1)))
    report = web_search.search("public question")
    assert report["state"] == "unavailable"
    assert report["attempts"][0]["reason"] == "response_size_limit"


def test_deeply_nested_json_is_rejected_without_unhandled_parser_error(transport):
    transport(lambda request: httpx.Response(200, content=b"[" * 2000 + b"]" * 2000))
    report = web_search.search("public question")
    assert report["state"] == "unavailable"
    assert report["attempts"][0]["reason"] == "expected_json_object"


def test_extreme_retry_metadata_is_ignored_without_overflow(transport):
    transport(lambda request: httpx.Response(429, json={"error": {"retry_after_seconds": 10 ** 400}}))
    report = web_search.search("public question")
    assert report["attempts"][0]["state"] == "rate_limited"
    assert "retry_after_seconds" not in report["attempts"][0]


def test_search_filters_obvious_unsafe_urls_and_bounds_snippets(transport):
    rows = [result("file:///tmp/private"), result("http://127.0.0.1/a"),
        result("https://user:password@example.org/a"), result("http://localhost/a"),
        result("https://inside.internal/a"), result("https://example.org:9999/a"),
        result("https://example.org/source#fragment", title="T" * 1000, content="S" * 9000)]
    transport(lambda request: httpx.Response(200, json={"results": rows}))
    report = web_search.search("public question")
    assert len(report["results"]) == 1
    row = report["results"][0]
    assert row["url"] == "https://example.org/source"
    assert len(row["title"]) == 500 and len(row["snippet"]) == 3000


def test_all_rejected_results_are_explicitly_invalid_instead_of_zero_matches(transport):
    transport(lambda request: httpx.Response(200, json={"results": [result("http://127.0.0.1")]}))
    report = web_search.search("public question")
    assert report["state"] == "unavailable"
    assert report["attempts"][0]["reason"] == "no_usable_public_result"


def academic_handler(request):
    if request.url.host == "api.crossref.org":
        return httpx.Response(200, json={"message": {"items": [{
            "DOI": "10.1234/one", "URL": "https://doi.org/10.1234/one", "title": ["Crossref paper"],
            "abstract": "<jats:p>Publisher abstract</jats:p>",
            "author": [{"given": "Xiao", "family": "Wang", "affiliation": [{"name": "Public University"}]}],
        }, {"DOI": "10.1234/two", "title": ["Second Crossref paper"]}]}})
    if request.url.host == "www.ebi.ac.uk":
        assert request.url.params["resultType"] == "core"
        return httpx.Response(200, json={"hitCount": 1, "resultList": {"result": [{
            "id": "123", "source": "MED", "title": "Europe PMC paper", "doi": "10.1234/pmc",
            "authorList": {"author": [{"fullName": "Wang X", "authorAffiliationDetailsList": {
                "authorAffiliation": [{"affiliation": "Research Institute"}]}}]},
        }]}})
    return httpx.Response(200, json={"results": [result()]})


def test_academic_search_queries_real_catalogues_and_preserves_source_diversity(transport):
    calls, _ = transport(academic_handler)
    report = web_search.search("Wang scientist", limit=3, kind="academic")
    assert report["state"] == "success" and len(calls) == 3
    assert [row["provider"] for row in report["results"]] == ["crossref", "europepmc", "tavily"]
    assert report["results"][0]["authors"] == ["Xiao Wang"]
    assert report["results"][0]["affiliations"] == ["Public University"]
    assert report["results"][0]["snippet"] == "Publisher abstract"
    assert report["results"][1]["authors"] == ["Wang X"]
    assert report["results"][1]["affiliations"] == ["Research Institute"]
    assert str(calls[0].url).startswith("https://api.crossref.org/works?")
    assert calls[0].url.params["query"] == "Wang scientist"


def test_academic_provider_failure_keeps_real_other_results_as_partial(transport):
    def handler(request):
        if request.url.host == "api.crossref.org":
            return httpx.Response(429, json={})
        return academic_handler(request)
    calls, _ = transport(handler)
    report = web_search.search("public science query", kind="academic")
    assert report["state"] == "partial" and report["results"]
    assert len(calls) == 3 and report["attempts"][0]["state"] == "rate_limited"
    assert all(row["provider"] != "crossref" for row in report["results"])


def test_academic_total_deadline_does_not_multiply_timeout_by_provider_count(transport, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(web_search.time, "monotonic", lambda: clock[0])
    def handler(request):
        clock[0] += 16
        return academic_handler(request)
    calls, _ = transport(handler)
    report = web_search.search("public science query", kind="academic", timeout=15)
    assert len(calls) == 1
    assert [a["state"] for a in report["attempts"]] == ["timeout", "budget_exhausted", "budget_exhausted"]
    assert report["state"] == "unavailable"


def test_malformed_metadata_nested_types_do_not_crash_or_invent_authors(transport):
    def handler(request):
        if request.url.host == "api.crossref.org":
            return httpx.Response(200, json={"message": {"items": [{"DOI": "10.1234/paper", "author": {"bad": 1}}]}})
        if request.url.host == "www.ebi.ac.uk":
            return httpx.Response(200, json={"resultList": {"result": [{"id": "1", "source": "MED", "authorList": {"author": {"bad": 1}}}]}})
        return httpx.Response(200, json={"results": []})
    transport(handler)
    report = web_search.search("public science query", kind="academic")
    assert report["state"] == "success"
    assert all(row["authors"] == [] for row in report["results"])


def test_extract_validates_before_provider_and_records_extraction_not_origin_get(transport, monkeypatch):
    validated = []
    def validate(url, *, timeout):
        validated.append((url, timeout))
        return "https://example.org/source"
    monkeypatch.setattr(web_search, "_validate_public_url", validate)
    raw = "Line one\r\nLine two\n第三行"
    calls, _ = transport(lambda request: httpx.Response(200, json={"results": [{
        "url": "https://example.org/source", "raw_content": raw}], "failed_results": []}))
    report = web_search.extract("https://example.org/source#frag", max_chars=15)
    assert validated and validated[0][1] == 15
    assert len(calls) == 1 and str(calls[0].url) == "https://api.tavily.com/extract"
    assert json.loads(calls[0].content) == {"urls": ["https://example.org/source"], "format": "text", "extract_depth": "basic"}
    assert report["extracted"] is True and report["state"] == "success"
    assert report["retrieval_mode"] == "provider_extract" and report["source_http_verified"] is False
    assert "source_http_status" not in report
    assert report["text"] == raw[:15] and report["truncated"] is True
    assert report["text_sha256"] == hashlib.sha256(raw[:15].encode()).hexdigest()
    assert report["retrieved_at"].endswith("Z")


@pytest.mark.parametrize("error,expected", [(ValueError("private endpoint"), "rejected"),
    (OSError("DNS private secret"), "unavailable"), (TimeoutError("DNS secret"), "unavailable")])
def test_unsafe_or_unresolved_extract_never_contacts_provider_or_returns_private_url(transport, monkeypatch, error, expected):
    def reject(url, *, timeout):
        raise error
    monkeypatch.setattr(web_search, "_validate_public_url", reject)
    calls, _ = transport(lambda request: pytest.fail("unsafe URL contacted provider"))
    report = web_search.extract("http://127.0.0.1/private")
    assert not calls and report["state"] == expected
    assert report["publicURL"] == "" and report["extracted"] is False
    assert "127.0.0.1" not in json.dumps(report) and "secret" not in json.dumps(report)


@pytest.mark.parametrize("body", [
    {"results": [{"url": "https://different.example.org/source", "raw_content": "Other source"}]},
    {"results": [], "failed_results": [{"error": "private secret"}]},
    {"results": [{"url": "https://example.org/source", "raw_content": ""}]},
    {},
])
def test_extract_never_attributes_unrelated_missing_or_failed_text_to_requested_url(transport, monkeypatch, body):
    monkeypatch.setattr(web_search, "_validate_public_url", lambda url, **kwargs: url)
    transport(lambda request: httpx.Response(200, json=body))
    report = web_search.extract("https://example.org/source")
    assert report["state"] == "unavailable" and report["extracted"] is False
    assert report["text"] == "" and report["text_sha256"] is None
    assert "private secret" not in json.dumps(report)


def test_extract_dns_work_counts_toward_total_budget(transport, monkeypatch):
    clock = [10.0]
    monkeypatch.setattr(web_search.time, "monotonic", lambda: clock[0])
    def validate(url, **kwargs):
        clock[0] += 16
        return url
    monkeypatch.setattr(web_search, "_validate_public_url", validate)
    calls, _ = transport(lambda request: pytest.fail("exhausted budget contacted provider"))
    report = web_search.extract("https://example.org/source", timeout=15)
    assert not calls and report["attempts"][0]["state"] == "budget_exhausted"


def test_capabilities_is_offline_and_disabled_mode_performs_no_network_or_dns(monkeypatch):
    monkeypatch.setattr(web_search.httpx, "Client", lambda **kwargs: pytest.fail("configuration used network"))
    monkeypatch.setattr(web_search, "_validate_public_url", lambda *args, **kwargs: pytest.fail("disabled used DNS"))
    monkeypatch.setenv("SKILLNET_WEB_ENABLED", "false")
    monkeypatch.setenv("TAVILY_API_KEY", "private-test-secret")
    caps = web_search.capabilities()
    assert caps["enabled"] is False and caps["key_configured"] is True and caps["mode"] == "authenticated"
    assert "private-test-secret" not in json.dumps(caps)
    assert web_search.search("public query")["state"] == "disabled"
    assert web_search.extract("https://example.org")["state"] == "disabled"


@pytest.mark.parametrize("kwargs", [
    {"query": ""}, {"query": " "}, {"query": None}, {"query": "x" * 2001},
    {"query": "x", "limit": 0}, {"query": "x", "limit": True}, {"query": "x", "limit": 11},
    {"query": "x", "kind": "unknown"}, {"query": "x", "kind": {}},
    {"query": "x", "timeout": True}, {"query": "x", "timeout": float("inf")},
    {"query": "x", "timeout": float("nan")}, {"query": "x", "timeout": 61},
    {"query": "x", "timeout": 10 ** 400},
])
def test_invalid_search_parameters_fail_locally_without_network(monkeypatch, kwargs):
    monkeypatch.setattr(web_search.httpx, "Client", lambda **kwargs: pytest.fail("invalid input used network"))
    with pytest.raises(ValueError):
        web_search.search(**kwargs)


@pytest.mark.parametrize("max_chars", [0, True, 100001, "20"])
def test_invalid_extract_size_fails_locally(monkeypatch, max_chars):
    monkeypatch.setattr(web_search.httpx, "Client", lambda **kwargs: pytest.fail("invalid input used network"))
    with pytest.raises(ValueError):
        web_search.extract("https://example.org/source", max_chars=max_chars)
