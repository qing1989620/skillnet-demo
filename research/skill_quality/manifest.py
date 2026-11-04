"""Canonical hashes, write-once artifacts, bounded safe reads and redaction."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

SECRET = re.compile(r"sk-(?:or-v1-)?[A-Za-z0-9_-]{16,}|Bearer\s+[^\s\"']+", re.I)
SENSITIVE_KEYS = {"authorization", "api_key", "openrouter_api_key", "deepseek_api_key"}


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return SECRET.sub("[REDACTED]", value) if isinstance(value, str) else value


def write_once(path: Path, value: Any, *, jsonl: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(canonical(row) + b"\n" for row in value) if jsonl else canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def safe_read(root: Path, relative: str, *, max_bytes: int = 2_000_000) -> bytes:
    parts = PurePosixPath(relative)
    if not relative or parts.is_absolute() or "\\" in relative or ":" in relative:
        raise ValueError("Invalid source path")
    if any(part in ("", ".", "..") for part in relative.split("/")):
        raise ValueError("Source path escapes approved root")
    root = root.resolve()
    target = root
    for part in parts.parts:
        target = target / part
        if target.is_symlink() or getattr(target, "is_junction", lambda: False)():
            raise ValueError("Linked sources are not permitted")
    if not target.resolve().is_relative_to(root) or not target.is_file():
        raise ValueError("Source is not an approved file")
    if target.stat().st_size > max_bytes:
        raise ValueError("Source exceeds byte limit")
    with target.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Source grew beyond byte limit")
    return data


def freeze_files(root: Path, paths: Iterable[Path]) -> dict[str, Any]:
    rows = [
        {"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": file_sha(p)}
        for p in sorted(paths)
        if p.is_file()
    ]
    return {"files": rows, "manifest_sha256": digest(rows)}


def verify_files(root: Path, manifest: dict[str, Any]) -> None:
    if digest(manifest["files"]) != manifest["manifest_sha256"]:
        raise ValueError("Manifest digest mismatch")
    seen: set[str] = set()
    for row in manifest["files"]:
        if row["path"] in seen:
            raise ValueError("Duplicate manifest path")
        seen.add(row["path"])
        data = safe_read(root, row["path"], max_bytes=max(2_000_000, row["bytes"]))
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("Artifact SHA mismatch: " + row["path"])
