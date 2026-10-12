"""Finite symbolic planning is deliberately weaker than execution evidence."""
import copy
import itertools
import json
import math
import random
from fractions import Fraction

import pytest

from skillnet.frontier import MAX_FACTS, MAX_STATES, VERSION, plan


def op(identity, requires=(), adds=(), deletes=(), cost=1, **extra):
    return dict(id=identity, requires=list(requires), adds=list(adds),
                deletes=list(deletes), cost=cost, **extra)


def replay(initial, operators, sequence):
    """Independent contract interpreter for selected plans, not runtime proof."""
    state = set(initial)
    actions = {item['id']: item for item in operators}
    cost = Fraction(0)
    for identity in sequence:
        action = actions[identity]
        assert set(action['requires']) <= state
        state.difference_update(action['deletes'])
        state.update(action['adds'])
        cost += Fraction(str(action['cost']))
    return state, cost


def test_composition_cost_and_explicit_evidence_boundary():
    actions = [op('extract', ['source'], ['table'], cost=2),
               op('verify', ['table'], ['verified'], cost=3),
               op('report', ['verified'], ['report'], cost=1)]
    result = plan(['source'], ['report'], actions)
    assert result['version'] == VERSION
    assert result['status'] == 'plan_found'
    assert result['plan'] == ['extract', 'verify', 'report']
    assert result['cost'] == 6
    assert 'report' in replay(['source'], actions, result['plan'])[0]
    assert result['missing_goals'] == []
    assert result['boundary']['scope'] == 'declared_symbolic_closed_world'
    assert result['boundary']['execution_verified'] is False
    assert result['boundary']['causal_model_learned'] is False
    assert result['boundary']['minimal_capability_proof'] is False
    assert result['boundary']['optimal_within_depth_bound'] is True


def test_joint_goal_cannot_be_inferred_from_fact_union():
    actions = [op('a', ['seed'], ['a'], ['b'], 0),
               op('b', ['seed'], ['b'], ['a'], 0),
               op('combine', ['a', 'b'], ['goal'])]
    result = plan(['seed'], ['a', 'b'], actions)
    assert result['status'] == 'unreachable'
    assert {'a', 'b'} <= set(result['reachable_facts'])
    assert result['missing_goals']  # Missing in a single state, despite the union.
    assert result['boundary']['known_symbolic_goal_state'] is False
    assert result['frontier'] == [{'operator': 'combine', 'missing_requirements': ['a']}]


def test_delete_effect_requires_rebuilding_dependency():
    actions = [op('clean', ['raw'], ['clean'], ['raw']),
               op('raw_report', ['raw', 'clean'], ['report']),
               op('restore', ['clean'], ['raw'], cost=5)]
    result = plan(['raw'], ['report'], actions)
    assert result['plan'] == ['clean', 'restore', 'raw_report']
    assert result['cost'] == 7


def test_dijkstra_finds_cheaper_longer_plan():
    actions = [op('direct', ['source'], ['goal'], cost=8),
               op('first', ['source'], ['middle'], cost=2),
               op('second', ['middle'], ['goal'], cost=3)]
    result = plan(['source'], ['goal'], actions)
    assert result['plan'] == ['first', 'second']
    assert result['cost'] == 5


def test_depth_pareto_label_retains_expensive_shorter_route():
    actions = [op('a1', ['start'], ['one'], ['start'], 0),
               op('a2', ['one'], ['two'], ['one'], 0),
               op('a3', ['two'], ['hub'], ['two'], 0),
               op('z_short', ['start'], ['hub'], ['start'], 5),
               op('tail', ['hub'], ['tail'], ['hub'], 0),
               op('finish', ['tail'], ['goal'], ['tail'], 0)]
    result = plan(['start'], ['goal'], actions, max_depth=3)
    assert result['status'] == 'plan_found'
    assert result['plan'] == ['z_short', 'tail', 'finish']
    assert result['cost'] == 5
    assert result['boundary']['optimal_within_depth_bound'] is True


def test_fraction_costs_do_not_introduce_float_tie_drift():
    actions = [op('a_first', ['start'], ['middle'], cost=0.1),
               op('b_second', ['middle'], ['goal'], cost=0.2),
               op('z_direct', ['start'], ['goal'], cost=0.30000000000000004)]
    result = plan(['start'], ['goal'], actions)
    assert result['plan'] == ['a_first', 'b_second']
    assert result['cost'] == 0.3


def test_very_small_positive_cost_is_not_rounded_to_zero():
    actions = [op('a_costly', ['start'], ['goal'], cost=1e-300),
               op('z_free', ['start'], ['goal'], cost=0)]
    result = plan(['start'], ['goal'], actions)
    assert result['plan'] == ['z_free']
    assert result['cost'] == 0


