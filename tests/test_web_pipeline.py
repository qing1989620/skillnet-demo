"""Real subprocess regressions for host web evidence in the DAG executor.

Only the language model is stubbed. The generated fixture programs execute in
the normal process sandbox; no external service or paid model is contacted.
"""
import hashlib
import json

import pytest

from skillnet import executor, llm, pipeline, runtime, web_research


NAME = '肖海冰'
TASK = '介绍肖海冰的故事，先核验机构和研究领域再整理著作'
URL = 'https://public-source.org/person'
TEXT = '这是实际冻结的公开来源记录，但目前无法确认同名人物的机构与研究领域。'


@pytest.fixture(autouse=True)
def isolated_execution(monkeypatch):
    monkeypatch.setenv('SKILLNET_SANDBOX', 'process')
    monkeypatch.setattr(executor, '_record_execution', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline.sandbox, 'available_stack', lambda: {})
    with llm.ledger_scope(llm.UsageLedger()):
        yield


def make_run(task=TASK):
    run = runtime.Run(run_id='offline-web-pipeline', task=task, task_fp='offline-web')
    run.budget = runtime.Budget(max_cost_yuan=1, max_llm_calls=20, max_seconds=30,
                               max_attempts_per_step=1)
    return run


def attach_file(run, workspace, name, data, *, logical=None, kind='任务输入'):
    path = workspace / 'artifacts' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    run.artifacts.append(runtime.Artifact(name=name, logical_name=logical or name,
        kind=kind, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        source_run_id='historical-run' if kind == '跨轮输入' else run.run_id))
    return path


def attach_evidence(run, workspace, *, identity=True):
    raw = TEXT.encode('utf-8')
    attach_file(run, workspace, 'web_snapshot_01.txt', raw)
    report = dict(version=web_research.VERSION, needed=True, enabled=True,
        identity_name=NAME if identity else '', state='success', evidence_file='web_sources.json', sources=[dict(
            source_id='web-01', url=URL, requested_url=URL, state='fetched',
            retrieval_mode='direct_fetch', content_type='text/plain; charset=utf-8',
            text_file='web_snapshot_01.txt', sha256=hashlib.sha256(raw).hexdigest(), text=TEXT)])
    index = json.dumps(report, ensure_ascii=False).encode('utf-8')
    report['evidence_sha256'] = hashlib.sha256(index).hexdigest()
    attach_file(run, workspace, 'web_sources.json', index)
    run.staged['web_research'] = report
    return report


def stub_model(monkeypatch, codes):
    prompts = []

    def chat(messages, **_kwargs):
        prompts.append(messages[-1]['content'])
        if len(prompts) > len(codes):
            pytest.fail('A blocked downstream step reached code generation')
        return '```python\n' + codes[len(prompts)-1] + '\n```'

    monkeypatch.setattr(pipeline.llm, 'chat', chat)
    return prompts


def write_csv_code(name, rows):
    fields = ['name', 'institution', 'domain', 'evidence_url', 'same_person']
    return ('import csv\n'
        f'with open({name!r}, "w", encoding="utf-8", newline="") as stream:\n'
        f'    writer = csv.DictWriter(stream, fieldnames={fields!r})\n'
        '    writer.writeheader()\n'
        f'    writer.writerows({rows!r})\n'
        'print("identity evidence retained")\n')


