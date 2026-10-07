"""S1/backend integration over the existing SkillNet HTTP contract.

This client talks to SkillNet, not to an undocumented S1 production API.
Discovery stays local to SkillNet's indexes; execution is an explicit operation.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import quote, urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "1.0"
_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_RUN_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


class IntegrationError(RuntimeError):
    """Stable error category without upstream bodies, credentials, or task text."""

    def __init__(self, code: str, message: str, *, status_code: int | None = None,
                 request_id: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.request_id = request_id


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class SearchInput(_Input):
    query: str = Field(min_length=1, max_length=4000)
    k: int = Field(default=5, ge=1, le=20)
    mode: Literal["bm25", "hybrid", "fabric"] = "hybrid"


class LoadInput(_Input):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")


class RunInput(_Input):
    task: str = Field(min_length=1, max_length=6000)
    k: int = Field(default=5, ge=1, le=15)
    max_steps: int = Field(default=3, ge=1, le=8)
    max_cost_yuan: float = Field(default=1.0, gt=0, le=20)
    max_seconds: int = Field(default=300, ge=30, le=1800)
    max_llm_calls: int = Field(default=40, ge=5, le=200)


@dataclass(frozen=True)
class ClientConfig:
    base_url: str = "http://127.0.0.1:8848"
    token: str = field(default="", repr=False)
    timeout_seconds: float = 45.0
    allow_insecure_http: bool = False

    def __post_init__(self) -> None:
        try:
            url = urlsplit(self.base_url)
            _ = url.port
        except ValueError:
            raise ValueError("SkillNet base URL is invalid") from None
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username
                or url.password or url.query or url.fragment):
            raise ValueError("SkillNet base URL must be an HTTP(S) URL without credentials or query")
        if url.scheme == "http" and url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            if not self.allow_insecure_http:
                raise ValueError("Remote HTTP requires allow_insecure_http=True on a trusted network")
        if not 0 < self.timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be between 0 and 600")
        if "\r" in self.token or "\n" in self.token:
            raise ValueError("SkillNet token contains invalid header characters")


def integration_manifest() -> dict[str, Any]:
    """Publish supported contracts without claiming access to the target system."""
    return {
        "contract_version": CONTRACT_VERSION,
        "target": "立理 S1",
        "target_url": "https://s1.liliai.cn/",
        "status": "contract_ready",
        "production_connection_verified": False,
        "direction": "S1 backend → SkillNet service",
        "client": "skillnet.integration.SkillNetClient",
        "documentation": "docs/s1-integration.md",
        "authentication": {"header": "X-SkillNet-Token", "scope": "service-to-service"},
        "operations": {
            "health": {"method": "GET", "path": "/api/health"},
            "search": {"method": "POST", "path": "/api/search", "default_mode": "hybrid"},
            "load_skill": {"method": "GET", "path": "/api/skill/{name}"},
            "create_run": {"method": "POST", "path": "/api/runs", "requires_model": True},
            "get_run": {"method": "GET", "path": "/api/runs/{run_id}"},
            "events": {"method": "GET", "path": "/api/runs/{run_id}/stream", "format": "SSE"},
            "cancel_run": {"method": "POST", "path": "/api/runs/{run_id}/cancel"},
            "artifact": {"method": "GET", "path": "/api/runs/{run_id}/artifacts/{name}"},
        },
        "tools": ["search_skills", "load_skill"],
        "deployment": {
            "runtime": "single_process",
            "tenant_authorization": "enforced by S1 backend before forwarding",
            "execution_isolation": "dedicated worker/container required for untrusted execution",
        },
    }


def skill_tools() -> list[dict[str, Any]]:
    """Function declarations paired with SkillNetClient.call_tool handlers."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_skills",
                "description": "检索科研技能摘要。先检索候选，再按名称加载完整技能。检索不调用大模型。",
                "strict": True,
                "parameters": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "query": {"type": "string", "minLength": 1, "maxLength": 4000},
                        "k": {"type": "integer", "minimum": 1, "maximum": 20},
                    },
                    "required": ["query", "k"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "按检索结果中的名称加载完整 SKILL.md，包含执行步骤、陷阱和验收条件。",
                "strict": True,
                "parameters": {
                    "type": "object", "additionalProperties": False,
                    "properties": {"name": {"type": "string", "maxLength": 64,
                                              "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"}},
                    "required": ["name"],
                },
            },
        },
    ]


