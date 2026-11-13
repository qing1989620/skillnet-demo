"""Obtain small CC BY UCI archives; treat all downloaded files as data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from decimal import Decimal
from pathlib import Path

import httpx

from research.skill_quality.manifest import freeze_files, write_once

SOURCES: dict[str, dict] = {
    "iris": {
        "id": 53,
        "slug": "iris",
        "file": "iris.data",
        "rows": 150,
        "doi": "10.24432/C56C76",
        "citation": "Fisher, R. (1936). Iris. UCI Machine Learning Repository.",
    },
    "wine": {
        "id": 109,
        "slug": "wine",
        "file": "wine.data",
        "rows": 178,
        "doi": "10.24432/C5PC7J",
        "citation": "Aeberhard, S. and Forina, M. (1992). Wine. UCI Machine Learning Repository.",
    },
    "wdbc": {
        "id": 17,
        "slug": "breast+cancer+wisconsin+diagnostic",
        "file": "wdbc.data",
        "rows": 569,
        "doi": "10.24432/C5DW2B",
        "citation": "Wolberg, W., Mangasarian, O., Street, N. and Street, W. Breast Cancer Wisconsin (Diagnostic). UCI Machine Learning Repository.",
    },
    "banknote": {
        "id": 267,
        "slug": "banknote+authentication",
        "file": "data_banknote_authentication.txt",
        "rows": 1372,
        "doi": "10.24432/C55P57",
        "citation": "Lohweg, V. (2012). Banknote Authentication. UCI Machine Learning Repository.",
    },
}


def fetch(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Source IDs are immutable")
    output.mkdir(parents=True)
    records = []
    with httpx.Client(timeout=60, follow_redirects=True, trust_env=False) as client:
        for name, source in SOURCES.items():
            url = f"https://archive.ics.uci.edu/static/public/{source['id']}/{source['slug']}.zip"
            response = client.get(url)
            response.raise_for_status()
            raw = response.content
            assert len(raw) < 2_000_000
            (output / f"{name}.zip").write_bytes(raw)
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                candidates = [n for n in archive.namelist() if n.rsplit("/", 1)[-1] == source["file"]]
                assert len(candidates) == 1
                entry = archive.getinfo(candidates[0])
                assert entry.file_size < 2_000_000
                data = archive.read(entry)
            table = [r for r in csv.reader(io.StringIO(data.decode("utf-8"))) if r]
            assert len(table) == source["rows"]
            (output / source["file"]).write_bytes(data)
            page = f"https://archive.ics.uci.edu/dataset/{source['id']}/{source['slug']}"
            records.append(
                {
                    "name": name,
                    **source,
                    "url": url,
                    "primary_page": page,
                    "license": "CC BY 4.0",
                    "archive_sha256": hashlib.sha256(raw).hexdigest(),
                    "data_sha256": hashlib.sha256(data).hexdigest(),
                    "download_date": "2026-11-11",
                }
            )
    manifest = {
        "sources": records,
        "medical_prediction_claims": False,
        "use": "derived tabular audit tasks, not classifiers for the original dataset target",
    }
    write_once(output / "sources.json", manifest)
    write_once(output / "manifest.json", freeze_files(output, output.iterdir()))
    return manifest


def source_records(directory: Path, name: str) -> list[dict]:
    source = SOURCES[name]
    table = [
        r for r in csv.reader(io.StringIO((directory / source["file"]).read_text(encoding="utf-8"))) if r
    ]
    values = [Decimal(r[1] if name == "wine" else r[2] if name == "wdbc" else r[0]) for r in table]
    low, high = min(values), max(values)
    records = []
    for index, (row, value) in enumerate(zip(table, values, strict=True)):
        label = (
            row[-1] == "Iris-virginica"
            if name == "iris"
            else row[0] == "1"
            if name == "wine"
            else row[1] == "M"
            if name == "wdbc"
            else row[-1] == "1"
        )
        score = (value - low) / (high - low)
        records.append({"source_row": index, "label": str(int(label)), "score": format(score, ".4f")})
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(fetch(args.output), ensure_ascii=False, indent=2))
