"""Bounded, falsifiable artifact predicates and conservative declared composition.

Declarations are never runtime evidence. ``evaluate`` inspects a single immutable
byte snapshot per supplied logical file. ``composition`` only proves implications
between declarations in a DAG; its frontier is an unsatisfied *declared*
precondition, not proof that an agent lacks a capability.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import stat
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

VERSION = 'skill-state-contract-v1'
MAX_PREDICATES = 32
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 50_000
MAX_COLUMNS = 256
MAX_STEPS = 128
KINDS = frozenset({
    'file_exists', 'csv_schema', 'csv_nonempty', 'csv_no_missing',
    'csv_unique', 'csv_numeric_range', 'csv_disjoint_groups', 'csv_values_in',
    'csv_group_numeric_coverage',
})


def _logical(value: Any) -> bool:
    if not isinstance(value, str) or not value or len(value) > 240 or value != value.strip():
        return False
    if any(ord(c) < 32 or c in '\\:*?"<>|' for c in value):
        return False
    parts = value.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                *(f'LPT{i}' for i in range(1, 10))}
    return all(p not in ('', '.', '..') and p == p.rstrip('. ')
               and p.split('.')[0].upper() not in reserved for p in parts)


def _column(value: Any) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= 256
            and not any(ord(c) < 32 for c in value))


def _decimal(value: Any, *, max_chars: int = 128) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError('numeric bounds must be finite numbers')
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('numeric bounds must be finite numbers')
    text = str(value).strip()
    if not text or len(text) > max_chars:
        raise ValueError('invalid numeric value')
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('invalid numeric value') from exc
    if not number.is_finite():
        raise ValueError('numeric values must be finite')
    return number


def _enum_key(value: str | int, *, max_chars: int = 256) -> tuple[str, Any]:
    """Finite numeric spellings compare by Decimal; other strings compare exactly."""
    if type(value) not in (str, int):
        raise ValueError('enumerated values must be strings or integers, excluding booleans')
    if isinstance(value, str) and (len(value) > max_chars or any(ord(c) < 32 for c in value)):
        raise ValueError('enumerated text exceeds the bounded text domain')
    try:
        return 'number', _decimal(value, max_chars=max_chars)
    except ValueError:
        if isinstance(value, int):
            raise
        return 'text', value


def _validate(spec: Any) -> str | None:
    if not isinstance(spec, dict):
        return 'predicate must be an object'
    kind = spec.get('kind')
    if not isinstance(kind, str) or kind not in KINDS:
        return 'unsupported predicate kind'
    if not _logical(spec.get('file')):
        return 'file must be a safe relative logical name'
    keys = {'kind', 'file'}
    if kind in ('csv_schema', 'csv_no_missing', 'csv_unique'):
        keys.add('columns')
        columns = spec.get('columns')
        if (not isinstance(columns, list) or not 1 <= len(columns) <= MAX_COLUMNS
                or not all(_column(c) for c in columns) or len(set(columns)) != len(columns)):
            return 'columns must be a nonempty unique list of column names'
    if kind == 'csv_schema':
        keys.add('exact')
        if 'exact' in spec and not isinstance(spec['exact'], bool):
            return 'exact must be a boolean'
    if kind == 'csv_numeric_range':
        keys.update({'column', 'min', 'max'})
        if not _column(spec.get('column')):
            return 'column must be a column name'
        if 'min' not in spec and 'max' not in spec:
            return 'at least one numeric bound is required'
        try:
            low = _decimal(spec['min']) if 'min' in spec else None
            high = _decimal(spec['max']) if 'max' in spec else None
            if low is not None and high is not None and low > high:
                return 'min must not exceed max'
        except ValueError as exc:
            return str(exc)
    if kind == 'csv_disjoint_groups':
        keys.update({'entity', 'group'})
        if not _column(spec.get('entity')) or not _column(spec.get('group')):
            return 'entity and group must be column names'
    if kind == 'csv_group_numeric_coverage':
        keys.update({'group', 'column', 'where'})
        if not _column(spec.get('group')) or not _column(spec.get('column')):
            return 'group and column must be column names'
        where = spec.get('where')
        if where is not None and (type(where) is not dict or set(where) != {'column', 'equals'}
                or not _column(where.get('column')) or type(where.get('equals')) is not str
                or len(where['equals']) > 256 or any(ord(c) < 32 for c in where['equals'])):
            return 'where must contain one column and an exact bounded text value'
    if kind == 'csv_values_in':
        keys.update({'column', 'values'})
        values = spec.get('values')
        if not _column(spec.get('column')):
            return 'column must be a column name'
        if not isinstance(values, list) or not 1 <= len(values) <= 64:
            return 'values must be a bounded nonempty list'
        try:
            normalized = [_enum_key(value) for value in values]
            if len(set(normalized)) != len(normalized):
                return 'enumerated values must be distinct after numeric normalization'
        except ValueError as exc:
            return str(exc)
    if set(spec) - keys:
        return 'unsupported predicate fields'
    return None


def _snapshot(path: Any, logical: str) -> dict:
    evidence: dict[str, Any] = {'file': logical}
    try:
        path = Path(path)
        absolute = path.absolute()
        # A supplied mapping is the authority: never join a predicate to a path.
        # Reject indirect filesystem links as well as a linked final component.
        for item in (absolute, *absolute.parents):
            if item.is_symlink() or (hasattr(item, 'is_junction') and item.is_junction()):
                return dict(state='unknown', detail='linked paths are not admissible evidence', evidence=evidence)
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            return dict(state='unknown', detail='mapped artifact is not a regular file', evidence=evidence)
        if before.st_size > MAX_BYTES:
            return dict(state='unknown', detail='artifact exceeds the byte verification limit', evidence=evidence)
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode) or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                return dict(state='unknown', detail='artifact changed before its snapshot', evidence=evidence)
            raw = stream.read(MAX_BYTES + 1)
            after = os.fstat(stream.fileno())
        if (len(raw) > MAX_BYTES or len(raw) != before.st_size
                or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
            return dict(state='unknown', detail='artifact changed or exceeded limits during its snapshot', evidence=evidence)
        evidence.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        return dict(state='passed', detail='complete byte snapshot', evidence=evidence, raw=raw)
    except (OSError, TypeError, ValueError):
        return dict(state='unknown', detail='artifact is absent or cannot be safely read', evidence=evidence)


def _csv(snapshot: dict) -> dict:
    if snapshot['state'] != 'passed':
        return snapshot
    evidence = dict(snapshot['evidence'])
    try:
        reader = csv.reader(io.StringIO(snapshot['raw'].decode('utf-8-sig'), newline=''), strict=True)
        header = next(reader, None)
        if not header or not all(_column(c) for c in header) or len(set(header)) != len(header):
            return dict(state='failed', detail='CSV header is empty, invalid, or duplicated', evidence=evidence)
        if len(header) > MAX_COLUMNS:
            return dict(state='unknown', detail='CSV exceeds the column verification limit', evidence=evidence)
        rows = []
        for row in reader:
            if len(row) != len(header):
                return dict(state='failed', detail=f'CSV record {len(rows) + 2} has an inconsistent width', evidence=evidence)
            if len(rows) >= MAX_ROWS:
                return dict(state='unknown', detail='CSV exceeds the row verification limit', evidence=evidence)
            rows.append(row)
        evidence.update(columns=header, rows=len(rows))
        return dict(state='passed', detail='bounded CSV parsed', evidence=evidence, header=header, rows=rows)
    except csv.Error as exc:
        # The stdlib CSV reader has a process-wide field-size limit. Do not
        # change it for other threads or mistake its resource boundary for a
        # malformed artifact / negative training example.
        if 'field larger than field limit' in str(exc):
            return dict(state='unknown', detail='CSV exceeds the parser field verification limit', evidence=evidence)
        return dict(state='failed', detail='CSV is not strict UTF-8 CSV', evidence=evidence)
    except UnicodeError:
        return dict(state='failed', detail='CSV is not strict UTF-8 CSV', evidence=evidence)


def _required_columns(spec: dict) -> set[str]:
    if spec['kind'] in ('csv_schema', 'csv_no_missing', 'csv_unique'):
        return set(spec['columns'])
    if spec['kind'] in ('csv_numeric_range', 'csv_values_in'):
        return {spec['column']}
    if spec['kind'] == 'csv_disjoint_groups':
        return {spec['entity'], spec['group']}
    if spec['kind'] == 'csv_group_numeric_coverage':
        return {spec['group'], spec['column']} | ({spec['where']['column']} if spec.get('where') else set())
    return set()


def _test(spec: dict, data: dict) -> tuple[str, str, dict]:
    kind = spec['kind']
    if data['state'] != 'passed':
        return data['state'], data['detail'], data['evidence']
    evidence = dict(data['evidence'])
    if kind == 'file_exists':
        return 'passed', 'mapped regular file exists and its complete bytes were hashed', evidence
    header, rows = data['header'], data['rows']
    required = _required_columns(spec)
    missing = sorted(required - set(header))
    if missing:
        evidence['missing_columns'] = missing
        return 'failed', 'required CSV columns are absent', evidence
    indices = {name: i for i, name in enumerate(header)}
    violations: list[int] = []
    total = 0
    if kind == 'csv_schema':
        ok = not spec.get('exact', False) or set(header) == required
        return ('passed' if ok else 'failed', 'CSV column set satisfies schema' if ok else 'CSV has undeclared columns', evidence)
    if kind == 'csv_nonempty':
        return ('passed' if rows else 'failed', 'CSV has data records' if rows else 'CSV has no data records', evidence)
    if kind == 'csv_group_numeric_coverage':
        group_counts: dict[str, int] = {}
        invalid_records = []
        invalid_count = 0
        where = spec.get('where')
        for number, row in enumerate(rows, start=2):
            if where and row[indices[where['column']]] != where['equals']:
                continue
            group = row[indices[spec['group']]]
            group_counts.setdefault(group, 0)
            text = row[indices[spec['column']]].strip()
            if not text:
                continue
            try:
                _decimal(text)
                group_counts[group] += 1
            except ValueError:
                invalid_count += 1
                if len(invalid_records) < 8:
                    invalid_records.append(number)
        empty = sorted(k for k, count in group_counts.items() if count == 0)
        evidence.update(groups=len(group_counts), groups_without_numeric=len(empty),
                        empty_groups=[k[:256] for k in empty[:8]],
                        invalid_numeric_records=invalid_count, violating_records=invalid_records)
        ok = bool(group_counts) and not empty and not invalid_count
        return ('passed' if ok else 'failed',
                'every selected group has finite numeric coverage and every nonblank value is finite'
                if ok else 'selected groups are absent, contain no numeric values, or contain invalid values', evidence)
    seen: set[tuple[str, ...]] = set()
    groups: dict[str, str] = {}
    low = _decimal(spec['min']) if 'min' in spec else None
    high = _decimal(spec['max']) if 'max' in spec else None
    values = {_enum_key(value) for value in spec['values']} if kind == 'csv_values_in' else set()
    for row_number, row in enumerate(rows, start=2):
        bad = False
        if kind == 'csv_no_missing':
            bad = any(not row[indices[c]].strip() for c in spec['columns'])
        elif kind == 'csv_unique':
            key = tuple(row[indices[c]] for c in spec['columns'])
            bad = key in seen
            seen.add(key)
        elif kind == 'csv_numeric_range':
            try:
                value = _decimal(row[indices[spec['column']]], max_chars=MAX_BYTES)
                bad = (low is not None and value < low) or (high is not None and value > high)
            except ValueError:
                bad = True
        elif kind == 'csv_disjoint_groups':
            entity, group = row[indices[spec['entity']]], row[indices[spec['group']]]
            bad = entity in groups and groups[entity] != group
            groups.setdefault(entity, group)
        elif kind == 'csv_values_in':
            try:
                bad = _enum_key(row[indices[spec['column']]], max_chars=MAX_BYTES) not in values
            except ValueError:
                bad = True
        if bad:
            total += 1
            if len(violations) < 8:
                violations.append(row_number)
    evidence.update(violation_count=total, violating_records=violations)
    return ('failed' if total else 'passed', 'predicate has observed counterexamples' if total else 'predicate holds for every inspected record', evidence)


def evaluate(predicates: list[dict], files: dict[str, Path]) -> dict:
    """Verify artifact predicates; missing evidence and resource limits fail closed.

    Empty tables satisfy universal constraints (unique/no-missing/range/disjoint).
    Use ``csv_nonempty`` separately when a nonempty result is required. Values are
    exact CSV cells for identity; only missingness/numeric parsing trims spaces.
    ``csv_values_in`` compares finite numeric spellings by exact Decimal value
    (``0``, ``0.0``, and ``0e0`` agree), and other strings by exact text. A list
    ``[0, 1]`` therefore enforces binary labels, unlike a numeric interval.
    """
    result: dict[str, Any] = {'version': VERSION, 'state': 'unknown', 'checks': []}
    if not isinstance(predicates, list) or not 1 <= len(predicates) <= MAX_PREDICATES:
        result['detail'] = 'between 1 and 32 predicates are required'
        return result
    if not isinstance(files, dict):
        result['detail'] = 'files must be a logical-name mapping'
        return result
    # Process one logical artifact at a time, so 32 distinct predicates cannot
    # retain 32 complete byte buffers and CSV matrices simultaneously. Preserve
    # caller order in the report, even when predicates for a file are interleaved.
    grouped: dict[str, list[tuple[int, dict]]] = {}
    result['checks'] = [None] * len(predicates)
    for index, spec in enumerate(predicates):
        error = _validate(spec)
        if error:
            result['checks'][index] = dict(predicate=spec, state='unknown', detail=error, evidence={})
            continue
        grouped.setdefault(spec['file'], []).append((index, spec))
    for name, entries in grouped.items():
        snapshot = _snapshot(files.get(name), name)
        parsed = _csv(snapshot) if any(spec['kind'] != 'file_exists' for _, spec in entries) else None
        for index, spec in entries:
            data = snapshot if spec['kind'] == 'file_exists' else parsed
            state, detail, evidence = _test(spec, data)
            result['checks'][index] = dict(predicate=dict(spec), state=state, detail=detail, evidence=evidence)
        # Explicitly release matrices before reading the next complete artifact.
        del data, parsed, snapshot
    states = {check['state'] for check in result['checks']}
    result['state'] = 'failed' if 'failed' in states else 'unknown' if 'unknown' in states else 'passed'
    return result


def _bounds(spec: dict) -> tuple[Decimal | None, Decimal | None]:
    return (_decimal(spec['min']) if 'min' in spec else None,
            _decimal(spec['max']) if 'max' in spec else None)


def _implication(ensure: dict, require: dict, known_columns: set[str], nonempty: bool) -> tuple[str, str]:
    if require['kind'] == 'file_exists':
        return 'declared_compatible', 'a valid artifact ensure implies file existence'
    if ensure['kind'] == 'csv_schema' and ensure.get('exact', False):
        if not _required_columns(require) <= set(ensure['columns']):
            return 'contradicted', 'an exact output schema lacks required columns'
    if ensure['kind'] != require['kind']:
        return 'unknown', 'no supported implication between these predicate kinds'
    kind = require['kind']
    if kind == 'csv_schema':
        left, right = set(ensure['columns']), set(require['columns'])
        if require.get('exact', False):
            if not left <= right or (ensure.get('exact', False) and left != right):
                return 'contradicted', 'declared column sets contradict the exact required schema'
            compatible = ensure.get('exact', False) and left == right
        else:
            compatible = right <= left
        return ('declared_compatible', 'output schema entails required columns') if compatible else ('unknown', 'output schema does not establish all required columns')
    if kind == 'csv_no_missing':
        compatible = set(require['columns']) <= set(ensure['columns'])
    elif kind == 'csv_unique':
        compatible = (set(ensure['columns']) <= set(require['columns'])
                      and set(require['columns']) <= known_columns)
    elif kind == 'csv_numeric_range':
        if ensure['column'] != require['column']:
            return 'unknown', 'numeric constraints concern different columns'
        low, high = _bounds(ensure)
        wanted_low, wanted_high = _bounds(require)
        if ((high is not None and wanted_low is not None and high < wanted_low)
                or (low is not None and wanted_high is not None and low > wanted_high)):
            return ('contradicted', 'declared numeric intervals are disjoint on a declared nonempty CSV') if nonempty else ('unknown', 'disjoint ranges do not entail the precondition; an empty CSV could satisfy both')
        compatible = ((wanted_low is None or (low is not None and low >= wanted_low))
                      and (wanted_high is None or (high is not None and high <= wanted_high)))
    elif kind == 'csv_disjoint_groups':
        compatible = ensure['entity'] == require['entity'] and ensure['group'] == require['group']
    elif kind == 'csv_values_in':
        compatible = (ensure['column'] == require['column']
                      and {_enum_key(v) for v in ensure['values']} <= {_enum_key(v) for v in require['values']})
    elif kind == 'csv_group_numeric_coverage':
        compatible = (ensure['group'] == require['group'] and ensure['column'] == require['column']
                      and ensure.get('where') == require.get('where'))
    else:
        compatible = True  # csv_nonempty (file_exists handled above)
    return ('declared_compatible', 'output predicate conservatively entails the precondition') if compatible else ('unknown', 'output predicate does not establish the precondition')


def _inconsistent(specs: list[dict]) -> bool:
    exact_schemas = [set(s['columns']) for s in specs if s['kind'] == 'csv_schema' and s.get('exact', False)]
    if exact_schemas:
        if any(s != exact_schemas[0] for s in exact_schemas[1:]):
            return True
        if any(not _required_columns(s) <= exact_schemas[0] for s in specs):
            return True
    for coverage in (s for s in specs if s['kind'] == 'csv_group_numeric_coverage' and s.get('where')):
        where = coverage['where']
        for values in (s for s in specs if s['kind'] == 'csv_values_in' and s['column'] == where['column']):
            if _enum_key(where['equals']) not in {_enum_key(v) for v in values['values']}:
                return True  # Coverage requires a selected row; enumeration forbids every selected row.
    nonempty = any(s['kind'] in ('csv_nonempty', 'csv_group_numeric_coverage') for s in specs)
    ranges = [s for s in specs if s['kind'] == 'csv_numeric_range'] if nonempty else []
    for first in ranges:
        low, high = _bounds(first)
        for second in ranges:
            if first['column'] != second['column']:
                continue
            other_low, other_high = _bounds(second)
            if ((high is not None and other_low is not None and high < other_low)
                    or (low is not None and other_high is not None and low > other_high)):
                return True
    return False


def composition(steps: list[dict]) -> dict:
    """Check typed declared composition; never certify an unexecuted plan.

    Only transitive dependency ancestors are sources. If several incomparable
    producers declare the same logical file, the consumer is ambiguous. A later
    producer shadows all older declarations for that file, including predicates
    that it does not itself preserve.
    """
    result: dict[str, Any] = {'version': VERSION, 'state': 'unknown', 'edges': [], 'frontier': [],
                              'boundary': 'declared compatibility only; runtime evidence is required'}

    def invalid(detail: str) -> dict:
        result['frontier'].append(dict(reason='invalid_declared_plan', state='unknown', detail=detail))
        return result

    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        return invalid('a bounded nonempty step list is required')
    nodes: dict[int, dict] = {}
    for step in steps:
        if not isinstance(step, dict) or type(step.get('idx')) is not int or step['idx'] < 0 or step['idx'] in nodes:
            return invalid('step indices must be unique nonnegative integers')
        deps = step.get('depends_on', [])
        if not isinstance(deps, list) or len(deps) > MAX_STEPS or any(type(i) is not int for i in deps) or len(set(deps)) != len(deps):
            return invalid('dependencies must be unique integer indices')
        contract = step.get('contract', {})
        if not isinstance(contract, dict):
            return invalid('step contract must be an object')
        for key in ('requires', 'ensures'):
            specs = contract.get(key, [])
            if not isinstance(specs, list) or len(specs) > MAX_PREDICATES:
                return invalid('requires and ensures must be bounded predicate lists')
        nodes[step['idx']] = step
    if any(dep not in nodes for s in steps for dep in s.get('depends_on', [])):
        return invalid('a dependency refers to an absent step')
    ancestry: dict[int, set[int]] = {}
    visiting: set[int] = set()

    def ancestors(idx: int) -> set[int]:
        if idx in visiting:
            raise ValueError('cyclic dependencies')
        if idx in ancestry:
            return ancestry[idx]
        visiting.add(idx)
        found: set[int] = set()
        for dep in nodes[idx].get('depends_on', []):
            found.add(dep)
            found.update(ancestors(dep))
        visiting.remove(idx)
        ancestry[idx] = found
        return found

    try:
        for idx in nodes:
            ancestors(idx)
    except ValueError:
        return invalid('cyclic dependencies do not define a declared DAG')
    for step in steps:
        idx = step['idx']
        for require in step.get('contract', {}).get('requires', []):
            error = _validate(require)
            name = require.get('file') if isinstance(require, dict) else None
            edge = dict(source=None, target=idx, file=name, predicate=require, state='unknown', detail=error or '', candidate_sources=[])
            if not error:
                producers = []
                for prior in sorted(ancestry[idx]):
                    declared = nodes[prior].get('contract', {}).get('ensures', [])
                    if any(isinstance(s, dict) and s.get('file') == name for s in declared):
                        producers.append(prior)
                nearest = [p for p in producers if not any(p in ancestry[q] for q in producers if p != q)]
                edge['candidate_sources'] = nearest
                if len(nearest) > 1:
                    edge['detail'] = 'several incomparable ancestors produce the same logical file'
                elif not nearest:
                    edge['detail'] = 'no ancestor declares this required artifact'
                else:
                    source = nearest[0]
                    edge['source'] = source
                    declarations = nodes[source].get('contract', {}).get('ensures', [])
                    declarations = [s for s in declarations if isinstance(s, dict) and s.get('file') == name]
                    valid = [s for s in declarations if _validate(s) is None]
                    known_columns = set().union(*(_required_columns(s) for s in valid)) if valid else set()
                    if _inconsistent(valid):
                        edge['detail'] = 'producer has mutually inconsistent output declarations'
                    elif not valid:
                        edge['detail'] = 'producer has no supported valid output predicate'
                    else:
                        nonempty = any(s['kind'] == 'csv_nonempty' for s in valid)
                        implications = [(*_implication(s, require, known_columns, nonempty), s) for s in valid]
                        contradictions = [p for p in implications if p[0] == 'contradicted']
                        successes = [p for p in implications if p[0] == 'declared_compatible']
                        selected = (contradictions or successes or implications)[0]
                        edge.update(state=selected[0], detail=selected[1], ensure=selected[2])
            result['edges'].append(edge)
            if edge['state'] != 'declared_compatible':
                result['frontier'].append(dict(step_idx=idx, file=name, predicate=require, state=edge['state'],
                                               reason='unsatisfied_declared_precondition', detail=edge['detail'],
                                               candidate_sources=edge['candidate_sources']))
    states = {e['state'] for e in result['edges']}
    if states:
        result['state'] = ('contradicted' if 'contradicted' in states else 'unknown' if 'unknown' in states else 'declared_compatible')
    return result
