"""Direct DeepSeek readiness study, with bounded spend and independent citation checks."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from research.skill_quality.manifest import digest, file_sha, freeze_files, read_jsonl, write_once
from research.skill_quality.openrouter_client import amount
from research.skill_quality.schemas import DIMENSIONS

MODEL = "deepseek-flash"
EXTRA = (
    "\nReturn exactly the eight dimensions once each. Use a short reason of at most 20 words "
    "and at most one citation per dimension; prefer a single complete source line. "
    "An exact_quote must equal all cited original lines joined by a newline, without line numbers. "
    'JSON shape example only, not an assessment: {"dimensions":[{"dimension":"contract_consistency",'
    '"score":null,"state":"unknown","reason":"Example only","citations":[]}]}. '
    "Produce all eight dimensions, no additional top-level keys."
)
CREDENTIAL = re.compile(r"(?<![A-Za-z0-9_-])sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}")


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    exact_quote: str
    relation: Literal["support", "counterevidence"]


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    dimension: str
    score: int | None = Field(ge=0, le=4)
    state: Literal["static_supported", "conflict", "declared", "unknown", "not_applicable"]
    reason: str
    citations: list[Citation]

    @model_validator(mode="after")
    def unknown_is_missing(self) -> Dimension:
        if self.dimension not in DIMENSIONS:
            raise ValueError("Unexpected dimension")
        if (self.state in {"unknown", "not_applicable"}) != (self.score is None):
            raise ValueError("Missingness and score conflict")
        return self


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    dimensions: list[Dimension]

    @model_validator(mode="after")
    def complete_dimensions(self) -> Assessment:
        if len(self.dimensions) != 8 or {r.dimension for r in self.dimensions} != set(DIMENSIONS):
            raise ValueError("Exactly eight distinct dimensions required")
        return self


def citation_checks(result: Assessment, material: dict) -> list[dict]:
    documents = {d["path"]: d for d in material["included_documents"]}
    output = []
    for dimension in result.dimensions:
        for citation in dimension.citations:
            document = documents.get(citation.path)
            reason = None
            if document is None:
                reason = "path_not_supplied"
            elif not citation.exact_quote.strip():
                reason = "empty_quote"
            elif citation.sha256 != document["sha256"]:
                reason = "sha256_mismatch"
            else:
                lines = {r["line"]: r["text"] for r in document["numbered_lines"]}
                if (
                    citation.end_line < citation.start_line
                    or citation.end_line - citation.start_line > len(lines)
                    or any(i not in lines for i in range(citation.start_line, citation.end_line + 1))
                ):
                    reason = "line_range_not_supplied"
                elif citation.exact_quote != "\n".join(
                    lines[i] for i in range(citation.start_line, citation.end_line + 1)
                ):
                    reason = "quote_not_exact"
            output.append(
                {
                    "dimension": dimension.dimension,
                    "relation": citation.relation,
                    "valid_locator": reason is None,
                    "invalid_reason": reason,
                }
            )
    return output


def usage_upper(usage: dict, pricing: dict) -> dict[str, str]:
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    if (
        type(prompt) is not int
        or type(completion) is not int
        or not 0 <= prompt <= 1048576
        or not 0 <= completion <= 2048
    ):
        raise ValueError("Missing or out-of-bound usage; stop rather than invent a bill")
    return {
        currency: str(
            (
                Decimal(prompt) * Decimal(rates["miss_peak"])
                + Decimal(completion) * Decimal(rates["output_peak"])
            )
            / Decimal(1_000_000)
        )
        for currency, rates in pricing["rates_per_million"].items()
    }


class Budget:
    """Durable conservative usage bounds, explicitly not provider invoices."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = path.with_suffix(".lock").open("a+b")
        if self.lock.tell() == 0:
            self.lock.write(b"0")
            self.lock.flush()
        self.lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            else:
                import fcntl

                fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
        except OSError:
            self.lock.close()
            raise RuntimeError("Budget ledger already in use") from None
        self.events = read_jsonl(path) if path.exists() else []

    def close(self) -> None:
        self.lock.close()

    def append(self, event: dict) -> None:
        with self.path.open("ab") as stream:
            stream.write(json.dumps(event, sort_keys=True).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.events.append(event)

    def reserve(self, identity: str) -> None:
        reserved = {e["id"] for e in self.events if e["event"] == "reserve"}
        settled = {e["id"] for e in self.events if e["event"] == "usage_bound"}
        if reserved - settled:
            raise RuntimeError("Unknown or pending charge; no automatic retry")
        if identity in reserved or len(reserved) >= 60:
            raise RuntimeError("Duplicate or attempt limit")
        for currency, cap, reservation in (("USD", "5", "0.35"), ("CNY", "20", "2.2")):
            spent = sum(
                (Decimal(e["upper"][currency]) for e in self.events if e["event"] == "usage_bound"),
                Decimal(0),
            )
            if spent + Decimal(reservation) > Decimal(cap):
                raise RuntimeError("Conservative budget exhausted")
        self.append({"event": "reserve", "id": identity, "upper": {"USD": "0.35", "CNY": "2.2"}})

    def settle(self, identity: str, upper: dict[str, str]) -> None:
        if set(upper) != {"USD", "CNY"}:
            raise ValueError("Both currency bounds required")
        for value in upper.values():
            amount(value)
        reservations = [e for e in self.events if e["event"] == "reserve" and e["id"] == identity]
        if len(reservations) != 1 or any(
            e["event"] == "usage_bound" and e["id"] == identity for e in self.events
        ):
            raise RuntimeError("Invalid settlement identity")
        if any(Decimal(upper[c]) > Decimal(reservations[0]["upper"][c]) for c in ("USD", "CNY")):
            raise RuntimeError("Usage exceeds reserved context bound")
        self.append({"event": "usage_bound", "id": identity, "upper": upper, "is_invoice": False})


class DirectClient:
    def __init__(self, key: str, transport: httpx.MockTransport | None = None):
        self.http = httpx.Client(
            base_url="https://api.deepseek.com",
            headers={"Authorization": "Bearer " + key},
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(120, connect=15),
        )

    def get(self, route: str) -> dict:
        response = self.http.get(route)
        if response.status_code != 200:
            raise RuntimeError("DeepSeek metadata HTTP " + str(response.status_code))
        return response.json()

    def post(self, messages: list[dict]) -> dict:
        response = self.http.post(
            "/chat/completions",
            json={
                "model": MODEL,
                "messages": messages,
                "thinking": {"type": "disabled"},
                "temperature": 0,
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
                "stream": False,
            },
        )
        if response.status_code != 200:
            raise RuntimeError("DeepSeek model HTTP " + str(response.status_code))
        return response.json()

    def close(self) -> None:
        self.http.close()


def key_from_file(path: Path) -> str:
    values = [
        line.split("=", 1)[1].strip().strip('"').strip("'")
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and line.split("=", 1)[0].strip() == "DEEPSEEK_API_KEY"
    ]
    if len(values) != 1 or not re.fullmatch(r"sk-[A-Za-z0-9_-]{20,}", values[0]):
        raise ValueError("Local credential missing or malformed")
    return values[0]


def direct_messages(row: dict, notices: str) -> list[dict]:
    messages = [dict(m) for m in row["messages"]]
    if any(CREDENTIAL.search(m["content"]) for m in messages):
        raise ValueError("Credential-like input requires review")
    messages[0]["content"] += EXTRA + "\nSource attribution notices:\n" + notices
    return messages


def run(output: Path, env_file: Path, *, transport: httpx.MockTransport | None = None) -> dict:
    if output.exists():
        raise FileExistsError("Use a fresh direct run ID")
    base = Path(__file__).parent
    approval_path = base / "results/deepseek-authorization.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if not approval["direct_deepseek_authorized"] or approval["cap_usd"] != 5:
        raise ValueError("This direct batch has not been authorized")
    price_path = base / "results/deepseek-pricing-snapshot.json"
    pricing = json.loads(price_path.read_text(encoding="utf-8"))
    source = Path("out/research/skill-study/20261106-judge-readiness-v2/requests.private.jsonl")
    plan_source = json.loads(source.with_name("plan.json").read_text(encoding="utf-8"))
    expected = {r["run_id"]: r["request_sha256"] for r in plan_source["requests"]}
    requests = read_jsonl(source)
    if len(requests) != 54 or any(digest(r) != expected[r["run_id"]] for r in requests):
        raise ValueError("Prepared requests changed")
    notices = "\n\n".join(
        Path(p).read_text(encoding="utf-8")
        for p in (
            "seed/community/licenses/claude/LICENSE",
            "seed/community/licenses/agentic/LICENSE",
            "seed/community/licenses/agentic/LICENSE-CONTENT",
        )
    )
    grouped = defaultdict(list)
    for row in requests:
        grouped[row["skill_uid"]].append(row)
    ordered = []
    for index, identity in enumerate(sorted(grouped)):
        group = grouped[identity]
        ordered.extend(group[index % 3 :] + group[: index % 3])
    prepared = [(row, direct_messages(row, notices)) for row in ordered]
    output.mkdir(parents=True)
    write_once(
        output / "adapted-requests.private.jsonl",
        [
            {
                "run_id": row["run_id"],
                "arm": row["arm"],
                "material_sha256": row["material_sha256"],
                "messages": messages,
            }
            for row, messages in prepared
        ],
        jsonl=True,
    )
    plan = {
        "model_alias": MODEL,
        "documented_version": pricing["documented_version"],
        "alias_is_not_an_immutable_weight_version": True,
        "source_requests_sha256": file_sha(source),
        "approval_sha256": file_sha(approval_path),
        "pricing_sha256": file_sha(price_path),
        "attempts_prepared": len(prepared),
        "order": "three-arm cyclic rotation across sorted parent IDs, balanced first-arm position",
        "temperature": 0,
        "thinking": "disabled",
        "max_output_tokens": 2048,
        "concurrency": 1,
        "budget_caps": {"USD": 5, "CNY": 20},
        "cost_accounting": "official peak-price upper bound from observed usage, not a provider invoice",
        "adaptation": "same extra JSON example, brevity/one-citation limits and license notices in every arm",
        "material_scope": "public bounded D1 excerpts only, full inventory; source notices retained",
        "license_scope": "permissive source notices reviewed for transmitted excerpts; not certification of full opaque packages",
        "skills_executed": 0,
    }
    write_once(output / "plan.json", plan)
    code = [Path(__file__), base / "prepare_judge_pilot.py", approval_path, price_path]
    write_once(output / "code-manifest.json", freeze_files(Path.cwd(), code))
    for code_path in code:
        snapshot_path = output / "code-snapshot" / code_path.relative_to(Path.cwd())
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(code_path.read_bytes())
    client = DirectClient("mock" if transport is not None else key_from_file(env_file), transport)
    budget = None
    rows, raw_models, error, invalid_streak = [], [], None, 0
    attempted, received = 0, 0
    started = time.monotonic()
    metadata_requests = 0
    try:
        models = client.get("/models")
        metadata_requests += 1
        write_once(output / "models.private.json", models)
        balance = client.get("/user/balance")
        metadata_requests += 1
        write_once(output / "balance-before.private.json", balance)
        if not any(m["id"] == MODEL for m in models["data"]):
            raise RuntimeError("Selected direct model unavailable")
        if not balance["is_available"]:
            error = "balance_unavailable_before_any_model_request"
        else:
            budget = Budget(Path("out/research/skill-study/deepseek-approved-pilot-ledger.jsonl"))
            for index, (row, messages) in enumerate(prepared):
                identity = row["run_id"] + "-direct-v1"
                budget.reserve(identity)
                call_started = time.monotonic()
                attempted += 1
                response = client.post(messages)
                received += 1
                write_once(output / f"response-{index:03}.private.json", response)
                upper = usage_upper(response.get("usage", {}), pricing)
                budget.settle(identity, upper)
                choice = response["choices"][0]
                content = choice["message"].get("content")
                parsed, checks, failure = None, [], None
                try:
                    if choice["finish_reason"] != "stop" or not isinstance(content, str):
                        raise ValueError("Incomplete response")
                    parsed = Assessment.model_validate_json(content)
                    checks = citation_checks(parsed, json.loads(row["messages"][1]["content"]))
                except (ValidationError, ValueError):
                    failure = "schema_or_completion_invalid"
                invalid_streak = invalid_streak + 1 if failure else 0
                observed_model = response.get("model")
                raw_models.append(observed_model)
                rows.append(
                    {
                        "run_id": identity,
                        "skill_uid": row["skill_uid"],
                        "arm": row["arm"],
                        "request_sha256": digest(messages),
                        "material_sha256": row["material_sha256"],
                        "response_id": response.get("id"),
                        "served_model": observed_model,
                        "system_fingerprint": response.get("system_fingerprint"),
                        "finish_reason": choice["finish_reason"],
                        "schema_valid": failure is None,
                        "failure": failure,
                        "assessment": parsed.model_dump() if parsed else None,
                        "citation_checks": checks,
                        "usage": response["usage"],
                        "tariff_upper": upper,
                        "is_invoice": False,
                        "wall_seconds": time.monotonic() - call_started,
                    }
                )
                with (output / "observations.jsonl").open("ab") as stream:
                    stream.write(json.dumps(rows[-1], ensure_ascii=False).encode("utf-8") + b"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                print(
                    json.dumps(
                        {
                            "completed": len(rows),
                            "prepared": len(prepared),
                            "schema_valid": failure is None,
                            "seconds": round(time.monotonic() - started, 1),
                        }
                    ),
                    flush=True,
                )
                if len(set(raw_models)) != 1:
                    raise RuntimeError("Served model changed within run")
                if invalid_streak >= 3:
                    raise RuntimeError("Three consecutive invalid responses; stop without automatic retry")
            after = client.get("/user/balance")
            metadata_requests += 1
            write_once(output / "balance-after.private.json", after)
    except Exception as exc:
        error = (
            type(exc).__name__ + ": " + str(exc)
            if isinstance(exc, (ValueError, RuntimeError))
            else type(exc).__name__
        )
    finally:
        client.close()
        if budget is not None:
            budget.close()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["arm"]].append(row)
    by_arm = {}
    for arm, items in groups.items():
        checks = [c for r in items for c in r["citation_checks"]]
        dimensions = [d for r in items if r["assessment"] for d in r["assessment"]["dimensions"]]
        by_arm[arm] = {
            "requests": len(items),
            "schema_valid": sum(r["schema_valid"] for r in items),
            "citations": len(checks),
            "valid_locators": sum(c["valid_locator"] for c in checks),
            "invalid_locator_reasons": dict(
                Counter(c["invalid_reason"] for c in checks if not c["valid_locator"])
            ),
            "dimension_states": dict(Counter(d["state"] for d in dimensions)),
        }
    summary = {
        "experiment": "direct_deepseek_matched_material_readiness_pilot",
        "date": "2026-11-07",
        "model_requests_completed": len(rows),
        "model_requests_attempted": attempted,
        "model_http200_responses": received,
        "metadata_requests_completed": metadata_requests,
        "complete": len(rows) == len(prepared),
        "error": error,
        "parents_observed": len({r["skill_uid"] for r in rows}),
        "human_gold": 0,
        "skills_executed": 0,
        "served_model_values": sorted({m for m in raw_models if isinstance(m, str)}),
        "missing_served_model_metadata": any(not isinstance(m, str) for m in raw_models),
        "by_arm": by_arm,
        "prompt_tokens": sum(r["usage"]["prompt_tokens"] for r in rows),
        "completion_tokens": sum(r["usage"]["completion_tokens"] for r in rows),
        "tariff_upper_from_observed_usage": {
            c: str(sum((Decimal(r["tariff_upper"][c]) for r in rows), Decimal(0))) for c in ("USD", "CNY")
        },
        "tariff_bounds_are_not_provider_invoices": True,
        "wall_seconds": time.monotonic() - started,
        "limitations": [
            "training examples, partial excerpts, one model, one response per arm; not independent human quality accuracy",
            "citation count is directly prompted; more citations alone is not evaluation-method superiority",
            "exact locator validity does not prove semantic entailment",
            "shared account balance delta can include unrelated use and is not attributed as a batch invoice",
            "model alias can change and is not an immutable weight snapshot",
        ],
    }
    write_once(output / "summary.json", summary)
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=Path("../skillnet-local-demo/.env"))
    args = parser.parse_args()
    result = run(args.output, args.env_file)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("complete", "model_requests_completed", "error", "tariff_upper_from_observed_usage")
            },
            ensure_ascii=False,
        )
    )