@pytest.mark.parametrize('case', ['missing', 'empty', 'unknown', 'unsupported_true', 'quote_only'])
def test_unresolved_identity_never_dispatches_clustering_even_if_plan_claims_parallel_roots(tmp_path, monkeypatch, case):
    workspace = tmp_path / 'workspace'
    run = make_run()
    report = attach_evidence(run, workspace)
    if case == 'missing':
        code = 'from pathlib import Path\nPath("gap.txt").write_text("missing identity evidence")\nprint("gap")'
    elif case in ('empty', 'quote_only'):
        code = write_csv_code('identity_ledger.csv', [])
        if case == 'quote_only':
            code += ('with open("factual_claims.csv", "w", encoding="utf-8", newline="") as stream:\n'
                     '    writer = csv.writer(stream)\n'
                     '    writer.writerow(["source_id", "evidence_url", "claim", "quote"])\n'
                     f'    writer.writerow(["web-01", {URL!r}, "source excerpt", {TEXT!r}])\n')
    else:
        code = write_csv_code('identity_ledger.csv', [dict(name=NAME, institution='尚未确认机构',
            domain='尚未确认领域', evidence_url=URL,
            same_person='unknown' if case == 'unknown' else 'true')])
    prompts = stub_model(monkeypatch, [code])
    plan = {'steps': [
        {'action': '检索人物资料', 'input_files': [], 'output_files': [], 'depends_on': []},
        {'action': '聚类人物著作并分析科研贡献', 'input_files': [],
         'output_files': ['cluster.csv'], 'depends_on': []},
    ]}
    bound = web_research.bind_plan(plan, report)
    assert bound['steps'][1]['depends_on'] == [0]
    pipeline.execute_run(run, None, workspace, bound, max_steps=2)
    pipeline.finalize_status(run)
    assert len(prompts) == 1
    assert run.steps[1].status == runtime.STEP_SKIPPED
    assert run.steps[1].n_attempts == 0 and run.steps[1].code == ''
    gate = run.steps[0].state_evidence['web_citations']
    assert gate['identity_rows'] >= 1 and gate['identity_state'] != 'verified'
    assert run.status != runtime.STATUS_COMPLETED
    assert not (workspace / 'artifacts' / 'step2_cluster.csv').exists()


