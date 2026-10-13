"""Bounded planning over declared, finite Boolean facts.

This module never executes a skill or certifies that its declared effects occur.
It answers a narrower question: which declared operator sequence reaches the
joint goal under closed-world, add/delete semantics? Runtime observations must
replace these assumptions before a resulting plan is treated as evidence.

``plan_found`` is cost optimal among declared plans within ``max_depth``.
``unreachable`` is returned only after the entire finite reachable state set is
closed, including transitions at the depth boundary. A truncated search is
``unknown``. Diagnostic fact unions and nearest-state gaps are not capability
proofs, causal estimates, or a globally minimal set of missing skills.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

VERSION = 'declared-capability-frontier-v1'
MAX_OPERATORS = 128
MAX_FACTS = 128
MAX_FACT_REFERENCES = 4096
MAX_NAME = 128
MAX_DEPTH = 64
MAX_STATES = 16_384
MAX_COST = 1_000_000_000_000
MAX_METADATA_NODES = 128
MAX_METADATA_DEPTH = 6


@dataclass(frozen=True)
class _Operator:
    id: str
    requires: frozenset[str]
    adds: frozenset[str]
    deletes: frozenset[str]
    cost: Fraction


@dataclass
class _Label:
    state: frozenset[str]
    cost: Fraction
    depth: int
    path: tuple[str, ...]
    active: bool = True


def _name(value: Any) -> bool:
    # Facts are opaque identifiers, never expressions, paths, or Python code.
    return (type(value) is str and 0 < len(value) <= MAX_NAME
            and all(c.isalnum() or c in '_.:/-' for c in value))


def _facts(value: Any, where: str) -> frozenset[str]:
    if type(value) is not list or len(value) > MAX_FACTS:
        raise ValueError(f'{where} must be a list of at most {MAX_FACTS} fact identifiers')
    if not all(_name(fact) for fact in value):
        raise ValueError(f'{where} contains an invalid fact identifier')
    return frozenset(value)


def _cost(value: Any) -> Fraction:
    if type(value) not in (int, float):
        raise ValueError('operator cost must be a finite nonnegative JSON number, excluding booleans')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('operator cost must be finite')
    if not 0 <= value <= MAX_COST:
        raise ValueError(f'operator cost must be between 0 and {MAX_COST}')
    # Exact arithmetic on the supplied decimal spelling avoids both floating
    # point tie drift and Decimal-context rounding of very small positive costs.
    return Fraction(str(value))


def _metadata(value: Any) -> None:
    """Accept bounded JSON only; no retained aliases, callbacks, or cycles."""
    nodes = 0
    ancestors: set[int] = set()

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_METADATA_NODES or depth > MAX_METADATA_DEPTH:
            raise ValueError('operator metadata exceeds the bounded JSON domain')
        if item is None or type(item) is bool:
            return
        if type(item) is str:
            if len(item) > 512:
                raise ValueError('operator metadata string is too long')
            return
        if type(item) is int:
            if item.bit_length() > 128:
                raise ValueError('operator metadata integer is too large')
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError('operator metadata numbers must be finite')
            return
        if type(item) not in (dict, list) or len(item) > 64:
            raise ValueError('operator metadata must contain bounded JSON values')
        identity = id(item)
        if identity in ancestors:
            raise ValueError('operator metadata must not contain cycles')
        ancestors.add(identity)
        try:
            if type(item) is dict:
                for key, child in item.items():
                    if type(key) is not str or not 0 < len(key) <= 128:
                        raise ValueError('operator metadata keys must be bounded nonempty strings')
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
        finally:
            ancestors.remove(identity)

    visit(value, 0)


def _validate(initial: Any, goals: Any, operators: Any, max_depth: Any,
              max_states: Any) -> tuple[frozenset[str], frozenset[str], list[_Operator], frozenset[str]]:
    if type(max_depth) is not int or not 0 <= max_depth <= MAX_DEPTH:
        raise ValueError(f'max_depth must be an integer between 0 and {MAX_DEPTH}')
    if type(max_states) is not int or not 1 <= max_states <= MAX_STATES:
        raise ValueError(f'max_states must be an integer between 1 and {MAX_STATES}')
    initial_set = _facts(initial, 'initial')
    goal_set = _facts(goals, 'goals')
    if type(operators) is not list or len(operators) > MAX_OPERATORS:
        raise ValueError(f'operators must be a list of at most {MAX_OPERATORS} operator objects')
    parsed: list[_Operator] = []
    ids: set[str] = set()
    universe = set(initial_set | goal_set)
    references = len(initial) + len(goals)
    required = {'id', 'requires', 'adds', 'deletes', 'cost'}
    for row in operators:
        if (type(row) is not dict or len(row) not in (5, 6)
                or not all(type(key) is str for key in row)
                or not required <= row.keys() or row.keys() - required - {'metadata'}):
            raise ValueError('operator must have id, requires, adds, deletes, cost, and optional metadata only')
        if not _name(row['id']) or row['id'] in ids:
            raise ValueError('operator ids must be valid and unique')
        ids.add(row['id'])
        requires = _facts(row['requires'], f"{row['id']}.requires")
        adds = _facts(row['adds'], f"{row['id']}.adds")
        deletes = _facts(row['deletes'], f"{row['id']}.deletes")
        if adds & deletes:
            raise ValueError('operator adds and deletes must not overlap')
        references += len(row['requires']) + len(row['adds']) + len(row['deletes'])
        if references > MAX_FACT_REFERENCES:
            raise ValueError('total fact references exceed the bounded input domain')
        universe.update(requires | adds | deletes)
        if len(universe) > MAX_FACTS:
            raise ValueError(f'the declared fact universe exceeds {MAX_FACTS} identifiers')
        cost = _cost(row['cost'])
        if 'metadata' in row:
            _metadata(row['metadata'])
        parsed.append(_Operator(row['id'], requires, adds, deletes, cost))
    if len(universe) > MAX_FACTS:
        raise ValueError(f'the declared fact universe exceeds {MAX_FACTS} identifiers')
    return initial_set, goal_set, sorted(parsed, key=lambda op: op.id), frozenset(universe)


def _number(value: Fraction) -> int | float:
    return value.numerator if value.denominator == 1 else float(value)


def _base(max_depth: Any, max_states: Any) -> dict[str, Any]:
    return {
        'version': VERSION,
        'status': 'unknown',
        'plan': [],
        'cost': None,
        'initial': [],
        'goals': [],
        'missing_goals': [],
        'reachable_facts': [],
        'frontier': [],
        'explored': 0,
        'limits': {
            'max_depth': max_depth if type(max_depth) is int and 0 <= max_depth <= MAX_DEPTH else None,
            'max_states': max_states if type(max_states) is int and 1 <= max_states <= MAX_STATES else None,
            'state_budget_unit': 'accepted nondominated state-depth labels, including initial',
            'hard_max_depth': MAX_DEPTH,
            'hard_max_states': MAX_STATES,
            'hard_max_operators': MAX_OPERATORS,
            'hard_max_facts': MAX_FACTS,
        },
        'boundary': {
            'scope': 'declared_symbolic_closed_world',
            'execution_verified': False,
            'causal_model_learned': False,
            'minimal_capability_proof': False,
            'search_complete': False,
            'optimal_within_depth_bound': False,
            'cutoffs': {'depth': False, 'states': False},
            'frontier_scope': 'nearest missing requirements in one observed symbolic state per operator',
            'missing_goals_scope': 'goals missing in one nearest observed symbolic state; not the fact union',
            'statement': 'Declared transitions are hypotheses. This result is not evidence of real skill effects.',
        },
    }


def plan(initial: list[str], goals: list[str], operators: list[dict], *,
         max_depth: int = 8, max_states: int = 4096) -> dict[str, Any]:
    """Find a lowest-cost declared plan within a bounded number of steps.

    An operator applies iff all ``requires`` hold, producing
    ``(state - deletes) | adds``. Missing facts are false only in this finite
    declared model. Costs must be finite nonnegative JSON numbers <= 10**12.
    Optional ``metadata`` is bounded JSON and has no execution semantics.

    State-depth Pareto labels preserve a more expensive but shorter route that
    may be necessary under a depth limit. The state budget counts accepted
    labels, including labels later dominated; ``explored`` counts expanded
    active labels. A budget cutoff returns ``unknown``, never ``unreachable``.
    """
    result = _base(max_depth, max_states)
    try:
        start, target, actions, universe = _validate(initial, goals, operators, max_depth, max_states)
    except (ValueError, OverflowError) as exc:
        result['reason'] = 'invalid_input'
        result['validation_errors'] = [str(exc)]
        return result

    result.update(initial=sorted(start), goals=sorted(target))
    result['boundary']['declared_facts'] = sorted(universe)
    initial_label = _Label(start, Fraction(0), 0, ())
    labels: dict[frozenset[str], list[_Label]] = {start: [initial_label]}
    reached: set[frozenset[str]] = {start}
    reached_facts = set(start)
    frontier: dict[str, tuple[str, ...]] = {}
    depth_boundary: set[frozenset[str]] = set()
    nearest = initial_label
    accepted = 1
    serial = 0
    queue: list[tuple[Fraction, int, tuple[str, ...], int, _Label]] = [
        (Fraction(0), 0, (), serial, initial_label)
    ]

    def observe(label: _Label) -> None:
        nonlocal nearest
        reached.add(label.state)
        reached_facts.update(label.state)
        key = (len(target - label.state), label.cost, label.depth, tuple(sorted(label.state)), label.path)
        previous = (len(target - nearest.state), nearest.cost, nearest.depth,
                    tuple(sorted(nearest.state)), nearest.path)
        if key < previous:
            nearest = label
        for action in actions:
            missing = tuple(sorted(action.requires - label.state))
            old = frontier.get(action.id)
            if old is None or (len(missing), missing) < (len(old), old):
                frontier[action.id] = missing

    observe(initial_label)

    def finish(status: str, reason: str, winner: _Label | None = None) -> dict[str, Any]:
        result.update(
            status=status,
            reason=reason,
            plan=list(winner.path) if winner is not None else [],
            cost=_number(winner.cost) if winner is not None else None,
            missing_goals=sorted(target - nearest.state),
            reachable_facts=sorted(reached_facts),
            frontier=[{'operator': op.id, 'missing_requirements': list(frontier[op.id])}
                      for op in actions if frontier[op.id]],
        )
        result['limits']['accepted_labels'] = accepted
        result['boundary']['observed_symbolic_states'] = len(reached)
        result['boundary']['known_symbolic_goal_state'] = not bool(target - nearest.state)
        result['boundary']['search_complete'] = status == 'unreachable'
        result['boundary']['optimal_within_depth_bound'] = status == 'plan_found'
        if status == 'unknown' and not target - nearest.state:
            # A known candidate may still lack a cost-optimality proof after a
            # state-budget cutoff. Do not put it in the selected plan field.
            result['boundary']['candidate_plan'] = list(nearest.path)
            result['boundary']['candidate_cost'] = _number(nearest.cost)
        return result

    while queue:
        _, _, _, _, current = heapq.heappop(queue)
        if not current.active:
            continue
        if target <= current.state:
            return finish('plan_found', 'declared_goal_reached', current)
        result['explored'] += 1
        if current.depth == max_depth:
            depth_boundary.add(current.state)
            continue
        for action in actions:
            if not action.requires <= current.state:
                continue
            state = (current.state - action.deletes) | action.adds
            cost = current.cost + action.cost
            depth = current.depth + 1
            old_labels = labels.get(state, [])
            if any(old.active and old.cost <= cost and old.depth <= depth for old in old_labels):
                continue
            if accepted >= max_states:
                result['boundary']['cutoffs']['states'] = True
                return finish('unknown', 'state_budget_exhausted')
            for old in old_labels:
                if old.active and cost <= old.cost and depth <= old.depth:
                    old.active = False
            label = _Label(state, cost, depth, current.path + (action.id,))
            labels[state] = [old for old in old_labels if old.active] + [label]
            accepted += 1
            serial += 1
            observe(label)
            heapq.heappush(queue, (cost, depth, label.path, serial, label))

    # Cost dominance alone cannot prove state-set closure at the depth limit.
    # Recheck every applicable transition there against all reached states,
    # including states reached later via a shorter route. Self-loops and cycles
    # within that closed set do not manufacture a false depth cutoff.
    for state in depth_boundary:
        for action in actions:
            if action.requires <= state and ((state - action.deletes) | action.adds) not in reached:
                result['boundary']['cutoffs']['depth'] = True
                return finish('unknown', 'depth_limit_exhausted')
    return finish('unreachable', 'finite_declared_state_space_exhausted')
