"""Independent invariants for host evidence, beyond a model's self evaluation."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from skillnet import web_research


NAME = "肖海冰"
INSTITUTION = "测试大学"
DOMAIN = "海洋科学"
TASK = "请调研肖海冰的著作，先核验人物机构与研究领域"
URL_A = "https://first-source.org/profile"
URL_B = "https://second-source.net/person"
URL_C = "https://unrelated-source.edu/catalogue"
BODY_A = "肖海冰在测试大学从事海洋科学研究。此公开页面提供人物机构与研究方向的文字记录。"
BODY_B = "研究人员肖海冰，机构为测试大学，研究领域为海洋科学。此页面独立记录这些有限字段。"
BODY_C = "本页面是公共目录和其他人物的索引，没有上述人物的机构与领域证据。"


def csv_file(workspace: Path, rows: list[dict], name="claims.csv") -> Path:
    path = workspace / "outputs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def identity_row(**extra):
    return {"name": NAME, "institution": INSTITUTION, "domain": DOMAIN,
        "source_id": "web-01", "evidence_url": URL_A, "same_person": "true", **extra}


@pytest.fixture
def evidence(monkeypatch, tmp_path):
    """Exercise collection's real snapshot writer; only outbound I/O is mocked."""
    calls = {"search": [], "fetch": [], "extract": []}
    bodies = {URL_A: BODY_A, URL_B: BODY_B}
    monkeypatch.setattr(web_research.web_search, "capabilities", lambda: {"enabled": True})

    def search(query, **kwargs):
        calls["search"].append((query, kwargs))
        return {"state": "success", "results": [{"title": "Public source", "url": url,
            "snippet": "A search snippet is not verified body text", "provider": "test_provider"}
            for url in bodies], "attempts": [{"provider": "test_provider", "state": "success", "status_code": 200}]}

    def fetch(url, **kwargs):
        calls["fetch"].append((url, kwargs))
        if url not in bodies:
            return {"state": "failed", "requested_url": url, "final_url": url,
                "status_code": None, "text": "", "raw_body": b"",
                "reason": "No test fixture source was supplied for this public URL"}
        raw = bodies[url].encode("utf-8")
        return {"state": "fetched", "requested_url": url, "final_url": url,
            "status_code": 200, "content_type": "text/plain; charset=utf-8",
            "body_sha256": hashlib.sha256(raw).hexdigest(), "body_bytes": len(raw),
            "text": bodies[url], "title": "Public source", "raw_body": raw,
            "redirect_chain": [], "retrieved_at": "2026-10-13T00:00:00Z", "reason": "public snapshot"}

    def extract(url, **kwargs):
        calls["extract"].append((url, kwargs))
        return {"state": "unavailable", "extracted": False, "text": "", "attempts": []}

    monkeypatch.setattr(web_research.web_search, "search", search)
    monkeypatch.setattr(web_research.web_fetch, "fetch_url", fetch)
    monkeypatch.setattr(web_research.web_search, "extract", extract)
    return SimpleNamespace(workspace=tmp_path, calls=calls, bodies=bodies,
        collect=lambda **kwargs: web_research.collect(TASK, tmp_path, **kwargs))


def test_identity_intent_is_scoped_to_public_name_not_all_user_input():
    decision = web_research.intent(TASK)
    assert decision["needed"] is True and decision["enabled"] is True
    assert decision["identity_name"] == NAME
    assert NAME in decision["query"] and len(decision["query"]) <= 240
    assert web_research.intent("计算本地 CSV 各列平均值")["enabled"] is False


@pytest.mark.parametrize("task,mode", [
    (TASK, "off"), ("不要联网，" + TASK, "on"), ("禁止网络搜索，" + TASK, "auto"),
    ("只使用提供数据，核验引用", "on"), ("内部未公开保密资料，检索相关论文", "on"),
])
def test_explicit_offline_or_confidential_request_never_contacts_network(evidence, task, mode):
    report = web_research.collect(task, evidence.workspace, mode=mode, discover_missing=True)
    assert report["state"] in {"disabled", "not_needed"}
    assert report["sources"] == [] and report["attempts"] == []
    assert not any(evidence.calls.values())
    assert not (evidence.workspace / "artifacts" / "web_sources.json").exists()