def test_host_web_context_reaches_actual_codegen_and_frozen_evidence_is_readable(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    run = make_run()
    report = attach_evidence(run, workspace)
    code = ('import json\n'
            'with open("web_sources.json", encoding="utf-8") as stream:\n'
            '    evidence = json.load(stream)\n'
            f'assert evidence["identity_name"] == {NAME!r}\n'
            'assert evidence["sources"][0]["source_id"] == "web-01"\n'
            'assert evidence["sources"][0]["sha256"]\n'
            + write_csv_code('identity_ledger.csv', [dict(name=NAME, institution='', domain='',
                evidence_url=URL, same_person='unknown')]))
    prompts = stub_model(monkeypatch, [code])
    plan = web_research.bind_plan({'steps': [{'action': '检索并核验人物',
        'input_files': [], 'output_files': []}]}, report)
    pipeline.execute_run(run, None, workspace, plan, max_steps=1)
    step = run.steps[0]
    assert step.attempts[0].ok and 'identity evidence retained' in step.attempts[0].stdout
    assert step.inputs == ['web_sources.json']
    assert '【宿主联网证据】' in prompts[0] and 'host_collected' in prompts[0]
    assert 'web_sources.json' in prompts[0] and '不能重造搜索命中' in prompts[0]
    copied = workspace / 'step1' / 'try1' / 'web_sources.json'
    assert hashlib.sha256(copied.read_bytes()).hexdigest() == report['evidence_sha256']
    assert step.state_evidence['web_citations']['identity_state'] == 'unknown'


def test_explicit_input_declarations_exclude_unrelated_history_and_ancestor_files(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    run = make_run('仅处理本地测试文件')
    attach_file(run, workspace, 'history_unrelated.csv', b'private,value\nunused,42\n',
                logical='unrelated.csv', kind='跨轮输入')
    codes = [
        'from pathlib import Path\nassert not Path("unrelated.csv").exists()\n'
        'Path("clean.csv").write_text("value\\n7\\n", encoding="utf-8")\nprint("producer")',
        'from pathlib import Path\nassert not Path("unrelated.csv").exists()\n'
        'assert not Path("clean.csv").exists()\nPath("middle.txt").write_text("separate responsibility")\nprint("isolated")',
        'from pathlib import Path\nassert not Path("unrelated.csv").exists()\n'
        'assert not Path("middle.txt").exists()\n'
        'assert Path("clean.csv").read_text(encoding="utf-8") == "value\\n7\\n"\n'
        'Path("summary.txt").write_text("actual declared ancestor input was read")\nprint("consumed")',
    ]
    prompts = stub_model(monkeypatch, codes)
    plan = {'steps': [
        {'action': '生成测试数据', 'input_files': [], 'output_files': ['clean.csv'], 'depends_on': []},
        {'action': '执行独立检查', 'input_files': [], 'output_files': ['middle.txt'], 'depends_on': [0]},
        {'action': '分析声明的原始输入', 'input_files': ['clean.csv'],
         'output_files': ['summary.txt'], 'depends_on': [1]},
    ]}
    pipeline.execute_run(run, None, workspace, plan, max_steps=3)
    pipeline.finalize_status(run)
    assert run.status == runtime.STATUS_COMPLETED, [(s.status, s.error) for s in run.steps]
    assert len(prompts) == 3
    assert [s.inputs for s in run.steps] == [[], [], ['clean.csv']]
    assert all(s.attempts[0].ok for s in run.steps)
    assert all('unrelated.csv' not in s.inputs for s in run.steps)
    assert (workspace / 'artifacts' / 'step3_summary.txt').read_text() == 'actual declared ancestor input was read'


def test_verified_source_quote_allows_real_downstream_delivery(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    run = make_run('查询公开来源并交付逐条来源可复核的摘录报告')
    report = attach_evidence(run, workspace, identity=False)
    code_first = '''import csv
import json
with open("web_sources.json", encoding="utf-8") as stream:
    evidence = json.load(stream)
source = evidence["sources"][0]
quote = source["text"][:80]
assert len(quote) >= 12 and source["sha256"]
with open("factual_claims.csv", "w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=["source_id", "evidence_url", "claim", "quote"])
    writer.writeheader()
    writer.writerow({"source_id": source["source_id"], "evidence_url": source["url"],
        "claim": quote, "quote": quote})
print("actual frozen source excerpt recorded", source["source_id"])
'''
    code_second = '''import csv
from pathlib import Path
with open("factual_claims.csv", encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == 1 and rows[0]["claim"] == rows[0]["quote"]
Path("report.md").write_text("# Public source excerpt\\n\\n" + rows[0]["claim"]
    + "\\n\\nSource: " + rows[0]["evidence_url"], encoding="utf-8")
print("verified excerpt consumed from actual upstream CSV")
'''
    prompts = stub_model(monkeypatch, [code_first, code_second])
    plan = web_research.bind_plan({'steps': [
        {'action': '提取真实来源并核验引用', 'input_files': [],
         'output_files': ['factual_claims.csv'], 'depends_on': []},
        {'action': '整理核验后的来源摘录报告', 'input_files': ['factual_claims.csv'],
         'output_files': ['report.md'], 'depends_on': [0]},
    ]}, report)
    pipeline.execute_run(run, None, workspace, plan, max_steps=2)
    pipeline.finalize_status(run)
    assert run.status == runtime.STATUS_COMPLETED, [(s.status, s.error) for s in run.steps]
    assert len(prompts) == 2 and all(s.n_attempts == 1 and s.attempts[0].ok for s in run.steps)
    gate = run.steps[0].state_evidence['web_citations']
    assert gate['state'] == 'verified' and gate['verified'] == 1 and gate['failed'] == 0
    host_checks = [v for v in run.steps[0].verifications if v.layer == 'host_web']
    assert len(host_checks) == 1 and host_checks[0].passed and host_checks[0].state == 'passed'
    assert 'factual_claims.csv' in run.steps[1].inputs
    assert run.steps[1].started_at_ms >= run.steps[0].ended_at_ms
    delivered = workspace / 'artifacts' / 'step2_report.md'
    assert TEXT in delivered.read_text(encoding='utf-8') and URL in delivered.read_text(encoding='utf-8')
    audit = web_research.audit_files([workspace/'artifacts'/'step1_factual_claims.csv', delivered], report, workspace)
    assert audit['state'] == 'verified' and audit['verified'] == 1


@pytest.mark.parametrize('task', [
    '请核验最近论文。\nname,value\n张三,100\n不要联网，只用上面的数据。',
    'Research latest findings.\nname,salary\nJohn,10000\nThis is confidential. Do not browse.',
])
def test_offline_instruction_after_data_never_calls_outbound_tools(tmp_path, monkeypatch, task):
    def reject_outbound(*_args, **_kwargs):
        pytest.fail('An explicit offline instruction after data must prevent outbound tools')

    monkeypatch.setattr(web_research.web_search, 'capabilities', lambda: {'enabled': True})
    monkeypatch.setattr(web_research.web_search, 'search', reject_outbound)
    monkeypatch.setattr(web_research.web_search, 'extract', reject_outbound)
    monkeypatch.setattr(web_research.web_fetch, 'fetch_url', reject_outbound)
    from skillnet import skill_discovery
    monkeypatch.setattr(skill_discovery, 'discover', reject_outbound)
    report = web_research.collect(task, tmp_path, mode='on', discover_missing=True)
    assert report['enabled'] is False and report['state'] == 'disabled'
    assert report['sources'] == [] and report['attempts'] == []
    assert report['discovery']['candidates'] == []
    assert not (tmp_path / 'artifacts').exists()


def test_current_host_input_supersedes_carried_snapshot_of_same_logical_name(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    run = make_run('继续核验上述公开来源并交付来源摘录')
    attach_file(run, workspace, 'history_previous_web_sources.json',
        b'{"sources":[{"source_id":"old-web","text":"obsolete historical excerpt"}]}',
        logical='web_sources.json', kind='跨轮输入')
    report = attach_evidence(run, workspace, identity=False)
    code = '''import csv
import json
from pathlib import Path
with open("web_sources.json", encoding="utf-8") as stream:
    evidence = json.load(stream)
source = evidence["sources"][0]
assert source["source_id"] == "web-01"
assert "obsolete historical excerpt" not in json.dumps(evidence)
assert not Path("history_previous_web_sources.json").exists()
with open("factual_claims.csv", "w", encoding="utf-8", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=["source_id", "evidence_url", "claim", "quote"])
    writer.writeheader()
    writer.writerow({"source_id": source["source_id"], "evidence_url": source["url"],
        "claim": source["text"], "quote": source["text"]})
print("only the current host evidence was mounted and read")
'''
    prompts = stub_model(monkeypatch, [code])
    plan = web_research.bind_plan({'steps': [{'action': '核验本轮真实来源',
        'input_files': [], 'output_files': ['factual_claims.csv'], 'depends_on': []}]}, report)
    pipeline.execute_run(run, None, workspace, plan, max_steps=1)
    pipeline.finalize_status(run)
    step = run.steps[0]
    assert run.status == runtime.STATUS_COMPLETED, (step.status, step.error)
    assert len(prompts) == 1 and step.n_attempts == 1 and step.attempts[0].ok
    assert not step.state_evidence.get('input_conflicts')
    assert [(a['name'], a['sha256']) for a in step.input_artifacts] == [
        ('web_sources.json', report['evidence_sha256'])]
    assert step.state_evidence['web_citations']['state'] == 'verified'
    assert (workspace / 'artifacts' / 'step1_factual_claims.csv').is_file()


def test_multiple_current_host_inputs_remain_ambiguous_despite_carried_snapshot(tmp_path, monkeypatch):
    workspace = tmp_path / 'workspace'
    run = make_run('继续核验上述公开来源')
    attach_file(run, workspace, 'history_previous_web_sources.json', b'{"sources":[]}',
        logical='web_sources.json', kind='跨轮输入')
    report = attach_evidence(run, workspace, identity=False)
    attach_file(run, workspace, 'another_current_web_sources.json',
        b'{"sources":[],"marker":"second current version"}', logical='web_sources.json')
    prompts = stub_model(monkeypatch, [])
    plan = web_research.bind_plan({'steps': [{'action': '读取本轮真实来源',
        'input_files': [], 'output_files': ['claims.csv'], 'depends_on': []}]}, report)
    pipeline.execute_run(run, None, workspace, plan, max_steps=1)
    pipeline.finalize_status(run)
    step = run.steps[0]
    assert run.status == runtime.STATUS_FAILED and step.status == runtime.STEP_FAILED
    assert not prompts and step.n_attempts == 0
    conflict = step.state_evidence['input_conflicts']
    assert len(conflict) == 1 and conflict[0]['logical_name'] == 'web_sources.json'
    assert {a['name'] for a in conflict[0]['candidates']} == {
        'web_sources.json', 'another_current_web_sources.json'}
    assert all(a['source_run_id'] == run.run_id for a in conflict[0]['candidates'])
