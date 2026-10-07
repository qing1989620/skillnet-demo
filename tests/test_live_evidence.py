"""Live stage evidence must come from the same execution, with bounded payloads."""
from __future__ import annotations

import hashlib

from skillnet import llm, pipeline, runtime, sandbox


def test_live_evidence_records_actual_code_output_file_and_checks(tmp_path, monkeypatch):
    code = "print('public demo')"
    calls = []

    def chat(*args, **kwargs):
        calls.append(kwargs.get("role"))
        return code

    def execute(script, **kwargs):
        assert script == code
        csv = kwargs["workdir"] / "summary.csv"
        csv.write_text("group,mean\nA,3\n", encoding="utf-8")
        return {"ok": True, "stdout": "public demo\n" * 300, "stderr": "",
                "duration": .01, "returncode": 0,
                "artifacts": [{"path": str(csv)}]}

    monkeypatch.setattr(llm, "chat", chat)
    monkeypatch.setattr(pipeline.sandbox, "available_stack", lambda: {})
    monkeypatch.setattr(pipeline.sandbox, "run_python", execute)
    run = runtime.Run(run_id=runtime.new_run_id("evidence"), task="public demo", task_fp="evidence")
    with llm.ledger_scope():
        pipeline.execute_run(run, None, tmp_path / "workspace",
                             {"steps": [{"action": "compute public data"}]})
    events = run.events
    kinds = [e.type for e in events]
    generated = next(e for e in events if e.type == "code.generated")
    attempt = next(e for e in events if e.type == "step.attempt")
    artifact = next(e for e in events if e.type == "artifact.created")
    assert generated.data["code"] == code == run.steps[0].code
    assert generated.data["chars"] == len(code)
    assert not generated.data["truncated"]
    assert kinds.index("code.generating") < kinds.index("code.generated") < kinds.index("sandbox.started")
    assert kinds.index("sandbox.started") < kinds.index("step.attempt") < kinds.index("verification.started")
    assert attempt.data["stdout"] == run.steps[0].attempts[0].stdout[-2000:]
    assert len(attempt.data["stdout"]) <= 2000
    assert artifact.data["sha256"] == hashlib.sha256(
        (tmp_path / "workspace" / "artifacts" / artifact.data["name"]).read_bytes()).hexdigest()
    assert len([e for e in events if e.type == "check.result"]) == len(run.steps[0].checks)
    assert calls == ["executor"], "observability must not introduce extra model calls"
    assert [e.seq for e in events] == list(range(1, len(events) + 1))


def test_code_evidence_is_bounded_without_changing_executed_program(tmp_path, monkeypatch):
    code = "# public demo\n" * 2000 + "print(1)"
    executed = []
    monkeypatch.setattr(llm, "chat", lambda *args, **kwargs: code)
    monkeypatch.setattr(pipeline.sandbox, "available_stack", lambda: {})

    def execute(script, **kwargs):
        executed.append(script)
        return {"ok": True, "stdout": "1", "stderr": "", "duration": .01, "artifacts": []}

    monkeypatch.setattr(pipeline.sandbox, "run_python", execute)
    run = runtime.Run(run_id=runtime.new_run_id("bounded"), task="public demo", task_fp="bounded")
    with llm.ledger_scope():
        pipeline.execute_run(run, None, tmp_path / "workspace", {"steps": [{"action": "compute"}]})
    generated = next(e for e in run.events if e.type == "code.generated")
    assert executed == [code]
    assert len(generated.data["code"]) == 24000
    assert generated.data["chars"] == len(code)
    assert generated.data["truncated"] is True


def test_modified_input_is_registered_even_with_same_size_and_mtime(tmp_path):
    csv = tmp_path / "summary.csv"
    csv.write_text("group,mean\nA,3\n", encoding="utf-8")
    before = csv.stat()
    script = """from pathlib import Path
import os
p = Path('summary.csv')
s = p.stat()
p.write_text('group,mean\\nA,4\\n', encoding='utf-8')
os.utime(p, ns=(s.st_atime_ns, s.st_mtime_ns))
print('corrected')
"""
    result = sandbox.run_python(script, workdir=tmp_path, keep_dir=True)
    assert result["ok"]
    assert csv.stat().st_size == before.st_size
    assert csv.stat().st_mtime_ns == before.st_mtime_ns
    assert [a["name"] for a in result["artifacts"]] == ["summary.csv"]


