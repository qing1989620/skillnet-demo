"""Public-data-derived audit tasks. Answers stay outside selector and worker inputs."""

from __future__ import annotations

import csv
import io
import random
from pathlib import Path

from research.skill_quality.manifest import digest

from .oracle import HEADER, reference
from .sources import source_records


def build_tasks(source: Path) -> list[dict]:
    tasks: list[dict] = []
    for source_index, name in enumerate(["iris", "wine", "wdbc", "banknote"]):
        records = source_records(source, name)
        for mask in range(8):
            for size in [24, 72]:
                for quoted in [False, True]:
                    for boundary in [False, True]:
                        seed = (
                            20261111 + source_index * 100000 + mask * 1000 + size * 10 + quoted * 2 + boundary
                        )
                        rng = random.Random(seed)
                        picked = rng.sample(records, size)
                        rows = [
                            [
                                f"{name}-{r['source_row']}",
                                f"subject-{i}",
                                "train" if i % 3 else "test",
                                r["label"],
                                "0.5001" if not boundary and r["score"] == "0.5000" else r["score"],
                            ]
                            for i, r in enumerate(picked)
                        ]
                        rows[0][1:3] = ["cross-subject", "train"]
                        rows[1][1:3] = ["cross-subject", "test"]
                        rows[1][4] = ""
                        rows[3][1:3] = ["local-subject", "train"]
                        rows[4][1:3] = ["local-subject", "train"]
                        rows[5][4] = ""
                        if quoted:
                            rows[6][0] += ",quoted\nsecond"
                            rows[7][1] += ",group"
                        if boundary:
                            rows[8][3:5], rows[9][3:5] = ["1", "0.5"], ["0", "0.5"]
                        conflict = rows[2].copy()
                        conflict[3] = "0" if conflict[3] == "1" else "1"
                        conflict[4] = "0.2" if conflict[4] != "0.2" else "0.8"
                        rows.extend([conflict, rows[10].copy()])
                        stream = io.StringIO(newline="")
                        writer = csv.writer(stream, lineterminator="\n")
                        writer.writerow(HEADER)
                        writer.writerows(rows)
                        raw = stream.getvalue()
                        intent = {"mask": mask, "threshold": "0.5"}
                        identity = f"{name}-m{mask}-n{size}-q{int(quoted)}-b{int(boundary)}"
                        request: dict = {
                            "task_id": identity,
                            "intent": intent,
                            "profile": {"quoted": quoted, "boundary": boundary},
                            "query": "parse CSV "
                            + ("deduplicate sample id " if mask & 1 else "")
                            + ("exclude cross split subjects " if mask & 2 else "")
                            + ("drop missing score " if mask & 4 else "")
                            + "compute binary metrics",
                        }
                        tasks.append(
                            {
                                "task_id": identity,
                                "dataset": name,
                                "split": "development" if source_index < 2 else "held_out",
                                "cohort": "main",
                                "template": f"m{mask}-q{int(quoted)}-b{int(boundary)}",
                                "source_rows": [r["source_row"] for r in picked],
                                "raw": raw,
                                "input_sha256": digest(raw),
                                "request": request,
                                "expected": reference(raw, intent),
                            }
                        )
    held = [t for t in tasks if t["split"] == "held_out"]
    for original in held:
        if original["request"]["intent"]["mask"] not in [0, 3, 7] or "-n24-" not in original["task_id"]:
            continue
        raw = original["raw"]
        # Add a new record whose score rounds to 0.5 in binary float but is
        # strictly below the declared threshold in exact decimal arithmetic.
        stream = io.StringIO(raw, newline="")
        rows = list(csv.reader(stream))
        rows.append(["precision-row", "precision-subject", "train", "0", "0.499999999999999999999999"])
        output = io.StringIO(newline="")
        csv.writer(output, lineterminator="\n").writerows(rows)
        raw = output.getvalue()
        identity = original["task_id"] + "-precision"
        request = {**original["request"], "task_id": identity}
        tasks.append(
            {
                **original,
                "task_id": identity,
                "request": request,
                "cohort": "precision",
                "raw": raw,
                "input_sha256": digest(raw),
                "expected": reference(raw, request["intent"]),
            }
        )
    return tasks


def probe_input(task: dict, cap: str) -> dict:
    stages, mask = task["expected"]["stages"], task["request"]["intent"]["mask"]
    if cap == "parse":
        return {"raw": task["raw"]}
    before = (
        ("dedup" if mask & 1 else "parse")
        if cap == "exclude"
        else (("exclude" if mask & 2 else "dedup" if mask & 1 else "parse") if cap == "drop" else "parse")
    )
    rows = task["expected"]["rows"] if cap == "metrics" else stages[before]
    return {"rows": [dict(zip(HEADER, r, strict=True)) for r in rows]}
