"""Bounded, real network discovery through fixed public provider endpoints.

Provider results are evidence candidates, never an identity verdict or executable
instructions.  Anonymous Tavily access is officially supported but rate limited;
an exhausted allowance is reported instead of replaced with simulated sources.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import math
import os
import re
import time
from urllib.parse import quote, urlsplit, urlunsplit

import httpx


SEARCH_VERSION = "skillnet-web-search-v1"
EXTRACT_VERSION = "skillnet-web-extract-v1"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_TAVILY = "https://api.tavily.com"
_CROSSREF = "https://api.crossref.org/works"
_EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_USER_AGENT = "SkillNet-Demo/1.0 (+https://github.com/qing1989620/skillnet-demo)"


def _enabled() -> bool:
    return os.getenv("SKILLNET_WEB_ENABLED", "true").strip().lower() not in {
        "0", "false", "off", "no",
    }


def _api_key() -> str:
    return os.getenv("TAVILY_API_KEY", "").strip()


def capabilities() -> dict:
    """Describe configuration without a request or disclosing a credential."""
    configured = bool(_api_key())
    return {
        "version": SEARCH_VERSION,
        "enabled": _enabled(),
        "mode": "authenticated" if configured else "keyless",
        "key_configured": configured,
        "keyless": not configured,
        "providers": ["tavily", "crossref", "europepmc"],
        "availability": "unprobed",
        "source_verification_required": True,
        "boundary": "Configuration only; provider availability and anonymous quotas are checked per request.",
    }


def _timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("timeout must be a finite number between 1 and 60 seconds")
    if not 1 <= value <= 60 or not math.isfinite(value):
        raise ValueError("timeout must be a finite number between 1 and 60 seconds")
    return float(value)


def _text(value, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def _rows(value, maximum: int) -> list:
    return value[:maximum] if isinstance(value, list) else []


def _result_url(value) -> str:
    """Filter obvious unsafe candidates; fetching also requires DNS validation."""
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username is not None or parsed.password is not None:
            return ""
        host = parsed.hostname.lower().rstrip(".")
        if not host or host == "localhost" or "." not in host:
            return ""
        if host.endswith((".localhost", ".local", ".internal", ".test", ".invalid")):
            return ""
        if parsed.port not in {None, 80, 443}:
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path, parsed.query, ""))
    except (TypeError, ValueError):
        return ""


def _headers(key: str) -> dict:
    if key:
        return {"Content-Type": "application/json", "Authorization": "Bearer " + key,
                "X-Client-Source": "skillnet-demo"}
    return {"Content-Type": "application/json", "X-Tavily-Access-Mode": "keyless",
            "X-Client-Source": "tavily-python-keyless"}


def _retry_seconds(headers, body) -> int | None:
    raw = headers.get("retry-after", "")
    err = body.get("error") if isinstance(body, dict) else None
    candidate = err.get("retry_after_seconds") if isinstance(err, dict) else None
    if candidate is None and isinstance(raw, str) and len(raw) <= 8 and raw.isdecimal():
        candidate = int(raw)
    if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
        if 0 <= candidate <= 86400 and math.isfinite(candidate):
            return int(candidate)
    return None


def _attempt(provider: str, state: str, reason: str, status=None, retry=None) -> dict:
    row = {"provider": provider, "status_code": status, "state": state, "reason": reason}
    if retry is not None:
        row["retry_after_seconds"] = retry
    return row


def _request(provider: str, method: str, url: str, *, deadline: float,
             headers=None, params=None, payload=None) -> tuple[dict | None, dict]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None, _attempt(provider, "budget_exhausted", "total_time_budget_exhausted")
    try:
        with httpx.Client(timeout=remaining, trust_env=False, follow_redirects=False) as client:
            with client.stream(method, url, headers=headers or {"User-Agent": _USER_AGENT},
                               params=params, json=payload) as response:
                status = response.status_code
                raw = bytearray()
                for chunk in response.iter_bytes(chunk_size=65536):
                    if time.monotonic() > deadline:
                        return None, _attempt(provider, "timeout", "total_time_budget_exhausted", status)
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        return None, _attempt(provider, "invalid_response", "response_size_limit", status)
                try:
                    body = json.loads(raw)
                except (ValueError, UnicodeError, RecursionError):
                    body = None
                retry = _retry_seconds(response.headers, body)
                if status == 429:
                    return None, _attempt(provider, "rate_limited", "provider_rate_limit", status, retry)
                if status == 401:
                    return None, _attempt(provider, "authentication_required", "provider_authentication_required", status)
                if status == 403:
                    return None, _attempt(provider, "access_denied", "provider_access_denied", status, retry)
                if 300 <= status < 400:
                    return None, _attempt(provider, "unavailable", "provider_redirect_not_followed", status)
                if status < 200 or status >= 300:
                    return None, _attempt(provider, "unavailable", "provider_http_error", status, retry)
                if not isinstance(body, dict):
                    return None, _attempt(provider, "invalid_response", "expected_json_object", status)
                if isinstance(body.get("error"), dict):
                    code = body["error"].get("code")
                    limited = isinstance(code, str) and any(x in code.lower() for x in ("limit", "quota", "budget"))
                    return None, _attempt(provider, "rate_limited" if limited else "unavailable",
                        "provider_rate_limit" if limited else "provider_error_envelope", status, retry)
                return body, _attempt(provider, "success", "live_provider_response", status)
    except httpx.TimeoutException:
        return None, _attempt(provider, "timeout", "provider_request_timeout")
    except httpx.HTTPError:
        # Exception messages can contain query strings, keys, or proxy settings.
        return None, _attempt(provider, "unavailable", "provider_network_error")


def _tavily(query: str, limit: int, key: str, deadline: float) -> tuple[list, dict]:
    body, attempt = _request("tavily", "POST", _TAVILY + "/search", deadline=deadline,
        headers=_headers(key), payload={"query": query, "max_results": limit,
            "include_answer": False, "include_raw_content": False})
    if body is None:
        return [], attempt
    raw_results = body.get("results")
    if not isinstance(raw_results, list):
        return [], _attempt("tavily", "invalid_response", "missing_results_list", attempt["status_code"])
    results = []
    for row in raw_results[:50]:
        if not isinstance(row, dict):
            continue
        url = _result_url(row.get("url"))
        if url:
            results.append({"title": _text(row.get("title"), 500), "url": url,
                "snippet": _text(row.get("content"), 3000), "provider": "tavily"})
    return results[:limit], _results_attempt(attempt, raw_results, results)


def _results_attempt(attempt: dict, raw_results: list, results: list) -> dict:
    if raw_results and not results:
        return _attempt(attempt["provider"], "invalid_response", "no_usable_public_result", attempt["status_code"])
    if not raw_results:
        return _attempt(attempt["provider"], "empty", "live_provider_returned_zero_results", attempt["status_code"])
    return attempt


def _crossref(query: str, limit: int, deadline: float) -> tuple[list, dict]:
    body, attempt = _request("crossref", "GET", _CROSSREF, deadline=deadline,
        params={"query": query, "rows": limit})
    if body is None:
        return [], attempt
    message = body.get("message")
    raw_results = message.get("items") if isinstance(message, dict) else None
    if not isinstance(raw_results, list):
        return [], _attempt("crossref", "invalid_response", "missing_items_list", attempt["status_code"])
    results = []
    for row in raw_results[:50]:
        if not isinstance(row, dict):
            continue
        doi = _text(row.get("DOI"), 500)
        url = _result_url(row.get("URL"))
        if not url and re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            url = "https://doi.org/" + quote(doi, safe="/()")
        if not url:
            continue
        titles = row.get("title")
        title = _text(titles[0], 500) if isinstance(titles, list) and titles else ""
        authors, affiliations = [], []
        for author in _rows(row.get("author"), 100):
            if not isinstance(author, dict):
                continue
            name = _text(" ".join(str(author.get(k) or "") for k in ("given", "family")), 200)
            if name:
                authors.append(name)
            for affiliation in _rows(author.get("affiliation"), 20):
                if isinstance(affiliation, dict):
                    value = _text(affiliation.get("name"), 500)
                    if value and value not in affiliations:
                        affiliations.append(value)
        abstract = _text(re.sub(r"<[^>]*>", " ", row.get("abstract", ""))
                         if isinstance(row.get("abstract"), str) else "", 3000)
        results.append({"title": title, "url": url, "snippet": abstract or title,
            "provider": "crossref", "doi": doi, "authors": authors, "affiliations": affiliations[:50]})
    return results[:limit], _results_attempt(attempt, raw_results, results)


def _europepmc(query: str, limit: int, deadline: float) -> tuple[list, dict]:
    body, attempt = _request("europepmc", "GET", _EUROPEPMC, deadline=deadline,
        params={"query": query, "pageSize": limit, "format": "json", "resultType": "core"})
    if body is None:
        return [], attempt
    result_list = body.get("resultList")
    raw_results = result_list.get("result") if isinstance(result_list, dict) else None
    if not isinstance(raw_results, list):
        return [], _attempt("europepmc", "invalid_response", "missing_results_list", attempt["status_code"])
    results = []
    for row in raw_results[:50]:
        if not isinstance(row, dict):
            continue
        source, identifier = _text(row.get("source"), 20), _text(row.get("id"), 80)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source) or not re.fullmatch(r"[A-Za-z0-9._-]+", identifier):
            continue
        title = _text(row.get("title"), 500)
        author_list = row.get("authorList")
        raw_authors = author_list.get("author") if isinstance(author_list, dict) else []
        authors, affiliations = [], []
        for author in _rows(raw_authors, 100):
            if not isinstance(author, dict):
                continue
            name = _text(author.get("fullName"), 200)
            if name:
                authors.append(name)
            details = author.get("authorAffiliationDetailsList")
            rows = details.get("authorAffiliation") if isinstance(details, dict) else []
            for affiliation in _rows(rows, 20):
                if isinstance(affiliation, dict):
                    value = _text(affiliation.get("affiliation"), 500)
                    if value and value not in affiliations:
                        affiliations.append(value)
        results.append({"title": title,
            "url": "https://europepmc.org/article/" + source + "/" + identifier,
            "snippet": _text(row.get("abstractText"), 3000) or title,
            "provider": "europepmc", "doi": _text(row.get("doi"), 500),
            "authors": authors, "affiliations": affiliations[:50]})
    return results[:limit], _results_attempt(attempt, raw_results, results)


def search(query: str, *, limit: int = 5, kind: str = "web", timeout: float = 15) -> dict:
    """Search live sources; academic mode adds two public scholarly catalogues."""
    if not isinstance(query, str) or not query.strip() or len(query) > 2000:
        raise ValueError("query must contain 1 to 2000 characters")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ValueError("limit must be an integer between 1 and 10")
    if not isinstance(kind, str) or kind not in {"web", "academic"}:
        raise ValueError("kind must be web or academic")
    budget = _timeout(timeout)
    key = _api_key()
    report = {"version": SEARCH_VERSION, "query": query.strip(), "kind": kind,
        "state": "disabled", "results": [], "attempts": [], "provider": "tavily" if kind == "web"
        else "crossref+europepmc+tavily", "keyless": not bool(key),
        "source_verification_required": True}
    if not _enabled():
        return report
    deadline = time.monotonic() + budget
    batches = []
    providers = [_crossref, _europepmc] if kind == "academic" else []
    for provider in providers:
        rows, attempt = provider(query.strip(), limit, deadline)
        batches.append(rows)
        report["attempts"].append(attempt)
    rows, attempt = _tavily(query.strip(), limit, key, deadline)
    batches.append(rows)
    report["attempts"].append(attempt)
    seen = set()
    # Round-robin preserves multiple sources within the small returned budget.
    for index in range(limit):
        for batch in batches:
            if index < len(batch) and batch[index]["url"] not in seen:
                report["results"].append(batch[index])
                seen.add(batch[index]["url"])
            if len(report["results"]) >= limit:
                break
        if len(report["results"]) >= limit:
            break
    failures = any(a["state"] not in {"success", "empty"} for a in report["attempts"])
    report["state"] = ("partial" if failures else "success") if report["results"] else (
        "unavailable" if failures else "empty")
    return report


def _validate_public_url(url: str, *, timeout: float) -> str:
    # Shared fetch boundary resolves DNS and rejects internal/reserved addresses.
    # Import lazily so configuration reporting never performs resolution.
    from .web_fetch import validate_url
    return validate_url(url, timeout=timeout)


def extract(url: str, *, timeout: float = 15, max_chars: int = 20000) -> dict:
    """Request provider extraction, explicitly distinct from an origin HTTP GET."""
    budget = _timeout(timeout)
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or not 1 <= max_chars <= 100000:
        raise ValueError("max_chars must be an integer between 1 and 100000")
    key = _api_key()
    report = {"version": EXTRACT_VERSION, "state": "disabled", "extracted": False,
        "publicURL": "", "provider": "tavily", "retrieval_mode": "provider_extract",
        "keyless": not bool(key), "retrieved_at": None, "text": "", "text_sha256": None,
        "attempts": [], "source_http_verified": False,
        "boundary": "Third-party extraction may use cached content; origin HTTP status, redirect safety, and factual claims are not certified."}
    if not _enabled():
        return report
    deadline = time.monotonic() + budget
    try:
        public_url = _validate_public_url(url, timeout=budget)
    except ValueError:
        report["state"] = "rejected"
        report["attempts"] = [_attempt("url_validator", "rejected", "unsafe_or_invalid_public_url")]
        return report
    except (OSError, TimeoutError):
        report["state"] = "unavailable"
        report["attempts"] = [_attempt("url_validator", "unavailable", "public_url_resolution_failed")]
        return report
    report["publicURL"] = public_url
    body, attempt = _request("tavily", "POST", _TAVILY + "/extract",
        deadline=deadline, headers=_headers(key),
        payload={"urls": [public_url], "format": "text", "extract_depth": "basic"})
    report["attempts"].append(attempt)
    if body is None:
        report["state"] = "unavailable"
        return report
    rows = body.get("results")
    if not isinstance(rows, list):
        report["attempts"][-1] = _attempt("tavily", "invalid_response", "missing_results_list", attempt["status_code"])
        report["state"] = "unavailable"
        return report
    for row in rows[:10]:
        if not isinstance(row, dict) or _result_url(row.get("url")) != _result_url(public_url):
            continue
        text = row.get("raw_content")
        if not isinstance(text, str) or not text.strip():
            continue
        report.update(state="success", extracted=True, text=text[:max_chars],
            truncated=len(text) > max_chars, retrieved_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        report["text_sha256"] = hashlib.sha256(report["text"].encode("utf-8")).hexdigest()
        return report
    report["state"] = "unavailable"
    report["attempts"][-1] = _attempt("tavily", "invalid_response", "requested_url_not_extracted", attempt["status_code"])
    return report
