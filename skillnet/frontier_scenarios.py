"""Public deterministic tasks; these are demonstrations, never customer data."""
from __future__ import annotations

import csv
import io
from pathlib import Path

from . import frontier_runtime

HEADER = ['sample_id', 'subject_id', 'split', 'label', 'score']
SCENARIOS = [
    {'id': 'combined', 'label': '复合缺口 → 定向执行 → 复核',
     'description': '重复、跨分组泄漏、缺失值同时存在；实际清洗后重读条件，计算留出指标。'},
    {'id': 'missing-provider', 'label': '缺少跨分组排除能力',
     'description': '从登记子集中移除唯一泄漏排除程序；展示未补上的条件，不靠文字宣称已解决。'},
    {'id': 'restored-provider', 'label': '恢复提供者后，同题复验',
     'description': '同一份数据加入泄漏排除程序，实测是否恢复可交付结果。'},
    {'id': 'threshold-counterexample', 'label': '阈值反例 → 拒绝错误版本',
     'description': '结构条件全部满足，故意使用 >0.5 的缺陷版本；独立复算能否识别算法错误。'},
    {'id': 'unmodeled-condition', 'label': '未建模条件 → 诚实保留失败',
     'description': '数据均合规但没有 test 留出样本；声明路径存在，实际执行失败。'},
]


def csv_bytes(rows: list[list[str]]) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(HEADER)
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def rows_for(mask: int = 0, variant: int = 0) -> list[list[str]]:
    """Three independent defects; variant changes names/order/numeric spellings."""
    prefix = f'v{variant}-'
    rows = [[prefix + str(i), prefix + subject, split, label, score]
            for i, (subject, split, label, score) in enumerate([
                ('A', 'train', '1', '0.90'), ('B', 'test', '0', '0.10'),
                ('C', 'test', '1', '0.50'), ('D', 'test', '0', '0.70'),
                ('E', 'test', '1', '0.80'), ('F', 'train', '0', '0.20')], 1)]
    if variant % 2:
        rows.reverse()
    if variant >= 2:
        rows.append([prefix + '7', prefix + 'H', 'test', '0', '0.500'])
    if mask & 1:
        # Duplicate exact record: dedup is required without changing leakage.
        rows.append(list(rows[1]))
    if mask & 2:
        rows.append([prefix + 'leak', prefix + 'A', 'test', '1', '0.95'])
    if mask & 4:
        rows.append([prefix + 'missing', prefix + 'G', 'test', '1', '  '])
    return rows


def scenarios() -> list[dict]:
    return [dict(s) for s in SCENARIOS]


def materialize(scenario_id: str, workspace: Path) -> Path:
    if scenario_id not in {s['id'] for s in SCENARIOS}:
        raise ValueError('unknown public scenario')
    rows = rows_for(7 if scenario_id == 'combined' else 2 if scenario_id in (
        'missing-provider', 'restored-provider') else 0)
    if scenario_id == 'unmodeled-condition':
        for row in rows:
            row[2] = 'train'
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / 'public-input.csv'
    path.write_bytes(csv_bytes(rows))
    return path


def run_scenario(scenario_id: str, workspace: Path) -> dict:
    path = materialize(scenario_id, workspace)
    kwargs = {}
    if scenario_id == 'missing-provider':
        kwargs['operator_ids'] = ['deduplicate', 'drop_missing_score', 'metrics_decimal']
    if scenario_id == 'threshold-counterexample':
        kwargs['metric_id'] = 'metrics_strict_bug'
    result = frontier_runtime.run(path, workspace / 'execution', **kwargs)
    result['scenario_id'] = scenario_id
    return frontier_runtime.public_report(result)