def test_provider_globally_disabled_never_searches_fetches_or_discovers(evidence, monkeypatch):
    monkeypatch.setattr(web_research.web_search, "capabilities", lambda: {"enabled": False})
    report = evidence.collect(mode="on", discover_missing=True)
    assert report["state"] == "disabled" and not any(evidence.calls.values())


def test_search_query_redacts_explicit_credentials_code_paths_phone_and_email(evidence):
    task = ("搜索最新公开论文，api_key=top-secret-key token=top-secret-token "
        "password=top-secret-password 联系 research-private@example.org 13812345678 "
        "C:\\private\\secret.csv /home/research/private.txt ```python\nPRIVATE_CODE=1\n``` ")
    web_research.collect(task, evidence.workspace)
    query = evidence.calls["search"][0][0]
    for secret in ("top-secret", "research-private", "13812345678", "secret.csv", "private.txt", "PRIVATE_CODE"):
        assert secret not in query


def test_url_credentials_and_secret_query_parameters_are_not_sent_to_search(evidence):
    task = "检索 https://private-user:private-pass@public-source.org/profile?access_key=private-value&sig=private-signature"
    report = web_research.collect(task, evidence.workspace)
    query = evidence.calls["search"][0][0]
    assert all(secret not in query for secret in ("private-user", "private-pass", "private-value", "private-signature"))
    explicit = next(source for source in report["sources"] if source["provider"] == "user_url")
    assert explicit["requested_url"] == "https://public-source.org/profile"
    assert explicit["state"] == "failed" and not explicit["text"]
    assert all(secret not in url for url, _ in evidence.calls["fetch"]
        for secret in ("private-user", "private-pass", "private-value", "private-signature"))


def test_https_documentation_url_is_not_mistaken_for_a_windows_path():
    url = "https://www.crossref.org/documentation/retrieve-metadata/rest-api/"
    decision = web_research.intent("请检索并核验 " + url)
    assert decision["enabled"] is True
    assert url in decision["query"]


def test_public_documentation_query_keeps_url_and_excludes_private_csv_rows(evidence):
    url = "https://www.crossref.org/documentation/retrieve-metadata/rest-api/"
    task = "请联网核验 " + url + "，交付 sources.csv。\nemployee,salary\nAlice,97000\nBob,65000\n"
    report = web_research.collect(task, evidence.workspace)
    query = evidence.calls["search"][0][0]
    assert url in query
    assert all(private not in query for private in ("Alice", "Bob", "97000", "65000", "employee,salary"))
    assert any(source["provider"] == "user_url" for source in report["sources"])


def test_payroll_research_never_sends_employee_rows_to_provider(evidence):
    task = "请搜索工资分析的公开方法\nemployee,salary\nAlice,97000\nBob,65000\n"
    web_research.collect(task, evidence.workspace)
    query = evidence.calls["search"][0][0]
    assert query.strip()
    assert all(private not in query for private in ("Alice", "Bob", "97000", "65000"))


@pytest.mark.parametrize("task", [
    "Do not browse. Search the latest public papers.",
    "Do not access the internet. Verify citations from provided data only.",
    "No web search. Research this question offline only.",
])
def test_english_explicit_offline_policy_never_contacts_any_provider(evidence, task):
    report = web_research.collect(task, evidence.workspace, mode="on", discover_missing=True)
    assert report["state"] == "disabled" and not any(evidence.calls.values())


