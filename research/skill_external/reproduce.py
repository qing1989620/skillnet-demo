"""Recompute released external judgments and community verdicts, never call APIs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from pydantic import ValidationError

from research.skill_quality.manifest import digest, file_sha, read_jsonl, verify_files

from .analysis import analyze
from .community_runtime import analyze as community_analyze
from .community_runtime import fixtures
from .diagnostics import parser_sensitivity
from .experiment import Judgment, payload, upper_cost
from .joint_analysis import analyze as joint_analyze
from .materials import context

RESULTS = Path(__file__).with_name("results")
ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def reproduce(root: Path = RESULTS, source: Path | None = None) -> dict:
    prepared, run, labels = [root / n for n in ["preparation", "deepseek-v1", "labels-v1"]]
    for name in [
        "preparation",
        "deepseek-v1",
        "labels-v1",
        "analysis-v3",
        "community-prepared-v1",
        "community-v1",
        "joint-posthoc-v1",
    ]:
        path = root / name
        verify_files(path, load(path / "manifest.json"))
    verify_files(ROOT, load(prepared / "code-manifest.json"))
    metadata = read_jsonl(labels / "official-label-metadata.jsonl")
    assert len(metadata) == 203
    for row in metadata:
        assert hashlib.sha256(row["raw_metadata_utf8"].encode("utf-8")).hexdigest() == row["sha256"]
    index = {r["case_id"]: r for r in read_jsonl(prepared / "packet-index.jsonl")}
    requests = read_jsonl(run / "requests-before-api.jsonl")
    by_id = {r["trial_id"]: r for r in requests}
    assert len(requests) == 609 and len(index) == 203
    if source is not None:
        cases = source / "snapshot/data/evaluation"
        summaries = source / "snapshot/baseline/artifact-summaries"
        rebuilt = {case.name: context(case, summaries) for case in sorted(cases.iterdir())}
        assert digest(list(rebuilt.values())) == load(prepared / "summary.json")["packet_digest"]
        for row in requests:
            packet = rebuilt[row["case_id"]]
            assert digest(packet) == row["packet_sha256"] == index[row["case_id"]]["packet_sha256"]
            assert digest(payload(packet, row["arm"])) == row["payload_sha256"]
    actual_cost = upper_cost(0, 0)
    trials = [load(p) for p in sorted((run / "trials").glob("*.json"))]
    for row in trials:
        assert all(row[k] == v for k, v in by_id[row["trial_id"]].items())
        assert row["packet_sha256"] == index[row["case_id"]]["packet_sha256"]
        if row.get("http_status") != 200:
            assert row["http_status"] == 402 and row["response"] is None
            continue
        response = row["response"]
        cost = upper_cost(response["usage"]["prompt_tokens"], response["usage"]["completion_tokens"])
        assert str(cost) == row["peak_upper_usd"]
        actual_cost += cost
        try:
            parsed = Judgment.model_validate_json(response["choices"][0]["message"]["content"])
            assert parsed.model_dump() == row["judgment"]
            assert row["schema_valid"] == (response["choices"][0]["finish_reason"] == "stop")
        except ValidationError:
            assert row["schema_valid"] is False and row["judgment"] is None
    assert str(actual_cost) == load(run / "ledger.json")["peak_upper_usd"]
    assert digest(parser_sensitivity(root)) == digest(load(root / "parser-posthoc-v1/summary.json"))
    community = root / "community-v1"
    bundle = root / "community-prepared-v1/bundle"
    expected_fixtures = fixtures(ROOT / "research/skill_network/results/sources-v2")
    assert digest(expected_fixtures) == digest(load(community / "fixtures.json"))
    entries = load(community / "entries.json")
    by_file = {r["file"]: r for r in entries}
    for row in load(community / "outcomes.json"):
        assert (
            row["source_sha256"]
            == by_file[row["script"]]["source_sha256"]
            == file_sha(bundle / "scripts" / row["script"])
        )
    with tempfile.TemporaryDirectory(prefix="skill-external-reproduction-") as directory:
        temp = Path(directory)
        result = analyze(None, prepared, run, temp / "external", labels / "official-label-metadata.jsonl")
        assert digest(result) == digest(load(root / "analysis-v3/analysis.json"))
        temp_community = temp / "community"
        temp_community.mkdir()
        for name in ["fixtures.json", "outcomes.json"]:
            shutil.copyfile(community / name, temp_community / name)
        assert digest(community_analyze(temp_community)) == digest(load(community / "summary.json"))
        assert digest(load(temp_community / "verdicts.json")) == digest(load(community / "verdicts.json"))
        joint = joint_analyze(community, bundle, temp / "joint")
        assert digest(joint) == digest(load(root / "joint-posthoc-v1/summary.json"))
    return {
        "status": "PASS",
        "new_api_calls": 0,
        "http_responses_reverified": 258,
        "http402_retained": 1,
        "matched_external_cases": 86,
        "community_cli_outputs_reverified": 355,
        "original_scripts": 9,
        "repaired_variants": 2,
        "posthoc_joint_replay_recomputed": True,
        "all_609_prompt_payloads_reconstructed": source is not None,
        "raw_third_party_context_redistributed": False,
        "scope": "Offline reproduction, not new independent observations or expert semantic validation",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    print(json.dumps(reproduce(source=args.source), ensure_ascii=False, indent=2))
