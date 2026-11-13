"""Build label-free context and inspect existing artifacts without executing them."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from research.skill_quality.manifest import digest, file_sha, freeze_files, write_once

SECRET = re.compile(r"sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9_.-]{20,}")


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    marker = f"\n[EXPLICIT CONTEXT TRUNCATION: original {len(text)} characters]\n"
    head = (limit - len(marker)) // 2
    return text[:head] + marker + text[-(limit - len(marker) - head) :]


def obj_facts(path: Path) -> dict:
    vertices, faces, groups, indices = 0, 0, 0, []
    finite = True
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if parts[0] == "v":
            vertices += 1
            try:
                finite &= all(math.isfinite(float(x)) for x in parts[1:4]) and len(parts) >= 4
            except ValueError:
                finite = False
        elif parts[0] == "f":
            faces += 1
            for token in parts[1:]:
                try:
                    value = int(token.split("/")[0])
                    indices.append((value, vertices))
                except ValueError:
                    indices.append((0, vertices))
        elif parts[0] in {"g", "o"}:
            groups += 1
    bad = sum(i == 0 or (i > 0 and i > vertices) or (i < 0 and -i > seen) for i, seen in indices)
    return {
        "vertices": vertices,
        "faces": faces,
        "groups_or_objects": groups,
        "nonfinite_or_malformed_vertices": not finite,
        "bad_vertex_references": bad,
    }


def inspect_artifacts(case: Path) -> list[dict]:
    root = case / "environment/artifacts"
    paths = sorted(p for p in root.rglob("*") if p.is_file() and p.name != ".gitkeep")
    facts = [
        {
            "ref": "artifact-snapshot-scope",
            "text": "Only the released partial snapshot is inspected. An unprovided artifact is NOT evidence that the original agent failed to create it.",
            "supplied_files": len(paths),
        }
    ]
    obj = []
    for path in paths:
        assert path.stat().st_size < 10_000_000
        relative = path.relative_to(root).as_posix()
        if path.suffix == ".obj":
            obj.append({"path": relative, **obj_facts(path)})
        elif path.suffix == ".json":
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                facts.append(
                    {
                        "ref": "artifact:" + relative,
                        "sha256": file_sha(path),
                        "type": type(value).__name__,
                        "keys": list(value)[:30] if isinstance(value, dict) else None,
                        "preview": clip(json.dumps(value, ensure_ascii=False), 5000),
                    }
                )
            except (ValueError, UnicodeDecodeError):
                facts.append({"ref": "artifact:" + relative, "parse_error": "invalid JSON or UTF-8"})
    if obj:
        facts.append(
            {
                "ref": "obj-aggregate",
                "files": len(obj),
                "vertices_total": sum(x["vertices"] for x in obj),
                "faces_total": sum(x["faces"] for x in obj),
                "bad_reference_files": [x["path"] for x in obj if x["bad_vertex_references"]],
                "nonfinite_files": [x["path"] for x in obj if x["nonfinite_or_malformed_vertices"]],
                "disclaimer": "Structural OBJ facts only; not rendering, physical or task correctness verification.",
            }
        )
        facts.append({"ref": "obj-file-examples", "examples": obj[:16]})
    return facts


def context(case: Path, summaries: Path) -> dict:
    env = case / "environment"
    instruction = (env / "original_task_instruction.md").read_text(encoding="utf-8")
    source = json.loads((env / "trajectory.json").read_text(encoding="utf-8"))
    steps = []
    for i, step in enumerate(source["steps"]):
        allowed = {
            k: step[k]
            for k in ["kind", "role", "text", "tool_name", "tool_input", "tool_output"]
            if k in step
        }
        steps.append("step:" + str(i + 1) + "\n" + json.dumps(allowed, ensure_ascii=False))
    trajectory = clip("\n\n".join(steps), 48000)
    skills = []
    for path in sorted((env / "available_skills").glob("*/SKILL.md")):
        skills.append({"ref": "skill:" + path.parent.name, "text": path.read_text(encoding="utf-8")})
    skill_text = clip(json.dumps(skills, ensure_ascii=False), 12000)
    matches = [p for p in summaries.glob("*.md") if p.stem.casefold().endswith(case.name.casefold())]
    assert len(matches) <= 1
    summary = (
        matches[0].read_text(encoding="utf-8")
        if matches
        else "No official artifact summary supplied; this does not prove output absence."
    )
    artifact_facts = inspect_artifacts(case)
    packet = {
        "case_id": case.name,
        "instruction": clip(instruction, 12000),
        "trajectory": trajectory,
        "available_skills": skill_text,
        "official_artifact_summary": clip(summary, 12000),
        "artifact_facts": clip(json.dumps(artifact_facts, ensure_ascii=False), 12000),
        "allowed_refs": [
            "instruction",
            "official-summary",
            *re.findall(r"step:\d+", trajectory),
            *re.findall(r'"ref": "([^"]+)"', skill_text),
            *[r["ref"] for r in artifact_facts],
        ],
        "context_truncated": any(
            "EXPLICIT CONTEXT TRUNCATION" in v
            for v in [clip(instruction, 12000), trajectory, skill_text, clip(summary, 12000)]
        ),
        "original_trajectory_chars": sum(len(s) for s in steps),
        "has_official_summary": bool(matches),
    }
    raw = json.dumps(packet, ensure_ascii=False)
    redacted, count = SECRET.subn("[REDACTED_PROVIDER_SECRET]", raw)
    packet = json.loads(redacted)
    packet["redacted_credential_patterns"] = count
    return packet


def prepare(source: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Immutable preparation")
    output.mkdir(parents=True)
    snapshot = source / "snapshot"
    cases = sorted((snapshot / "data/evaluation").iterdir())
    assert len(cases) == 203
    packets, group_rows = [], []
    for case in cases:
        packets.append(context(case, snapshot / "baseline/artifact-summaries"))
        metadata = json.loads((case / "metadata.json").read_text(encoding="utf-8"))
        # Explicit allowlist, never copy reward or trajectory_label into inference.
        group_rows.append(
            {
                "case_id": case.name,
                "task": metadata["source_task_name"],
                "domain": metadata["source_domain_slug"],
            }
        )
    write_once(output / "packets.jsonl", packets, jsonl=True)
    write_once(output / "groups.jsonl", group_rows, jsonl=True)
    protocol_path = Path(__file__).with_name("protocol.json")
    write_once(output / "protocol.json", json.loads(protocol_path.read_text(encoding="utf-8")))
    summary = {
        "cases": len(packets),
        "source_tasks": len({r["task"] for r in group_rows}),
        "domains": dict(Counter(r["domain"] for r in group_rows)),
        "official_summaries": sum(r["has_official_summary"] for r in packets),
        "truncated_contexts": sum(r["context_truncated"] for r in packets),
        "redactions": sum(r["redacted_credential_patterns"] for r in packets),
        "packet_digest": digest(packets),
        "label_fields_in_packets": 0,
    }
    write_once(output / "summary.json", summary)
    write_once(
        output / "code-manifest.json",
        freeze_files(Path.cwd(), list(Path(__file__).parent.glob("*.py")) + [protocol_path]),
    )
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return summary