def test_collection_freezes_real_raw_bytes_and_original_source_binding(evidence):
    report = evidence.collect()
    assert report["state"] == "success" and len(report["sources"]) == 2
    assert len(evidence.calls["search"]) == 1 and len(evidence.calls["fetch"]) == 2
    assert not evidence.calls["extract"]
    assert report["identity_name"] == NAME
    for source in report["sources"]:
        raw = (evidence.workspace / "artifacts" / source["text_file"]).read_bytes()
        assert raw == evidence.bodies[source["requested_url"]].encode("utf-8")
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert source["retrieval_mode"] == "direct_fetch" and source["status_code"] == 200
    index = evidence.workspace / "artifacts" / report["evidence_file"]
    assert hashlib.sha256(index.read_bytes()).hexdigest() == report["evidence_sha256"]


def test_collection_failure_preserves_unknown_and_never_invents_source_content(evidence, monkeypatch):
    monkeypatch.setattr(web_research.web_fetch, "fetch_url", lambda url, **kwargs: {
        "state": "failed", "requested_url": url, "status_code": 503,
        "text": "", "raw_body": b"", "reason": "network unavailable"})
    report = evidence.collect()
    assert report["state"] == "unavailable"
    assert report["sources"] and all(source["state"] == "failed" for source in report["sources"])
    assert all(not source.get("text") and not source.get("text_file") for source in report["sources"])
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_search_snippet_alone_cannot_verify_a_quote_or_person(evidence, monkeypatch):
    monkeypatch.setattr(web_research.web_fetch, "fetch_url", lambda url, **kwargs: {
        "state": "failed", "requested_url": url, "reason": "not fetched"})
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row(quote="A search snippet is not verified body text")])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_provider_extract_is_accepted_but_never_labeled_as_direct_origin_get(evidence, monkeypatch):
    monkeypatch.setattr(web_research.web_fetch, "fetch_url", lambda url, **kwargs: {
        "state": "failed", "requested_url": url, "status_code": 403, "reason": "origin forbidden"})
    monkeypatch.setattr(web_research.web_search, "extract", lambda url, **kwargs: {
        "state": "success", "extracted": True, "publicURL": url, "provider": "tavily",
        "retrieval_mode": "provider_extract", "source_http_verified": False,
        "text": evidence.bodies[url], "retrieved_at": "2026-10-13T00:00:00Z",
        "attempts": [{"provider": "tavily", "status_code": 200, "state": "success"}]})
    report = evidence.collect()
    assert report["state"] == "success"
    for source in report["sources"]:
        assert source["state"] == "extracted" and source["retrieval_mode"] == "provider_extract"
        assert source["status_code"] is None
        assert (evidence.workspace / "artifacts" / source["text_file"]).read_text(encoding="utf-8") == source["text"]


def test_valid_quote_only_proves_text_presence_not_claim_entailment(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A,
        "claim": "A broader claim requires separate entailment validation", "quote": BODY_A[:25]}])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 1 and audit["failed"] == 0
    assert "蕴含" in audit["items"][0]["reason"]


@pytest.mark.parametrize("quote", [
    " " * 12,
    "\u200b" * 12,
    "\u200b\u200c\u200d\ufeff" * 3,
    NAME + " " * 20,
])
def test_invisible_or_short_effective_quotes_cannot_pass_by_length_padding(evidence, quote):
    # Invisible formatting can occur in a real page; byte presence is insufficient.
    evidence.bodies[URL_A] += quote
    report = evidence.collect()
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A,
        "claim": "An asserted factual claim requires a substantive excerpt", "quote": quote}])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["failed"] == 1 and audit["verified"] == 0


@pytest.mark.parametrize("quote", [" " * 12, "\u200b" * 12,
    "\u200b\u200c\u200d\ufeff" * 3, NAME + " " * 20])
def test_grounded_reply_does_not_treat_padded_empty_excerpts_as_verified_claims(evidence, quote):
    report = evidence.collect()
    # Even an externally supplied/stale audit cannot unlock the free-form answer
    # through a truthy string that contains no substantive quoted evidence.
    report["citation_audit"] = {"state": "verified", "identity_state": "verified",
        "items": [{"state": "verified", "quote": quote}]}
    assert web_research.grounded_reply(report) is not None


