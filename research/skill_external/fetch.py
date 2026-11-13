"""Fetch an immutable public data snapshot without importing its executable code."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path, PurePosixPath

import httpx

from research.skill_quality.manifest import file_sha, freeze_files, write_once

COMMIT = "0774768cf49faafbd358a568a6963a5015143982"
REPO = "HanZhi306/SkillTV-Bench"


def fetch(output: Path, archive_cache: Path | None = None) -> dict:
    if output.exists():
        raise FileExistsError("Immutable source directories")
    output.mkdir(parents=True)
    url = f"https://codeload.github.com/{REPO}/tar.gz/{COMMIT}"
    if archive_cache is None:
        with httpx.Client(timeout=180, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        content = response.content
    else:
        content = archive_cache.read_bytes()
    assert len(content) < 150_000_000
    archive = output / "source.tar.gz"
    archive.write_bytes(content)
    selected = []
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tf:
        for member in tf.getmembers():
            parts = PurePosixPath(member.name).parts
            relative = PurePosixPath(*parts[1:])
            name = relative.as_posix()
            if ".." in relative.parts or relative.is_absolute() or not member.isfile():
                continue
            wanted = name.startswith(("data/evaluation/", "baseline/artifact-summaries/")) or name in {
                "README.md",
                "LICENSE",
                "DATA_LICENSE.md",
                "LICENSE_AND_THIRD_PARTY_NOTICES.md",
                "CITATION.cff",
            }
            if not wanted:
                continue
            assert member.size < 10_000_000
            stream = tf.extractfile(member)
            assert stream is not None
            raw = stream.read()
            target = output / "snapshot" / Path(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            selected.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    write_once(
        output / "source.json",
        {
            "repo": REPO,
            "commit": COMMIT,
            "url": url,
            "download_date": "2026-11-13",
            "archive_sha256": file_sha(archive),
            "selected": selected,
        },
    )
    write_once(output / "manifest.json", freeze_files(output, output.rglob("*")))
    return {
        "commit": COMMIT,
        "files": len(selected),
        "archive_bytes": len(content),
        "cases": len(list((output / "snapshot/data/evaluation").iterdir())),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive-cache", type=Path)
    args = parser.parse_args()
    print(json.dumps(fetch(args.output, args.archive_cache), ensure_ascii=False, indent=2))
