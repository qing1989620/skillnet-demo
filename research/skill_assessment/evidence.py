"""Check source identity and coordinates, without claiming semantic entailment."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from research.skill_quality.manifest import digest, safe_read
from research.skill_quality.schemas import SkillSnapshot


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha256: str
    text: str


@dataclass(frozen=True)
class Citation:
    path: str
    sha256: str
    start_line: int
    end_line: int
    quote: str


@dataclass(frozen=True)
class Bundle:
    skill_uid: str
    name: str
    source_repo: str
    source_commit: str
    source_path: str
    files: dict[str, SourceFile]

    def cite(self, path: str, start: int, end: int | None = None) -> Citation:
        source = self.files[path]
        stop = start if end is None else end
        if type(start) is not int or type(stop) is not int:
            raise ValueError("Citation coordinates must be integers")
        if start < 1 or stop < start or stop > len(source.text.splitlines()):
            raise ValueError("Citation is outside the registered file")
        quote = "\n".join(source.text.splitlines()[start - 1 : stop])
        citation = Citation(path, source.sha256, start, stop, quote)
        self.verify(citation)
        return citation

    def locate(self, path: str, needle: str) -> Citation:
        matches = [i for i, line in enumerate(self.files[path].text.splitlines(), 1) if needle in line]
        if len(matches) != 1:
            raise ValueError(f"Expected one occurrence of {needle!r}, got {len(matches)}")
        return self.cite(path, matches[0])

    def verify(self, citation: Citation) -> None:
        source = self.files.get(citation.path)
        if source is None:
            raise ValueError("Citation file is not registered")
        if hashlib.sha256(source.text.encode("utf-8")).hexdigest() != source.sha256:
            raise ValueError("Source object has changed")
        if citation.sha256 != source.sha256:
            raise ValueError("Citation SHA mismatch")
        if type(citation.start_line) is not int or type(citation.end_line) is not int:
            raise ValueError("Citation coordinates must be integers")
        lines = source.text.splitlines()
        if not (1 <= citation.start_line <= citation.end_line <= len(lines)):
            raise ValueError("Invalid citation coordinates")
        actual = "\n".join(lines[citation.start_line - 1 : citation.end_line])
        if not citation.quote.strip() or actual != citation.quote:
            raise ValueError("Citation quote mismatch")


def load_bundle(root: Path, snapshot: SkillSnapshot) -> Bundle:
    """Only read manifest-registered files; verify all bytes; no imports/eval."""
    if snapshot.source_kind != "original_skill_md":
        raise ValueError("This pilot requires original Skill packages")
    registry = json.loads(safe_read(root, "seed/community/packages.json", max_bytes=20_000_000))
    package = registry[snapshot.name]
    if digest({k: v for k, v in package.items() if k != "package_sha256"}) != package["package_sha256"]:
        raise ValueError("Package manifest SHA mismatch")
    expected_root = "seed/community/skills/" + snapshot.name
    if package["package_path"] != expected_root or package["commit"] != snapshot.source_commit:
        raise ValueError("Package origin mismatch")
    expected_repo = "https://github.com/" + package["repository"].lower().removesuffix(".git")
    if snapshot.source_repo != expected_repo or package["skill_md_sha256"] != snapshot.document_sha256:
        raise ValueError("Snapshot origin or document identity mismatch")
    expected_resources = {r.path: (r.sha256, r.bytes) for r in snapshot.resources}
    if len(expected_resources) != len(snapshot.resources):
        raise ValueError("Duplicate snapshot resources")
    files: dict[str, SourceFile] = {}
    for row in package["files"]:
        path = row["path"]
        if path in files or expected_resources.get(path) != (row["sha256"], row["bytes"]):
            raise ValueError("Registered resources disagree")
        raw = safe_read(root, expected_root + "/" + path)
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("Resource bytes changed: " + path)
        # The selected pilot packages contain only UTF-8 text resources.
        files[path] = SourceFile(path, row["sha256"], raw.decode("utf-8"))
    if set(files) != set(expected_resources) or files["SKILL.md"].sha256 != snapshot.document_sha256:
        raise ValueError("Snapshot and package disagree")
    if files["SKILL.md"].text != snapshot.document:
        raise ValueError("Snapshot document changed")
    return Bundle(
        snapshot.skill_uid,
        snapshot.name,
        snapshot.source_repo,
        snapshot.source_commit,
        snapshot.source_path,
        files,
    )