@pytest.mark.parametrize("row", [
    {"source_id": "web-01", "evidence_url": URL_B, "quote": BODY_A[:25]},
    {"source_id": "web-01", "evidence_url": "https://fabricated.example.org/source", "quote": BODY_A[:25]},
])
def test_source_id_cannot_be_rebound_to_another_actual_or_fabricated_url(evidence, row):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [row])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["failed"] == 1 and audit["verified"] == 0


def test_unknown_source_id_is_not_repaired_by_matching_url(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [{"source_id": "not-collected", "evidence_url": URL_A, "quote": BODY_A[:25]}])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_snapshot_byte_mutation_invalidates_formerly_valid_quote(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A, "quote": BODY_A[:25]}])
    snapshot = evidence.workspace / "artifacts" / report["sources"][0]["text_file"]
    snapshot.write_bytes(snapshot.read_bytes() + b"tampered")
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["failed"] == 1


def test_in_memory_text_cannot_create_evidence_absent_from_frozen_snapshot(evidence):
    report = evidence.collect()
    invented = "这是完全凭空编造且不在真实冻结快照中的一段证据正文"
    mutated = copy.deepcopy(report)
    mutated["sources"][0]["text"] = invented
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A, "quote": invented}])
    audit = web_research.audit_files([path], mutated, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] == "failed"


def test_frozen_source_index_mutation_invalidates_evidence_bundle(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A, "quote": BODY_A[:25]}])
    index = evidence.workspace / "artifacts" / report["evidence_file"]
    index.write_bytes(index.read_bytes() + b"\n ")
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] == "failed"


def test_snapshot_cannot_be_relabelled_as_a_different_unfetched_source(evidence):
    report = evidence.collect()
    mutated = copy.deepcopy(report)
    forged_url = "https://never-fetched.org/person"
    mutated["sources"][0]["url"] = forged_url
    mutated["sources"][0]["requested_url"] = forged_url
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": forged_url, "quote": BODY_A[:25]}])
    audit = web_research.audit_files([path], mutated, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] == "failed"


def test_two_independent_intact_sources_can_support_only_the_scoped_identity_fields(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 1 and audit["failed"] == 0
    assert "有限" in audit["items"][0]["reason"]
    assert "身份证明" in audit["items"][0]["reason"]


@pytest.mark.parametrize("extra", [{"institution": "另一个大学"}, {"domain": "核物理"},
    {"institution": ""}, {"domain": ""}, {"name": "另一个人"}])
def test_same_name_is_insufficient_when_claimed_identity_fields_are_wrong_or_missing(evidence, extra):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row(**extra)])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_one_website_with_two_pages_is_not_two_independent_identity_sources(evidence):
    evidence.bodies.clear()
    evidence.bodies.update({URL_A: BODY_A, "https://first-source.org/second": BODY_B})
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["unknown"] == 1


def test_two_subdomains_of_one_website_do_not_establish_source_independence(evidence):
    evidence.bodies.clear()
    evidence.bodies.update({URL_A: BODY_A, "https://news.first-source.org/second": BODY_B})
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_two_sources_explicitly_negating_identity_fields_cannot_pass_support_gate(evidence):
    negative = NAME + "并非" + INSTITUTION + "成员，也不研究" + DOMAIN + "。请勿与其他人物混淆。"
    evidence.bodies.update({URL_A: negative, URL_B: negative})
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["identity_state"] != "verified"


def test_distant_fields_from_separate_people_do_not_form_identity_support(evidence):
    unrelated = NAME + "研究核物理。\n" + "其他公开资料。" * 100 + "\n王明是" + INSTITUTION + "的" + DOMAIN + "研究人员。"
    assert unrelated.index(INSTITUTION) - unrelated.index(NAME) > 600
    evidence.bodies.update({URL_A: unrelated, URL_B: unrelated})
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["identity_state"] != "verified"