class SkillNetClient:
    """Reusable, bounded HTTP client; mutations are never automatically retried.

    Use one client per backend process and close it during application shutdown.
    ``transport`` permits offline contract tests with httpx.MockTransport.
    """

    def __init__(self, config: ClientConfig | None = None, *,
                 transport: httpx.BaseTransport | None = None) -> None:
        self.config = config or ClientConfig()
        headers = {"Accept": "application/json", "User-Agent": "SkillNet-Integration/1.0"}
        if self.config.token:
            headers["X-SkillNet-Token"] = self.config.token
        self._http = httpx.Client(
            base_url=self.config.base_url.rstrip("/") + "/",
            headers=headers, timeout=httpx.Timeout(self.config.timeout_seconds, connect=5.0),
            transport=transport, follow_redirects=False, trust_env=False,
        )

    def __enter__(self) -> SkillNetClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    @staticmethod
    def _check_status(response: httpx.Response) -> None:
        if 200 <= response.status_code < 300:
            return
        code = {
            401: "unauthorized", 403: "forbidden", 404: "not_found",
            409: "conflict", 422: "invalid_request", 429: "rate_limited", 503: "unavailable",
        }.get(response.status_code, "http_error")
        # Upstream error bodies can contain prompts, paths, or credentials.
        raise IntegrationError(code, f"SkillNet request failed (HTTP {response.status_code})",
                               status_code=response.status_code,
                               request_id=response.headers.get("X-Request-ID", "")[:128])

    @staticmethod
    def _read_bounded(response: httpx.Response, max_bytes: int) -> bytes:
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > max_bytes:
                raise IntegrationError("response_too_large", "SkillNet response exceeds the size limit")
            chunks.append(chunk)
        return b"".join(chunks)

    def _json(self, method: str, path: str, *, payload: dict[str, Any] | None = None,
              headers: dict[str, str] | None = None) -> dict[str, Any]:
        try:
            with self._http.stream(method, path, json=payload, headers=headers) as response:
                self._check_status(response)
                body = self._read_bounded(response, 8 * 1024 * 1024)
                try:
                    data = json.loads(body)
                except (ValueError, UnicodeError):
                    raise IntegrationError("invalid_response", "SkillNet returned invalid JSON") from None
                if not isinstance(data, dict):
                    raise IntegrationError("invalid_response", "SkillNet returned a non-object response")
                return data
        except httpx.TimeoutException:
            raise IntegrationError("timeout", "SkillNet request timed out; mutation outcome may be unknown") from None
        except httpx.HTTPError:
            raise IntegrationError("transport_error", "SkillNet connection failed") from None

    def health(self) -> dict[str, Any]:
        data = self._json("GET", "api/health")
        if not isinstance(data.get("ok"), bool):
            raise IntegrationError("invalid_response", "SkillNet health contract is invalid")
        return data

    def search(self, query: str, *, k: int = 5, mode: str = "hybrid") -> dict[str, Any]:
        request = SearchInput(query=query, k=k, mode=mode)
        data = self._json("POST", "api/search", payload={
            "query": request.query, "k": request.k, "modes": [request.mode],
        })
        result = data.get("by_mode", {}).get(request.mode) if isinstance(data.get("by_mode"), dict) else None
        if not isinstance(result, dict) or not isinstance(result.get("selected"), list):
            raise IntegrationError("invalid_response", "SkillNet search contract is invalid")
        if any(not isinstance(name, str) or len(name) > 64 or not _SKILL_NAME.fullmatch(name) for name in result["selected"]):
            raise IntegrationError("invalid_response", "SkillNet returned invalid skill identifiers")
        if len(result["selected"]) > request.k or len(set(result["selected"])) != len(result["selected"]):
            raise IntegrationError("invalid_response", "SkillNet returned an invalid selection count")
        return result

    def load_skill(self, name: str) -> dict[str, Any]:
        request = LoadInput(name=name)
        data = self._json("GET", f"api/skill/{request.name}")
        skill = data.get("skill")
        if not isinstance(skill, dict) or skill.get("name") != request.name or not isinstance(data.get("markdown"), str):
            raise IntegrationError("invalid_response", "SkillNet skill contract is invalid")
        return data

    def call_tool(self, name: str, arguments: Mapping[str, Any] | str) -> dict[str, Any]:
        """Dispatch the two declared discovery tools with validated inputs.

        Discovery intentionally has no execution/evolution operation. Return values
        can be JSON-encoded into the host agent's function/tool response.
        """
        if name not in {"search_skills", "load_skill"}:
            raise ValueError("Unsupported SkillNet tool")
        if isinstance(arguments, str):
            if len(arguments) > 16000:
                raise ValueError("Tool arguments exceed the size limit")
            try:
                arguments = json.loads(arguments)
            except ValueError:
                raise ValueError("Tool arguments must be valid JSON") from None
        if not isinstance(arguments, Mapping):
            raise ValueError("Tool arguments must be an object")
        if name == "load_skill":
            request = LoadInput.model_validate(dict(arguments))
            return self.load_skill(request.name)
        # The agent cannot switch this cheap discovery tool to paid Fabric reranking.
        if set(arguments) - {"query", "k"}:
            raise ValueError("Unsupported search tool arguments")
        request = SearchInput.model_validate(dict(arguments))
        result = self.search(request.query, k=request.k)
        details = result.get("detail", [])
        if not isinstance(details, list):
            raise IntegrationError("invalid_response", "SkillNet search summaries are invalid")
        selected = set(result["selected"])
        cards = [
            {key: card[key] for key in ("name", "domain", "capability", "score", "channels") if key in card}
            for card in details if isinstance(card, dict) and isinstance(card.get("name"), str) and card["name"] in selected
        ]
        return {
            "query": request.query, "selected": result["selected"], "skills": cards,
            "decision": result.get("decision", "confirm"),
            "confidence": result.get("confidence", 0),
            "confidence_kind": "heuristic_relevance_not_probability",
            "degraded": result.get("degraded", False),
            "next_action": "load_skill for each selected skill before executing",
        }

    @staticmethod
    def _run_path(run_id: str) -> str:
        if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
            raise ValueError("Invalid run identifier")
        return f"api/runs/{run_id}"

    def create_run(self, task: str, **budgets: Any) -> dict[str, Any]:
        request = RunInput(task=task, **budgets)
        data = self._json("POST", "api/runs", payload=request.model_dump())
        try:
            self._run_path(data.get("run_id", ""))
        except ValueError:
            raise IntegrationError("invalid_response", "SkillNet returned an invalid run identifier") from None
        return data

    def get_run(self, run_id: str) -> dict[str, Any]:
        data = self._json("GET", self._run_path(run_id))
        if data.get("run_id") != run_id or not isinstance(data.get("status"), str):
            raise IntegrationError("invalid_response", "SkillNet run contract is invalid")
        return data

    def cancel_run(self, run_id: str) -> dict[str, Any]:
        return self._json("POST", self._run_path(run_id) + "/cancel")

    def iter_run_events(self, run_id: str, *, last_event_id: str | None = None) -> Iterator[dict[str, Any]]:
        headers = {"Accept": "text/event-stream"}
        if last_event_id is not None:
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", last_event_id):
                raise ValueError("Invalid event identifier")
            headers["Last-Event-ID"] = last_event_id
        try:
            with self._http.stream("GET", self._run_path(run_id) + "/stream", headers=headers) as response:
                self._check_status(response)
                if "text/event-stream" not in response.headers.get("content-type", ""):
                    raise IntegrationError("invalid_response", "SkillNet event stream has invalid content type")
                data_lines: list[str] = []
                event, event_id, size = "message", "", 0
                for line in response.iter_lines():
                    size += len(line)
                    if size > 262144:
                        raise IntegrationError("response_too_large", "SkillNet event exceeds the size limit")
                    if not line:
                        if data_lines:
                            try:
                                data = json.loads("\n".join(data_lines))
                            except ValueError:
                                raise IntegrationError("invalid_response", "SkillNet event contains invalid JSON") from None
                            if not isinstance(data, dict):
                                raise IntegrationError("invalid_response", "SkillNet event data must be an object")
                            yield {"event": event, "id": event_id, "data": data}
                            if event == "end":
                                return
                        data_lines, event, event_id, size = [], "message", "", 0
                    elif not line.startswith(":"):
                        key, _, value = line.partition(":")
                        value = value.removeprefix(" ")
                        if key == "data":
                            data_lines.append(value)
                        elif key == "event":
                            event = value
                        elif key == "id":
                            event_id = value
        except httpx.TimeoutException:
            raise IntegrationError("timeout", "SkillNet event stream timed out; query run state before reconnecting") from None
        except httpx.HTTPError:
            raise IntegrationError("transport_error", "SkillNet event stream connection failed") from None

    def download_artifact(self, run_id: str, name: str, *, expected_sha256: str | None = None,
                          max_bytes: int = 32 * 1024 * 1024) -> bytes:
        if not isinstance(name, str) or not name or len(name) > 255 or name in {".", ".."} or any(c in name for c in "/\\\x00\r\n"):
            raise ValueError("Artifact name must be a filename without path components")
        if not 0 < max_bytes <= 128 * 1024 * 1024:
            raise ValueError("Artifact size limit must be between 1 byte and 128 MiB")
        if expected_sha256 is not None and not re.fullmatch(r"[A-Fa-f0-9]{64}", expected_sha256):
            raise ValueError("Invalid expected artifact digest")
        path = self._run_path(run_id) + "/artifacts/" + quote(name, safe="")
        try:
            with self._http.stream("GET", path) as response:
                self._check_status(response)
                content = self._read_bounded(response, max_bytes)
        except httpx.TimeoutException:
            raise IntegrationError("timeout", "SkillNet artifact download timed out") from None
        except httpx.HTTPError:
            raise IntegrationError("transport_error", "SkillNet artifact download failed") from None
        if expected_sha256 and hashlib.sha256(content).hexdigest() != expected_sha256.lower():
            raise IntegrationError("digest_mismatch", "SkillNet artifact digest does not match its manifest")
        return content
