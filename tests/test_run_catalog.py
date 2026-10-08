"""History queries must remain correct across checkpoint rewrites and restart."""
import json
import os
from pathlib import Path

from skillnet.runtime import Run, RunStore, RunStep, ProgrammaticCheck, VerificationResult


def record(store, rid, started, task="公开示例", status="COMPLETED"):
    run = Run(run_id=rid, task=task, task_fp="sample", status=status, started_at_ms=started)
    store.save(run)
    return run


def test_checkpoint_mtime_does_not_hide_newest_task(tmp_path):
    store = RunStore(tmp_path)
    record(store, "older", 100)
    record(store, "newer", 200)
    os.utime(tmp_path / "older.json", (3000000000, 3000000000))
    cold = RunStore(tmp_path)
    assert cold.list_recent(limit=1)[0]["run_id"] == "newer"


def test_paging_search_full_task_live_state_and_evidence(tmp_path):
    store = RunStore(tmp_path)
    run = record(store, "a", 200, "长问题" * 100 + "needle")
    record(store, "b", 200)
    record(store, "c", 100, status="FAILED")
    run.status = "EXECUTING"
    run.steps = [RunStep(idx=3, action="实际执行", checks=[ProgrammaticCheck("csv", True)],
                         verifications=[VerificationResult("结论", False)], code="private code")]
    run.staged["learning_gate"] = {"eligible": False, "reason": "语义验收未通过"}
    page = store.list_page(limit=1)
    assert page["runs"][0]["run_id"] == "b"
    assert store.list_page(limit=1, offset=1)["runs"][0]["run_id"] == "a"
    found = store.list_page(q="NEEDLE", status="EXECUTING")
    assert found["total"] == 1 and found["summary"]["active"] == 1
    row = found["runs"][0]
    assert (row["checks_passed"], row["checks_total"], row["semantic_passed"], row["semantic_total"]) == (1, 1, 0, 1)
    assert row["learning_eligible"] is False
    assert "private code" not in json.dumps(found) and "_search" not in row


def test_summary_cache_only_reads_changed_files_and_removes_deleted(tmp_path, monkeypatch):
    record(RunStore(tmp_path), "a", 100)
    record(RunStore(tmp_path), "b", 200)
    (tmp_path / "corrupt.json").write_text("{", encoding="utf-8")
    (tmp_path / "array.json").write_text("[]", encoding="utf-8")
    store = RunStore(tmp_path)
    reads = []
    original = Path.read_text
    def read(path, *args, **kwargs):
        reads.append(path.name)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    assert store.list_page()["total"] == 2
    reads.clear()
    store.list_page()
    assert "a.json" not in reads and "b.json" not in reads
    record(RunStore(tmp_path), "a", 300)
    (tmp_path / "b.json").unlink()
    assert store.list_page()["total"] == 1
    assert store.list_recent()[0]["started_at_ms"] == 300


def test_input_version_survives_roundtrip(tmp_path):
    store = RunStore(tmp_path)
    run = record(store, "versions", 100)
    provenance = {"logical_name": "figure.png", "name": "step3_figure.png", "from_step": 2, "sha256": "abc"}
    run.steps = [RunStep(idx=0, action="读取", depends_on=[2], inputs=["figure.png"], input_artifacts=[provenance])]
    store.save(run)
    assert RunStore(tmp_path).get("versions").steps[0].input_artifacts == [provenance]