@pytest.mark.parametrize("kind", ["snapshot", "index"])
def test_giant_frozen_files_are_rejected_before_reading_entire_content(evidence, monkeypatch, kind):
    report = evidence.collect()
    target = evidence.workspace / "artifacts" / (report["evidence_file"] if kind == "index"
        else report["sources"][0]["text_file"])
    target.write_bytes(b"x" * 2_000_001)
    original_read = Path.read_bytes
    def bounded_read(path):
        if path.resolve() == target.resolve():
            pytest.fail("oversized frozen evidence was read before the size gate")
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", bounded_read)
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A, "quote": BODY_A[:25]}])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["verified"] == 0


def test_unrelated_current_citation_cannot_borrow_identity_support_from_other_sources(evidence):
    evidence.bodies[URL_C] = BODY_C
    report = evidence.collect()
    source = next(source for source in report["sources"] if source["url"] == URL_C)
    path = csv_file(evidence.workspace, [identity_row(source_id=source["source_id"], evidence_url=URL_C)])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_false_quote_cannot_be_overridden_by_otherwise_valid_identity_fields(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row(quote="这段引文从未出现于任何已取得的原始来源正文")])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] == "failed" and audit["failed"] == 1


def test_unknown_identity_is_preserved_instead_of_promoted_by_a_valid_quote(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [identity_row(same_person="unknown", quote=BODY_A[:25])])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["unknown"] == 1


def test_deleted_snapshot_fails_identity_support_closed(evidence):
    report = evidence.collect()
    snapshot = evidence.workspace / "artifacts" / report["sources"][0]["text_file"]
    snapshot.unlink()
    path = csv_file(evidence.workspace, [identity_row()])
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["verified"] == 0


def test_missing_csv_is_a_failed_audit_not_an_unhandled_exception(evidence):
    report = evidence.collect()
    audit = web_research.audit_files([evidence.workspace / "outputs" / "missing.csv"], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["verified"] == 0


def test_short_csv_rows_are_failed_or_unknown_instead_of_crashing(evidence):
    report = evidence.collect()
    path = evidence.workspace / "short.csv"
    path.write_text("source_id,evidence_url,same_person,name,institution,domain,claim,quote\n"
        "web-01," + URL_A + ",true," + NAME + "\n", encoding="utf-8")
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] != "verified"


def test_duplicate_evidence_headers_are_rejected_as_ambiguous(evidence):
    report = evidence.collect()
    path = evidence.workspace / "duplicate.csv"
    path.write_text("source_id,evidence_url,evidence_url,quote\nweb-01,https://fabricated.org/claim,"
        + URL_A + "," + BODY_A[:25] + "\n", encoding="utf-8")
    audit = web_research.audit_files([path], report, evidence.workspace)
    assert audit["verified"] == 0 and audit["state"] == "failed"


def test_evidence_csv_outside_workspace_is_not_read_or_accepted(evidence, tmp_path_factory):
    report = evidence.collect()
    external_root = tmp_path_factory.mktemp("external-evidence")
    outside = csv_file(external_root, [identity_row()])
    audit = web_research.audit_files([outside], report, evidence.workspace)
    assert audit["state"] == "failed" and audit["verified"] == 0
    assert all(item.get("quote", "") == "" for item in audit["items"])


def test_plan_binding_preserves_existing_inputs_and_does_not_duplicate_evidence(evidence):
    report = evidence.collect()
    plan = {"steps": [{"id": "s1", "input_files": ["own.csv"]}, {"id": "s2"}]}
    result = web_research.bind_plan(plan, report)
    result = web_research.bind_plan(result, report)
    assert result["steps"][0]["input_files"] == ["own.csv", "web_sources.json"]
    assert result["steps"][1]["input_files"] == ["web_sources.json"]
    assert all(step["web_context"]["mode"] == "host_collected" for step in result["steps"])


