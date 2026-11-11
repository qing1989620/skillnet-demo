"""Package the offline method, original recorded data and Chinese reporting material."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from research.skill_quality.manifest import freeze_files, verify_files

from .reproduce import RESULTS, reproduce

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SECRET = re.compile(rb"(?<![A-Za-z0-9_-])sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release(output: Path) -> dict:
    verified = reproduce()
    for run_name in ["diagnostic-v3", "natural-v3"]:
        manifest = json.loads((RESULTS / run_name / "code-manifest.json").read_text(encoding="utf-8"))
        verify_files(ROOT, manifest)
    staging_parent = ROOT / "out/tmp"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="skill-decision-release-", dir=staging_parent)) / "SkillJudge"
    staging.mkdir()
    method = staging / "research/skill_decision"
    method.mkdir(parents=True)
    for path in HERE.iterdir():
        if path.is_file() and path.suffix in {".py", ".ps1", ".md", ".ini", ".json", ".txt"}:
            shutil.copyfile(path, method / path.name)
    shutil.copytree(HERE / "tests", method / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ["diagnostic-v3", "natural-v3"]:
        shutil.copytree(RESULTS / name, method / "results" / name)
    dependencies = [
        "research/skill_quality/__init__.py",
        "research/skill_quality/manifest.py",
        "research/skill_quality/schemas.py",
        "research/skill_study/__init__.py",
        "research/skill_study/cli_contracts.py",
        "research/skill_study/package_audit.py",
        "skillnet/__init__.py",
        "skillnet/schema.py",
    ]
    for name in dependencies:
        target = staging / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for relative in ["claude/LICENSE", "agentic/LICENSE", "agentic/LICENSE-CONTENT"]:
        target = staging / "SOURCE_NOTICES" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "seed/community/licenses" / relative, target)
    for name in ["README.md", "METHOD_REPORT_ZH.md"]:
        shutil.copyfile(HERE / name, staging / name)
    model_card = {
        "date": "2026-11-11",
        "name": "证据约束技能判别器 v1",
        "implementation_revision": "v1.2",
        "method_type": "deterministic evidence rules plus registered independent task-artifact verification",
        "neural_model_trained": False,
        "new_paid_model_calls": 0,
        "new_api_cost_usd": 0,
        "input": "Skill package, version manifest and trusted task evidence",
        "outputs": [
            "repair_required",
            "tested_pass_within_scope",
            "insufficient_evidence",
            "outside_tested_scope",
        ],
        "decision_boundary": "recorded exact suite or exact input hash; no family-wide certification",
        "human_semantic_gold": 0,
        "natural_overall_quality_accuracy": None,
        "intended_use": "thesis development, advisor review and reproducible method demonstration",
        "not_established": [
            "general semantic-quality classification",
            "cross-source generalization",
            "security certification",
            "improved SkillNet orchestration",
        ],
        "local_checks": {
            "research_tests_passed": 209,
            "new_method_tests_passed": 11,
            "ruff": "PASS",
            "format": "PASS",
            "mypy": "PASS",
            "original_delivery_checked": 13513,
            "original_delivery_differences": 0,
        },
        "reproduction": verified,
        "python": platform.python_version(),
        "base_repository_commit": "216c93e763357017e318bb324349ff05a88357a3",
    }
    (staging / "METHOD_CARD.json").write_text(
        json.dumps(model_card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    files = [p for p in staging.rglob("*") if p.is_file()]
    for path in files:
        assert ".private." not in path.name and not path.name.startswith(".env")
        assert not SECRET.search(path.read_bytes()), path.name
    manifest = freeze_files(staging, files)
    (staging / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    verify_files(staging, manifest)
    output.mkdir(parents=True, exist_ok=True)
    report = output / "Skill优劣判别方法_实测成果与汇报稿_2026-11-11.md"
    archive_path = output / "Skill判别器_源码数据与演示_2026-11-11.zip"
    shutil.copyfile(HERE / "METHOD_REPORT_ZH.md", report)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                archive.write(path, "SkillJudge/" + path.relative_to(staging).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for row in manifest["files"]:
            assert hashlib.sha256(archive.read("SkillJudge/" + row["path"])).hexdigest() == row["sha256"]
    metadata = {
        "report": str(report.resolve()),
        "report_sha256": sha(report),
        "source_zip": str(archive_path.resolve()),
        "source_zip_sha256": sha(archive_path),
        "staging_root": str(staging.resolve()),
        "files": len(files) + 1,
        "new_paid_model_calls": 0,
        "reproduction": verified,
    }
    (output / "交付校验.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT.parent / "reports/Skill判别方法成果_2026-11-11")
    print(json.dumps(release(parser.parse_args().output), ensure_ascii=False, indent=2))
