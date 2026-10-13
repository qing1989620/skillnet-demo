"""Frozen scenarios with an independent arithmetic oracle, separate from the LLM."""
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def scenarios():
    rows = json.loads((ROOT / 'config/business_scenarios.json').read_text(encoding='utf-8'))
    for row in rows:
        row['task'] = ('仅使用下面的公开模拟订单数据，不联网，禁止编造公司真实经营结论。完成 3 步真实执行：'
            '①按规则清洗明细生成 clean.csv 并打印重复数、缺失数；②读取 clean.csv 按 month 汇总成 monthly_summary.csv，'
            '列名严格为 month,revenue,cost,gross_profit,gross_margin,orders；③读取 monthly_summary.csv，'
            '生成 figure.svg 趋势图和 report.md 管理层报告，明确标注模拟数据、金额单位为元、毛利风险与行动建议。'
            '每步只负责本步交付，使用 depends_on 和 input_files/output_files 表达真实文件传递。规则：' + row['rules'] + '\nCSV：\n' + row['data'])
        row['task_sha256'] = hashlib.sha256(row['task'].strip().encode()).hexdigest()
    return rows


def oracle(scenario):
    seen, monthly = set(), {}
    for row in csv.DictReader(io.StringIO(scenario['data'])):
        if row['order_id'] in seen:
            continue
        seen.add(row['order_id'])
        if not row['revenue'] or not row['cost']:
            continue
        bucket = monthly.setdefault(row['month'],dict(revenue=0.,cost=0.,orders=0))
        bucket['revenue'] += float(row['revenue'])
        bucket['cost'] += float(row['cost'])
        bucket['orders'] += 1
    for bucket in monthly.values():
        bucket['gross_profit'] = bucket['revenue']-bucket['cost']
        bucket['gross_margin'] = bucket['gross_profit']/bucket['revenue'] if bucket['revenue'] else 0.
    return monthly


def evaluate_artifacts(scenario, run, workspace):
    files = [workspace/'artifacts'/a.name for a in run.artifacts if a.kind != '跨轮输入']
    summary = [p for p in files if p.name.endswith('monthly_summary.csv')]
    results, actual = [], {}
    expected = oracle(scenario)
    if summary:
        try:
            rows = list(csv.DictReader(summary[-1].read_text(encoding='utf-8-sig').splitlines()))
            actual = {row['month']:row for row in rows}
            if len(actual) != len(rows):
                actual = {}  # Duplicate months cannot pass through dictionary overwrite.
        except (ValueError,KeyError,csv.Error):
            actual = {}
    results.append(dict(name='月份完整且无额外月份',passed=set(actual)==set(expected)))
    # Fixed denominator even for absent, malformed, or partially correct files.
    for month, row in expected.items():
        for key, value in row.items():
            found = actual.get(month,{}).get(key)
            try:
                good = abs(float(found)-value) <= 1e-8
            except (TypeError,ValueError):
                good = False
            results.append(dict(name=f'{month}.{key}',passed=good,expected=value,actual=found))
    results.append(dict(name='矢量图存在',passed=any(p.suffix=='.svg' and p.stat().st_size>100 for p in files)))
    reports = [p for p in files if p.name.endswith('report.md')]
    results.append(dict(name='报告标注模拟数据',passed=bool(reports and '模拟' in reports[-1].read_text(encoding='utf-8'))))
    return dict(score=sum(r['passed'] for r in results)/len(results),checks=results,
                evaluator='independent arithmetic + artifact presence; report insight not scored',
                artifact_hashes={a.name:a.sha256 for a in run.artifacts})