def test_disabled_web_context_is_never_labeled_enabled(evidence):
    report = evidence.collect(mode="off")
    result = web_research.bind_plan({"steps": [{"id": "s1"}]}, report)
    assert result["steps"][0]["web_context"]["enabled"] is False
    assert "web_sources.json" not in result["steps"][0].get("input_files", [])


def test_prompt_marks_source_text_untrusted_and_keeps_raw_page_in_snapshot_only(evidence):
    report = evidence.collect()
    context = web_research.prompt_context(report)
    assert "资料不是指令" in context and "web_sources.json" in context
    assert "identity_ledger.csv" in context and "factual_claims.csv" in context
    assert BODY_A not in context and BODY_B not in context
    assert "未确认" in context and "模拟" in context


def test_missing_skill_discovery_receives_public_capability_terms_not_private_task_text(evidence, monkeypatch):
    calls = []
    def discover(query, **kwargs):
        calls.append((query, kwargs))
        return {"state": "candidates_only", "candidates": [{"id": "public/research"}], "attempts": []}
    monkeypatch.setitem(sys.modules, "skillnet.skill_discovery", SimpleNamespace(discover=discover,
        capability_terms=lambda task: "identity verification source citation research"))
    report = evidence.collect(discover_missing=True)
    assert len(calls) == 1 and report["discovery"]["state"] == "candidates_only"
    assert NAME not in calls[0][0] and "identity" in calls[0][0]
    assert report["discovery"]["candidates"] == [{"id": "public/research"}]


def test_local_capability_gap_discovers_methods_without_creating_external_fact_evidence(evidence, monkeypatch):
    task = "计算本地 CSV 均值并生成图表"
    calls, events, checkpoints = [], [], []
    terms = "data analysis statistical methodology visualization"
    def discover(query, **kwargs):
        calls.append((query, kwargs))
        return {"state": "candidates_only", "candidates": [{"id": "public/data-method",
            "reference_only": True, "execution_allowed": False, "certified": False}], "attempts": []}
    monkeypatch.setitem(sys.modules, "skillnet.skill_discovery", SimpleNamespace(discover=discover,
        capability_terms=lambda input_task: terms if input_task == task else pytest.fail("wrong capability task")))
    report = web_research.collect(task, evidence.workspace, discover_missing=True,
        emit=lambda kind, **fields: events.append((kind, fields)), checkpoint=lambda: checkpoints.append(True))
    assert calls == [(terms, {"timeout": 18})]
    assert report["needed"] is False and report["state"] == "not_needed"
    assert report["sources"] == [] and report["queries"] == [] and report["attempts"] == []
    assert not any(evidence.calls.values()) and not report.get("evidence_file")
    assert not (evidence.workspace / "artifacts").exists()
    assert report["discovery"]["candidates"][0]["execution_allowed"] is False
    assert [kind for kind, _ in events] == ["web.skills.discovered"] and checkpoints
    plan = {"steps": [{"action": "计算本地 CSV 均值", "input_files": ["data.csv"]}]}
    assert web_research.bind_plan(copy.deepcopy(plan), report) == plan
    assert web_research.audit_files([], report, evidence.workspace)["state"] == "not_applicable"
    assert web_research.grounded_reply(report) is None
    context = web_research.prompt_context(report)
    assert "identity_ledger.csv" not in context and "factual_claims.csv" not in context


def test_method_discovery_failure_does_not_turn_local_analysis_into_external_fact_failure(evidence, monkeypatch):
    def discover(query, **kwargs):
        return {"state": "unavailable", "candidates": [], "attempts": [{"state": "rate_limited"}]}
    monkeypatch.setitem(sys.modules, "skillnet.skill_discovery", SimpleNamespace(discover=discover,
        capability_terms=lambda task: "data analysis"))
    report = web_research.collect("计算本地 CSV 均值", evidence.workspace, discover_missing=True)
    assert report["needed"] is False and report["state"] == "not_needed"
    assert report["discovery"]["state"] == "unavailable" and report["sources"] == []
    assert not any(evidence.calls.values())
    assert web_research.audit_files([], report, evidence.workspace)["state"] == "not_applicable"


