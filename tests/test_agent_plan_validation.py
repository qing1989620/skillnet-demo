"""Planning-boundary regressions; bad file predicates get one bounded repair."""
import copy
import json

import pytest

from skillnet import agent
from skillnet.catalog import SkillLibrary


def plan(*, bad=False):
    return {'approach': 'Read frozen host sources, then verify the actual excerpts.',
        'steps': [{'skill': 'manual', 'action': '核验宿主真实来源',
            'input_files': ['web_sources.json'], 'output_files': ['factual_claims.csv'],
            'requires': [{'kind': 'csv_schema', 'file': 'web_sources.json', 'columns': ['sources']}]
                        if bad else [{'kind': 'file_exists', 'file': 'web_sources.json'}],
            'ensures': [{'kind': 'csv_schema', 'file': 'factual_claims.csv',
                         'columns': ['source_id', 'evidence_url', 'claim', 'quote']}],
            'verification': ['逐条回到真实来源，核对引文原文与来源 SHA。']}],
        'risks': ['未核验的来源不能作为事实'], 'artifacts': ['factual_claims.csv']}


def stub_chat(monkeypatch, responses):
    calls = []
    outputs = [json.dumps(response, ensure_ascii=False) for response in responses]

    def chat(messages, **kwargs):
        calls.append((copy.deepcopy(messages), kwargs.copy()))
        if len(calls) > len(outputs):
            pytest.fail('Planning repair exceeded its single retry allowance')
        return outputs[len(calls)-1]

    monkeypatch.setattr(agent, 'chat', chat)
    return calls, outputs


def test_format_errors_identify_json_predicates_in_requires_and_ensures():
    invalid = plan(bad=True)
    invalid['steps'].append({'ensures': [{'kind': 'csv_nonempty', 'file': 'response.json'}]})
    errors = agent._format_contract_errors(invalid)
    assert len(errors) == 2
    assert '步骤1.requires' in errors[0] and 'web_sources.json' in errors[0] and 'csv_schema' in errors[0]
    assert '步骤2.ensures' in errors[1] and 'response.json' in errors[1]
    assert agent._format_contract_errors(plan()) == []


@pytest.mark.parametrize('file', ['table.csv', 'TABLE.CSV', 'nested/table.csv'])
def test_valid_csv_predicates_and_json_file_exists_are_not_weakened(file):
    valid = plan()
    valid['steps'][0]['ensures'][0]['file'] = file
    assert agent._format_contract_errors(valid) == []


def test_error_list_is_bounded_for_oversized_malformed_plan():
    invalid = {'steps': [{'requires': [{'kind': 'csv_schema', 'file': f'{index}.json'}]}
                         for index in range(50)]}
    errors = agent._format_contract_errors(invalid)
    assert len(errors) == 16 and '步骤16.requires' in errors[-1]


def test_one_bounded_replan_preserves_goal_sources_and_necessary_acceptance(monkeypatch):
    broken, fixed = plan(bad=True), plan()
    calls, outputs = stub_chat(monkeypatch, [broken, fixed])
    result = agent.ResearchAgent(SkillLibrary([]), model='test-model').run(
        '核验真实公开来源，禁止把JSON当成CSV', max_steps=2, max_tokens=800)
    assert len(calls) == 2
    initial, repair = calls
    assert initial[1]['role'] == repair[1]['role'] == 'executor'
    assert initial[1]['max_tokens'] == repair[1]['max_tokens'] == 800
    assert initial[1]['model'] == repair[1]['model'] == 'test-model'
    assert repair[0][-2] == {'role': 'assistant', 'content': outputs[0]}
    assert 'web_sources.json' in repair[0][-1]['content']
    assert '保留任务目标、数据与必要验收' in repair[0][-1]['content']
    assert 'JSON不可按CSV验收' in repair[0][-1]['content']
    assert result.response['steps'][0]['input_files'] == broken['steps'][0]['input_files']
    assert result.response['steps'][0]['ensures'] == broken['steps'][0]['ensures']
    assert result.response['steps'][0]['verification'] == broken['steps'][0]['verification']
    assert result.response['steps'][0]['requires'] == fixed['steps'][0]['requires']
    trace = result.response['_plan_repairs']
    assert len(trace) == 1 and trace[0]['errors'] == agent._format_contract_errors(broken)
    assert trace[0]['remaining'] == [] and result.raw == outputs[1]


def test_second_invalid_plan_stays_invalid_without_third_call_or_deleted_checks(monkeypatch):
    broken = plan(bad=True)
    still_broken = copy.deepcopy(broken)
    still_broken['steps'][0]['requires'].append({'kind': 'csv_nonempty', 'file': 'web_sources.json'})
    calls, outputs = stub_chat(monkeypatch, [broken, still_broken])
    result = agent.ResearchAgent(SkillLibrary([])).run('核对来源原文', max_steps=2)
    assert len(calls) == 2 and result.raw == outputs[1]
    assert result.response['steps'][0]['requires'] == still_broken['steps'][0]['requires']
    assert result.response['steps'][0]['verification'] == broken['steps'][0]['verification']
    remaining = result.response['_plan_repairs'][0]['remaining']
    assert remaining == agent._format_contract_errors(still_broken) and len(remaining) == 2


def test_valid_plan_does_not_spend_an_extra_planning_call(monkeypatch):
    valid = plan()
    calls, _ = stub_chat(monkeypatch, [valid])
    result = agent.ResearchAgent(SkillLibrary([])).run('核对引用')
    assert len(calls) == 1 and result.response == valid and '_plan_repairs' not in result.response
