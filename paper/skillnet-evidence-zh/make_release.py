"""Package the verified paper and public data; never include private run folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDF = "SkillNet_中文研究论文.pdf"
SECRET = re.compile(rb"(?<![A-Za-z0-9_-])sk-(?:or-v1-)?[A-Za-z0-9_-]{20,}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release(output: Path) -> dict:
    verification = json.loads((HERE / "results/verification.json").read_text(encoding="utf-8"))
    assert verification["pdf_sha256"] == sha(HERE / PDF)
    assert verification["rendered_pages_visually_inspected"] == 9
    manifest_path = HERE / "results/release-manifest.json"
    files = []
    for path in sorted(HERE.rglob("*")):
        relative = path.relative_to(HERE)
        if any(part in {"build", "tmp", "__pycache__"} for part in relative.parts):
            continue
        if not path.is_file() or path == manifest_path:
            continue
        if path.is_symlink() or ".private." in path.name or path.name.startswith(".env"):
            raise ValueError("Private or linked material cannot enter the release")
        raw = path.read_bytes()
        if path.suffix.lower() not in {".pdf", ".png"} and SECRET.search(raw):
            raise ValueError("Potential credential detected")
        files.append(path)
    manifest = {
        "date": "2026-11-11",
        "scope": "public manuscript, constructed inputs, actual model artifacts and offline reproduction",
        "hashes_are_integrity_checks_not_external_provider_signatures": True,
        "files": [
            {"path": p.relative_to(HERE).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in files
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.mkdir(parents=True, exist_ok=True)
    pdf_target = output / "SkillNet_中文研究论文_2026-11-11.pdf"
    zip_target = output / "SkillNet_中文论文_LaTeX与数据_2026-11-11.zip"
    shutil.copyfile(HERE / PDF, pdf_target)
    shutil.copyfile(HERE / "README.md", output / "成果与复现说明.md")
    with zipfile.ZipFile(zip_target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as archive:
        for path in [*files, manifest_path]:
            archive.write(path, "SkillNet-paper/" + path.relative_to(HERE).as_posix())
    with zipfile.ZipFile(zip_target) as archive:
        assert archive.testzip() is None
        for record in manifest["files"]:
            raw = archive.read("SkillNet-paper/" + record["path"])
            assert hashlib.sha256(raw).hexdigest() == record["sha256"]
    result = {
        "pdf": str(pdf_target.resolve()),
        "pdf_sha256": sha(pdf_target),
        "source_zip": str(zip_target.resolve()),
        "source_zip_sha256": sha(zip_target),
        "source_files": len(files) + 1,
    }
    (output / "交付校验.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=HERE.parents[2] / "reports/SkillNet_中文论文_2026-11-11"
    )
    print(json.dumps(release(parser.parse_args().output), ensure_ascii=False, indent=2))