def test_unchanged_inputs_excluded_but_nested_same_basename_is_new(tmp_path):
    (tmp_path / "summary.csv").write_text("group,mean\nA,3\n", encoding="utf-8")
    folder = tmp_path / "prior"
    folder.mkdir()
    (folder / "report.md").write_text("unchanged", encoding="utf-8")
    result = sandbox.run_python("""from pathlib import Path
p = Path('new')
p.mkdir()
(p / 'summary.csv').write_text('group,mean\\nB,4\\n', encoding='utf-8')
print(Path('summary.csv').read_text())
""", workdir=tmp_path, keep_dir=True)
    assert result["ok"]
    assert [a["name"] for a in result["artifacts"]] == ["new/summary.csv"]


def test_modified_file_flows_through_later_steps_with_distinct_provenance(tmp_path, monkeypatch):
    programs = iter([
        "from pathlib import Path\nPath('summary.csv').write_text('group,mean\\nA,3\\n')\nprint('created')",
        "from pathlib import Path\np=Path('summary.csv')\np.write_text(p.read_text().replace('A,3','A,4'))\nprint('corrected')",
        "from pathlib import Path\ns=Path('summary.csv').read_text()\nassert 'A,4' in s\nPath('verified.txt').write_text(s)\nprint('verified latest version')",
    ])
    monkeypatch.setattr(llm, "chat", lambda *a, **k: next(programs))
    monkeypatch.setattr(sandbox, "available_stack", lambda: {})
    run = runtime.Run(run_id=runtime.new_run_id("versions"), task="public demo", task_fp="versions")
    with llm.ledger_scope():
        pipeline.execute_run(run, None, tmp_path / "workspace",
                             {"steps": [{"action": "create"}, {"action": "correct"}, {"action": "verify"}]})
    assert all(s.status == runtime.STEP_DONE for s in run.steps)
    assert [a.name for a in run.artifacts] == ["step1_summary.csv", "step2_summary.csv", "step3_verified.txt"]
    assert "A,3" in (tmp_path / "workspace/artifacts/step1_summary.csv").read_text()
    assert "A,4" in (tmp_path / "workspace/artifacts/step2_summary.csv").read_text()
    assert "A,4" in (tmp_path / "workspace/artifacts/step3_verified.txt").read_text()


def test_repair_reads_stdout_diagnostic_when_stderr_is_empty(tmp_path, monkeypatch):
    calls = []

    def chat(messages, **kwargs):
        calls.append(messages)
        if len(calls) == 1:
            return "import sys\nprint('mean dtype check failed: cast mean to float')\nsys.exit(1)"
        assert "mean dtype check failed: cast mean to float" in messages[1]["content"]
        return "from pathlib import Path\nPath('verified.txt').write_text('fixed')\nprint('fixed')"

    monkeypatch.setattr(llm, "chat", chat)
    monkeypatch.setattr(sandbox, "available_stack", lambda: {})
    run = runtime.Run(run_id=runtime.new_run_id("repair"), task="public demo", task_fp="repair")
    with llm.ledger_scope():
        pipeline.execute_run(run, None, tmp_path / "workspace", {"steps": [{"action": "compute"}]})
    assert run.steps[0].status == runtime.STEP_DONE
    assert run.steps[0].fixed
    assert len(calls) == 2
    assert run.steps[0].attempts[0].stderr == "", "raw stderr must remain faithful to the process"


def test_exhausted_stdout_only_failure_has_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: "import sys\nprint('column check failed')\nsys.exit(1)")
    monkeypatch.setattr(sandbox, "available_stack", lambda: {})
    run = runtime.Run(run_id=runtime.new_run_id("error"), task="public demo", task_fp="error")
    with llm.ledger_scope():
        pipeline.execute_run(run, None, tmp_path / "workspace", {"steps": [{"action": "compute"}]})
    assert run.steps[0].status == runtime.STEP_FAILED
    assert "column check failed" in run.steps[0].error