def test_empty_goal_is_zero_step_success():
    result = plan([], [], [], max_depth=0, max_states=1)
    assert result['status'] == 'plan_found'
    assert result['plan'] == []
    assert result['cost'] == 0
    assert result['explored'] == 0


def test_initially_satisfied_joint_goal_needs_no_operator():
    result = plan(['a', 'b'], ['a', 'b'], [], max_states=1)
    assert result['status'] == 'plan_found'
    assert result['plan'] == []


def test_unreachable_requires_finite_closure():
    actions = [op('available', ['source'], ['table']),
               op('blocked', ['missing'], ['goal'])]
    result = plan(['source'], ['goal'], actions)
    assert result['status'] == 'unreachable'
    assert result['reason'] == 'finite_declared_state_space_exhausted'
    assert result['boundary']['search_complete'] is True
    assert result['boundary']['cutoffs'] == {'depth': False, 'states': False}
    assert result['frontier'] == [{'operator': 'blocked', 'missing_requirements': ['missing']}]


def test_depth_cutoff_is_unknown_when_new_states_are_left():
    actions = [op('one', ['source'], ['middle']), op('two', ['middle'], ['goal'])]
    result = plan(['source'], ['goal'], actions, max_depth=1)
    assert result['status'] == 'unknown'
    assert result['reason'] == 'depth_limit_exhausted'
    assert result['boundary']['cutoffs'] == {'depth': True, 'states': False}
    assert result['boundary']['search_complete'] is False
    assert result['plan'] == [] and result['cost'] is None
    assert 'goal' not in result['reachable_facts']


def test_zero_depth_does_not_claim_impossible_when_applicable_action_exists():
    result = plan(['source'], ['goal'], [op('finish', ['source'], ['goal'])], max_depth=0)
    assert result['status'] == 'unknown'


def test_depth_boundary_with_only_self_loops_is_closed():
    actions = [op('noop', ['source'], ['source'], cost=0),
               op('blocked', ['missing'], ['goal'])]
    result = plan(['source'], ['goal'], actions, max_depth=0)
    assert result['status'] == 'unreachable'
    assert result['limits']['accepted_labels'] == 1


def test_zero_cost_cycles_do_not_exhaust_budget_or_fake_depth_cutoff():
    actions = [op('forward', ['a'], ['b'], ['a'], 0),
               op('backward', ['b'], ['a'], ['b'], 0)]
    result = plan(['a'], ['goal'], actions, max_depth=1, max_states=2)
    assert result['status'] == 'unreachable'
    assert result['explored'] == 2
    assert result['limits']['accepted_labels'] == 2


def test_later_discovered_boundary_successor_does_not_leave_spurious_cutoff():
    actions = [op('a1', ['start'], ['a1'], ['start'], 0),
               op('a2', ['a1'], ['a2'], ['a1'], 0),
               op('boundary', ['a2'], ['b'], ['a2'], 100),
               op('z1', ['start'], ['z'], ['start'], 5),
               op('z2', ['z'], ['b'], ['z'], 0)]
    result = plan(['start'], ['impossible'], actions, max_depth=2)
    assert result['status'] == 'unreachable'
    assert result['boundary']['cutoffs']['depth'] is False


def test_state_budget_cutoff_is_unknown():
    actions = [op('one', ['source'], ['middle']), op('two', ['middle'], ['goal'])]
    result = plan(['source'], ['goal'], actions, max_states=2)
    assert result['status'] == 'unknown'
    assert result['reason'] == 'state_budget_exhausted'
    assert result['limits']['accepted_labels'] == 2
    assert result['boundary']['cutoffs']['states'] is True


def test_state_budget_can_exactly_cover_a_goal():
    result = plan(['source'], ['goal'], [op('finish', ['source'], ['goal'])], max_states=2)
    assert result['status'] == 'plan_found'


def test_candidate_after_cutoff_is_not_exposed_as_selected_optimal_plan():
    actions = [op('a_goal', ['source'], ['goal'], cost=100),
               op('b_middle', ['source'], ['middle'], cost=1)]
    result = plan(['source'], ['goal'], actions, max_states=2)
    assert result['status'] == 'unknown'
    assert result['plan'] == [] and result['cost'] is None
    assert result['missing_goals'] == []
    assert result['boundary']['candidate_plan'] == ['a_goal']
    assert result['boundary']['candidate_cost'] == 100
    assert result['boundary']['optimal_within_depth_bound'] is False


