"""Package an offline, byte-verifiable thesis draft with both actual methods."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PDF_NAME = "SkillNet_双方法与网络优化_中文研究论文_2026-11-11_v2.pdf"
ZIP_NAME = "SkillNet_双方法论文_LaTeX源码代码与逐次数据_2026-11-11_v2.zip"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def package(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    parent = ROOT / "out/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="skillnet-v2-release-", dir=parent)) / "SkillNet_双方法研究"
    stage.mkdir()
    paper = stage / "paper/skillnet-evidence-zh-v2"
    shutil.copytree(HERE, paper, ignore=shutil.ignore_patterns("build", "tmp", "__pycache__", "*.pdf", "verification.json", "release-manifest.json"))
    # Include vector figures, but not intermediate compiled manuscript copies.
    for path in (HERE / "figures").glob("*.pdf"):
        copy_file(path, paper / "figures" / path.name)
    for module in ["skill_network", "skill_decision"]:
        target = stage / "research" / module
        shutil.copytree(ROOT / "research" / module, target,
                        ignore=shutil.ignore_patterns("results", "__pycache__", ".pytest_cache", ".mypy_cache"))
        names = ["prepared-v3", "calibration-v2", "execution-v2", "analysis-v1", "joint-posthoc-v1", "sources-v2"] if module == "skill_network" else ["diagnostic-v3", "natural-v3"]
        for name in names:
            shutil.copytree(ROOT / "research" / module / "results" / name, target / "results" / name)
    dependencies = [
        "research/skill_quality/__init__.py", "research/skill_quality/manifest.py", "research/skill_quality/schemas.py",
        "research/skill_study/__init__.py", "research/skill_study/cli_contracts.py", "research/skill_study/package_audit.py",
        "research/skill_study/routing_pilot.py", "skillnet/__init__.py", "skillnet/schema.py", "skillnet/frontier.py",
    ]
    for relative in dependencies:
        copy_file(ROOT / relative, stage / relative)
    for name in ["claude/LICENSE", "agentic/LICENSE", "agentic/LICENSE-CONTENT"]:
        copy_file(ROOT / "seed/community/licenses" / name, stage / "SOURCE_NOTICES" / name)
    for name in ["README.md", "成果说明_先读这里.md", "THIRD_PARTY_NOTICES.md"]:
        copy_file(HERE / name, stage / name)
    copy_file(HERE / "requirements-reproduce.txt", stage / "requirements.txt")
    copy_file(HERE / "verification.json", stage / "verification.json")
    copy_file(HERE / "build/main.pdf", stage / PDF_NAME)
    secret = re.compile(rb"(?<![A-Za-z0-9_-])sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}")
    files = sorted(path for path in stage.rglob("*") if path.is_file())
    for path in files:
        assert path.name not in {".env", ".env.local"}
        if path.suffix not in {".pdf", ".png", ".zip"}:
            assert not secret.search(path.read_bytes()), f"Credential-shaped value in {path.relative_to(stage)}"
    manifest = {"format": "skillnet-two-method-paper-v2", "date": "2026-11-11", "new_api_calls": 0,
                "source_files": [{"path": p.relative_to(stage).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
                "scope": "Controlled executable network, not natural SkillNet-wide certification"}
    (stage / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    zip_path = output / ZIP_NAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(stage.parent).as_posix())
    copy_file(HERE / "build/main.pdf", output / PDF_NAME)
    copy_file(HERE / "成果说明_先读这里.md", output / "成果说明_先读这里.md")
    result = {"pdf": str(output / PDF_NAME), "pdf_sha256": sha(output / PDF_NAME),
              "zip": str(zip_path), "zip_sha256": sha(zip_path), "files": len(files)+1,
              "stage": str(stage), "new_api_calls": 0}
    (output / "交付清单.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.output.resolve()), ensure_ascii=False, indent=2))