@pytest.mark.parametrize("task,mode,enabled", [
    ("计算本地 CSV 均值", "off", True),
    ("不要联网，计算本地 CSV 均值", "auto", True),
    ("No web search. Calculate local CSV means.", "auto", True),
    ("内部未公开保密资料，计算本地 CSV 均值", "auto", True),
    ("Confidential employee data; calculate local CSV means.", "auto", True),
    ("计算本地 CSV 均值", "auto", False),
])
def test_method_only_gap_does_not_override_offline_confidential_or_global_disabled_policy(
        evidence, monkeypatch, task, mode, enabled):
    def forbidden(*args, **kwargs):
        pytest.fail("method discovery must not override an explicit privacy/network policy")
    monkeypatch.setitem(sys.modules, "skillnet.skill_discovery", SimpleNamespace(discover=forbidden,
        capability_terms=forbidden))
    monkeypatch.setattr(web_research.web_search, "capabilities", lambda: {"enabled": enabled})
    report = web_research.collect(task, evidence.workspace, mode=mode, discover_missing=True)
    assert report["sources"] == [] and not any(evidence.calls.values())
    assert not (evidence.workspace / "artifacts").exists()
    assert not report.get("evidence_file")


def test_non_identity_discovery_routes_task_capabilities_instead_of_fixed_citation_terms(evidence, monkeypatch):
    task = "调研软件测试方法并分析数据"
    calls = []
    def discover(query, **kwargs):
        calls.append(query)
        return {"state": "candidates_only", "candidates": [], "attempts": []}
    monkeypatch.setitem(sys.modules, "skillnet.skill_discovery", SimpleNamespace(discover=discover,
        capability_terms=lambda input_task: "software testing data analysis" if input_task == task
            else pytest.fail("missing original capability request")))
    report = web_research.collect(task, evidence.workspace, discover_missing=True)
    assert calls == ["software testing data analysis"]
    assert report["needed"] is True and report["sources"]


def test_non_web_task_does_not_create_artifacts_or_apply_web_audit(evidence):
    report = web_research.collect("计算本地 CSV 均值", evidence.workspace)
    assert report["state"] == "not_needed" and not any(evidence.calls.values())
    assert web_research.audit_files([], report, evidence.workspace)["state"] == "not_applicable"
    plan = {"steps": [{"id": "s1", "input_files": ["data.csv"]}]}
    assert web_research.bind_plan(plan, report) == plan


@pytest.mark.parametrize("task", [
    "Research discontinued cancer medicines",
    "Research continued fractions and Ramanujan",
    "Explain previous-generation semiconductor lithography",
])
def test_new_research_topics_do_not_inherit_history_from_word_substrings(task):
    assert web_research.uses_history(task) is False


@pytest.mark.parametrize("task", [
    "Continue",
    "Continue the analysis",
    "Continue the task",
    "Use the previous results",
    "Analyze the previous data and file",
    "Review the previous turn and analysis",
    "Follow-up on previous results",
])
def test_explicit_english_conversation_references_can_reuse_history(task):
    assert web_research.uses_history(task) is True


def test_quote_only_audit_never_claims_person_identity_was_cross_supported(evidence):
    report = evidence.collect()
    path = csv_file(evidence.workspace, [{"source_id": "web-01", "evidence_url": URL_A,
        "claim": "A public source mentions a name", "quote": BODY_A[:25]}])
    report["citation_audit"] = web_research.audit_files([path], report, evidence.workspace)
    reply = web_research.grounded_reply(report)
    assert reply is not None
    assert "台账在已测字段上得到交叉支持" not in reply