def test_ties_and_frontier_are_deterministic_under_operator_permutations():
    actions = [op('z', ['seed'], ['goal'], cost=1),
               op('a', ['seed'], ['goal'], cost=1),
               op('blocked', ['unknown'], ['elsewhere'])]
    outputs = [plan(['seed'], ['goal'], list(order)) for order in itertools.permutations(actions)]
    assert all(output == outputs[0] for output in outputs)
    assert outputs[0]['plan'] == ['a']


def test_inputs_outputs_and_optional_metadata_do_not_alias():
    actions = [op('finish', ['source'], ['goal'], metadata={'note': ['symbolic']})]
    initial, goals = ['source'], ['goal']
    original = copy.deepcopy((initial, goals, actions))
    result = plan(initial, goals, actions)
    assert (initial, goals, actions) == original
    result['plan'].append('corruption')
    result['initial'].clear()
    result['boundary']['declared_facts'].clear()
    actions[0]['metadata']['note'].append('later mutation')
    again = plan(initial, goals, actions)
    assert again['plan'] == ['finish']
    assert again['initial'] == ['source']
    assert again['boundary']['declared_facts'] == ['goal', 'source']


def test_duplicate_facts_normalize_as_sets_without_mutating_input():
    result = plan(['source', 'source'], ['goal', 'goal'],
                  [op('finish', ['source', 'source'], ['goal', 'goal'])])
    assert result['status'] == 'plan_found'
    assert result['initial'] == ['source']
    assert result['goals'] == ['goal']


@pytest.mark.parametrize('initial,goals,actions,kwargs', [
    ('source', ['goal'], [], {}),
    ([], 'goal', [], {}),
    ([], [], {}, {}),
    (None, [], [], {}),
    ([], None, [], {}),
    ([], [], None, {}),
    ([True], [], [], {}),
    ([1], [], [], {}),
    ([None], [], [], {}),
    ([''], [], [], {}),
    ([' spaced'], [], [], {}),
    (['has space'], [], [], {}),
    (['line\nbreak'], [], [], {}),
    (['hidden\u200bcharacter'], [], [], {}),
    (['x' * 129], [], [], {}),
    (["__import__('os').system('bad')"], [], [], {}),
    ([], [], [None], {}),
    ([], [], [[]], {}),
    ([], [], [dict(id='incomplete')], {}),
    ([], [], [op('same'), op('same')], {}),
    ([], [], [op('')], {}),
    ([], [], [op('bad id')], {}),
    ([], [], [op('bad', cost=True)], {}),
    ([], [], [op('bad', cost=False)], {}),
    ([], [], [op('bad', cost='1')], {}),
    ([], [], [op('bad', cost=None)], {}),
    ([], [], [op('bad', cost=-1)], {}),
    ([], [], [op('bad', cost=math.nan)], {}),
    ([], [], [op('bad', cost=math.inf)], {}),
    ([], [], [op('bad', cost=-math.inf)], {}),
    ([], [], [op('bad', cost=10**500)], {}),
    ([], [], [op('bad', adds=['x'], deletes=['x'])], {}),
    ([], [], [dict(op('bad'), requires='fact')], {}),
    ([], [], [dict(op('bad'), adds={'fact'})], {}),
    ([], [], [dict(op('bad'), deletes=None)], {}),
    ([], [], [op('bad', script='do not execute')], {}),
    ([], [], [dict(op('bad'), **{f'extra{x}': 1 for x in range(1000)})], {}),
    ([], [], [op('bad', metadata={'callback': lambda: None})], {}),
    ([], [], [op('bad', metadata={'number': math.nan})], {}),
    ([], [], [op('bad', metadata={'number': math.inf})], {}),
    ([], [], [op('bad', metadata={'number': 10**100})], {}),
    ([], [], [op('bad', metadata={1: 'invalid key'})], {}),
    ([], [], [op('bad', metadata={'long': 'x' * 513})], {}),
    ([], [], [op('bad', metadata=list(range(65)))], {}),
    ([], [], [], {'max_depth': True}),
    ([], [], [], {'max_depth': -1}),
    ([], [], [], {'max_depth': 65}),
    ([], [], [], {'max_depth': 1.5}),
    ([], [], [], {'max_states': True}),
    ([], [], [], {'max_states': 0}),
    ([], [], [], {'max_states': MAX_STATES + 1}),
    ([], [], [], {'max_states': '4096'}),
])
def test_invalid_input_is_unknown_never_exception(initial, goals, actions, kwargs):
    result = plan(initial, goals, actions, **kwargs)
    assert result['status'] == 'unknown'
    assert result['reason'] == 'invalid_input'
    assert result['validation_errors']
    assert result['explored'] == 0
    assert result['plan'] == [] and result['cost'] is None
    assert result['boundary']['execution_verified'] is False


