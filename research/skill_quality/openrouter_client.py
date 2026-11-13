"""Separate structured client with durable per-attempt reservations and no implicit spend."""

from __future__ import annotations

import math
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, BinaryIO, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .manifest import canonical, digest, read_jsonl, redact

T = TypeVar("T", bound=BaseModel)


class ClientFailure(RuntimeError):
    """Only stable, non-sensitive failure codes leave this boundary."""


def amount(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Invalid USD amount")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid USD amount") from None
    if not result.is_finite() or result < 0:
        raise ValueError("Invalid USD amount")
    return result


class CostLedger:
    """Single-writer event journal. Pending/unknown bills block new requests."""

    def __init__(self, limit_usd: str, path: Path | None = None):
        self.limit = amount(limit_usd)
        self.path = path
        self._lock = threading.RLock()
        self._file_lock: BinaryIO | None = None
        self._closed = False
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            lock = path.with_suffix(path.suffix + ".lock").open("a+b")
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
            except OSError:
                lock.close()
                raise ClientFailure("ledger_already_in_use") from None
            self._file_lock = lock
        self.events = read_jsonl(path) if path is not None and path.exists() else []

    def close(self) -> None:
        with self._lock:
            self._closed = True
            if self._file_lock is not None:
                self._file_lock.close()  # The OS releases the lock, including after a crash.
                self._file_lock = None

    def _write(self, event: dict[str, Any]) -> None:
        if self._closed:
            raise ClientFailure("ledger_closed")
        safe = redact(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("ab") as stream:
                stream.write(canonical(safe) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
        self.events.append(safe)

    @property
    def spent(self) -> Decimal:
        return sum(
            (
                amount(e["billed_cost_usd"])
                for e in self.events
                if e["event"] == "settled" and e["billed_cost_usd"] is not None
            ),
            Decimal("0"),
        )

    def reserve(self, attempt_id: str, upper_usd: str, metadata: dict[str, Any]) -> None:
        with self._lock:
            self._reserve(attempt_id, upper_usd, metadata)

    def _reserve(self, attempt_id: str, upper_usd: str, metadata: dict[str, Any]) -> None:
        if set(metadata) & {"event", "attempt_id", "reserved_upper_usd", "billed_cost_usd", "cost_status"}:
            raise ClientFailure("reserved_metadata_key")
        reserved = {e["attempt_id"] for e in self.events if e["event"] == "reserved"}
        settled = {
            e["attempt_id"]
            for e in self.events
            if e["event"] == "settled" and e["billed_cost_usd"] is not None
        }
        if reserved - settled:
            raise ClientFailure("unknown_or_pending_billing")
        if attempt_id in reserved:
            raise ClientFailure("duplicate_attempt_id")
        upper = amount(upper_usd)
        if upper <= 0 or self.spent + upper > self.limit:
            raise ClientFailure("budget_insufficient")
        self._write(
            {"event": "reserved", "attempt_id": attempt_id, "reserved_upper_usd": str(upper), **metadata}
        )

    def settle(self, attempt_id: str, cost: Any, metadata: dict[str, Any]) -> None:
        with self._lock:
            self._settle(attempt_id, cost, metadata)

    def _settle(self, attempt_id: str, cost: Any, metadata: dict[str, Any]) -> None:
        if set(metadata) & {"event", "attempt_id", "reserved_upper_usd", "billed_cost_usd", "cost_status"}:
            raise ClientFailure("reserved_metadata_key")
        if not any(e["event"] == "reserved" and e["attempt_id"] == attempt_id for e in self.events):
            raise ClientFailure("unreserved_attempt")
        if any(e["event"] == "settled" and e["attempt_id"] == attempt_id for e in self.events):
            raise ClientFailure("duplicate_settlement")
        known = str(amount(cost)) if cost is not None else None
        self._write(
            {
                "event": "settled",
                "attempt_id": attempt_id,
                "billed_cost_usd": known,
                "cost_status": "billed" if known is not None else "unverified",
                **metadata,
            }
        )


@dataclass(frozen=True)
class PaidApproval:
    approval_id: str
    rotated_key_confirmed: bool
    approved_budget_usd: str
    model: str
    provider: str
    pricing_snapshot_sha256: str


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()

    def close(value: Any) -> None:
        if isinstance(value, dict):
            value.pop("default", None)
            if value.get("type") == "object":
                value["additionalProperties"] = False
                value["required"] = list(value.get("properties", {}))
            for item in list(value.values()):
                close(item)
        elif isinstance(value, list):
            for item in value:
                close(item)

    close(schema)
    return schema


class OpenRouterClient:
    def __init__(
        self,
        *,
        ledger: CostLedger,
        model: str,
        provider: str,
        transport: httpx.MockTransport | None = None,
        approval: PaidApproval | None = None,
        max_retries: int = 1,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not model or not provider or not 0 <= max_retries <= 3:
            raise ClientFailure("configuration_missing")
        self.mock = isinstance(transport, httpx.MockTransport)
        if not self.mock:
            if (
                approval is None
                or not approval.approval_id
                or not approval.rotated_key_confirmed
                or approval.model != model
                or approval.provider != provider
                or amount(approval.approved_budget_usd) <= 0
                or ledger.limit > amount(approval.approved_budget_usd)
                or ledger.path is None
                or len(approval.pricing_snapshot_sha256) != 64
            ):
                raise ClientFailure("paid_call_not_approved")
            key = os.environ.get("OPENROUTER_API_KEY", "")
            if not key:
                raise ClientFailure("key_not_configured")
        else:
            key = "mock-credential-never-a-live-key"
        self.ledger, self.model, self.provider = ledger, model, provider
        self.max_retries, self.sleep = max_retries, sleep
        self.http = httpx.Client(
            base_url="https://openrouter.ai/api/v1/",
            transport=transport,
            headers={"Authorization": "Bearer " + key},
            follow_redirects=False,
            timeout=httpx.Timeout(60.0, connect=10.0),
            trust_env=False,
        )

    def close(self) -> None:
        self.http.close()
        self.ledger.close()

    def complete(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        *,
        run_id: str,
        upper_cost_usd: str,
        role: str = "quality_judge",
        max_tokens: int = 2048,
    ) -> T:
        if not run_id or isinstance(max_tokens, bool) or not 1 <= max_tokens <= 8192:
            raise ClientFailure("configuration_missing")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": False,
            "provider": {"only": [self.provider], "allow_fallbacks": False, "require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": strict_schema(response_model),
                },
            },
        }
        meta = {
            "run_id": run_id,
            "role": role,
            "requested_model": self.model,
            "requested_provider": self.provider,
            "request_sha256": digest(payload),
            "prompt_sha256": digest(messages),
            "mock": self.mock,
        }
        for retry in range(self.max_retries + 1):
            attempt_id = f"{run_id}:{retry}"
            self.ledger.reserve(attempt_id, upper_cost_usd, meta)
            started = time.monotonic()
            status, data, failure = None, {}, None
            try:
                response = self.http.post("chat/completions", json=payload)
                status = response.status_code
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("response_not_object")
            except httpx.TimeoutException:
                failure = "timeout"
            except httpx.TransportError:
                failure = "transport_failure"
            except (ValueError, TypeError):
                failure = "invalid_response_json"
            if not isinstance(data, dict):
                data = {}
            raw_usage = data.get("usage")
            usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
            raw_cost = usage.get("cost")
            try:
                cost = amount(raw_cost) if raw_cost is not None else None
            except ValueError:
                cost, failure = None, "invalid_billing"
            row = {
                "http_status": status,
                "retry_count": retry,
                "latency_ms": round((time.monotonic() - started) * 1000, 3),
                "response_model": data.get("model"),
                "provider_name": data.get("provider"),
                "generation_id": data.get("id"),
                "system_fingerprint": data.get("system_fingerprint"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
                if isinstance(usage.get("prompt_tokens_details"), dict)
                else None,
                "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
                if isinstance(usage.get("completion_tokens_details"), dict)
                else None,
                "response_sha256": digest(data),
                "schema_valid": False,
                "failure_kind": failure,
            }
            parsed = None
            if failure is None and status == 200:
                try:
                    choice = data["choices"][0]
                    if choice["finish_reason"] != "stop":
                        raise ClientFailure("incomplete_or_filtered_output")
                    if choice["message"].get("refusal"):
                        raise ClientFailure("model_refusal")
                    if not isinstance(data.get("model"), str) or not data["model"]:
                        raise ClientFailure("response_model_missing")
                    parsed = response_model.model_validate_json(choice["message"]["content"])
                    row["schema_valid"] = True
                except ClientFailure as exc:
                    failure = str(exc)
                except (ValueError, TypeError, KeyError, IndexError, ValidationError):
                    failure = "schema_invalid"
            elif failure is None:
                failure = "http_" + str(status)
            row["failure_kind"] = failure
            self.ledger.settle(attempt_id, cost, row)
            if cost is None:
                raise ClientFailure("unknown_billing")
            if cost > amount(upper_cost_usd) or self.ledger.spent > self.ledger.limit:
                raise ClientFailure("actual_cost_exceeds_reservation")
            if parsed is not None:
                return parsed
            if status in (429, 500, 502, 503, 504) and retry < self.max_retries:
                try:
                    wait = float(response.headers.get("Retry-After", str(2**retry)))
                except ValueError:
                    wait = float(2**retry)
                self.sleep(min(30.0, max(0.0, wait)) if math.isfinite(wait) else 30.0)
                continue
            raise ClientFailure(failure or "invalid_response")
        raise ClientFailure("retries_exhausted")
