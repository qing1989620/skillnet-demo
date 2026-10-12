"""The research evidence must come from executed programs and an independent oracle."""
import json

from tools.capability_probe_lab import behavioral_comparisons, digest, fixtures, run_lab


def test_probe_experiment_executes_and_exposes_gate_limit(tmp_path):
    report = run_lab(tmp_path / 'evidence.json', tmp_path / 'lab')
    before, after = (report['summary'][arm] for arm in ('unconditional', 'contract_gate'))
    assert before['code_calls'] == 33
    assert before['invalid_input_outputs'] > 0
    assert after['code_calls'] == 6
    assert after['invalid_inputs_executed'] == after['invalid_input_outputs'] == 0
    assert after['valid_false_blocks'] == 0
    assert after['unknown_blocked'] == 3
    assert all(item['matched'] for item in report['admissions'])

    # A valid input can still induce a numerically wrong result. File existence
    # passes, but the independent oracle catches the boundary comparator bug.
    bug = next(r for r in report['records'] if r['arm']=='contract_gate'
        and r['probe']=='threshold_boundary' and r['implementation']=='csv-threshold-gt-bug')
    assert bug['executed'] is True and bug['execution_ok'] is True
    assert bug['post']['state'] == 'passed'
    assert bug['independent']['state'] == 'failed'
    assert bug['output'] != bug['independent']['expected']
    assert bug['output_sha256']
    assert bug['executed_code_sha256'] == report['protocol']['executed_code_sha256'][bug['implementation']]
    assert (tmp_path/'lab'/'threshold_boundary'/'csv-threshold-gt-bug'/'contract_gate'/'main.py').is_file()

    frozen = json.loads((tmp_path/'lab'/'preregistered-protocol.json').read_text(encoding='utf-8'))
    assert digest(frozen['protocol']) == report['protocol_sha256'] == frozen['protocol_sha256']
    assert all(r['started_at_us'] > report['protocol']['preregistered_at_us']
               for r in report['records'] if r['executed'])
    saved = json.loads((tmp_path/'evidence.json').read_text(encoding='utf-8'))
    recorded_digest = saved.pop('report_sha256')
    assert digest(saved) == recorded_digest
    assert report['reward_applied'] is False


def test_no_observation_cannot_establish_behavioral_agreement():
    comparisons = behavioral_comparisons([], fixtures())
    assert comparisons and all(c['status']=='insufficient_evidence' for c in comparisons)
    assert all(not c['observed_probes'] for c in comparisons)