def test_oversized_fact_universe_across_otherwise_valid_lists():
    result = plan([f'i{x}' for x in range(MAX_FACTS)], ['new'], [])
    assert result['reason'] == 'invalid_input'


def test_oversized_operator_list_and_fact_reference_count():
    too_many = [op(f'o{x}') for x in range(129)]
    assert plan([], [], too_many)['reason'] == 'invalid_input'
    facts = [f'f{x}' for x in range(128)]
    redundant = [op(f'o{x}', facts, facts) for x in range(17)]
    assert plan([], [], redundant)['reason'] == 'invalid_input'


def test_metadata_cycle_and_depth_are_rejected():
    cycle = []
    cycle.append(cycle)
    assert plan([], [], [op('bad', metadata=cycle)])['reason'] == 'invalid_input'
    deep = None
    for _ in range(8):
        deep = [deep]
    assert plan([], [], [op('bad', metadata=deep)])['reason'] == 'invalid_input'


def test_invalid_huge_limits_are_not_reflected_into_json_output():
    huge = 10**5000
    for kwargs in ({'max_depth': huge}, {'max_states': huge}):
        result = plan([], [], [], **kwargs)
        assert result['reason'] == 'invalid_input'
        assert len(json.dumps(result)) < 3000


def test_operator_keys_must_be_plain_strings():
    row = op('bad')
    row[1] = 'extra'
    assert plan([], [], [row])['reason'] == 'invalid_input'


def test_operator_metadata_is_not_an_execution_instruction(tmp_path):
    target = tmp_path / 'must-not-exist'
    actions = [op('finish', adds=['goal'], metadata={'script': f'open({str(target)!r}, "w")'})]
    result = plan([], ['goal'], actions)
    assert result['status'] == 'plan_found'
    assert not target.exists()


def test_unicode_fact_names_are_opaque_literal_identifiers():
    result = plan(['表格.存在'], ['结果.核验'], [op('核验', ['表格.存在'], ['结果.核验'])])
    assert result['status'] == 'plan_found'
    assert result['plan'] == ['核验']


def _enumerated_depth_oracle(initial, goals, actions, max_depth):
    best = None
    layer = [(set(initial), Fraction(0))]
    for depth in range(max_depth + 1):
        next_layer = []
        for state, cost in layer:
            if set(goals) <= state and (best is None or cost < best):
                best = cost
            if depth == max_depth:
                continue
            for action in actions:
                if set(action['requires']) <= state:
                    child = (state - set(action['deletes'])) | set(action['adds'])
                    next_layer.append((child, cost + Fraction(str(action['cost']))))
        layer = next_layer
    return best


def _complete_reachability_oracle(initial, goals, actions):
    reached = {frozenset(initial)}
    pending = [frozenset(initial)]
    while pending:
        current = pending.pop()
        if set(goals) <= current:
            return True
        for action in actions:
            if set(action['requires']) <= current:
                child = (current - set(action['deletes'])) | set(action['adds'])
                if child not in reached:
                    reached.add(child)
                    pending.append(child)
    return False


def test_seeded_small_models_match_independent_exhaustive_plan_oracle():
    rng = random.Random(149332)
    facts = ['a', 'b', 'c']
    for _ in range(250):
        initial = [fact for fact in facts if rng.randrange(2)]
        goals = [fact for fact in facts if rng.randrange(2)]
        actions = []
        for index in range(rng.randrange(1, 5)):
            requires = [fact for fact in facts if rng.randrange(3) == 0]
            adds, deletes = [], []
            for fact in facts:
                effect = rng.randrange(3)
                if effect == 1:
                    adds.append(fact)
                elif effect == 2:
                    deletes.append(fact)
            actions.append(op(f'op{index}', requires, adds, deletes, rng.randrange(4)))
        depth = rng.randrange(5)
        expected = _enumerated_depth_oracle(initial, goals, actions, depth)
        result = plan(initial, goals, actions, max_depth=depth)
        if expected is not None:
            assert result['status'] == 'plan_found', (initial, goals, actions, result)
            state, cost = replay(initial, actions, result['plan'])
            assert set(goals) <= state
            assert cost == expected
            assert result['cost'] == float(expected)
            assert len(result['plan']) <= depth
        else:
            assert result['status'] in {'unreachable', 'unknown'}
            if result['status'] == 'unreachable':
                assert not _complete_reachability_oracle(initial, goals, actions)
            else:
                assert result['boundary']['cutoffs']['depth'] is True
