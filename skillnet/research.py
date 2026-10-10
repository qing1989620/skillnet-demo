"""Frozen synthetic research audit; no clinical data, training, or efficacy claim."""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

DATA = '''sample_id,subject_id,split,label,score
s01,p01,train,0,0.10
s02,p02,train,1,0.90
s03,p03,train,1,0.80
s04,p04,validation,0,0.20
s05,p05,validation,1,0.70
s06,p06,test,1,0.90
s07,p07,test,0,0.20
s08,p08,test,1,0.40
s09,p09,test,0,0.80
s10,p10,test,1,0.70
s11,p11,test,0,0.30
s12,p01,test,1,0.95
s13,p12,test,1,
s06,p06,test,1,0.90
'''


def research_scenario():
    task = ('使用下方公开模拟科研预测数据，完成 3 步真实执行，不联网、不训练模型。'
        '这是科研复现审计，不是医学诊断或真实模型性能。①按 sample_id 去重保留首次记录；'
        '识别同时出现在多个 split 的 subject_id；删除这些受试者的全部记录，再删除 score 缺失记录。'
        '生成 clean_predictions.csv（保留原列与原值）和 cohort_audit.csv，后者列名 check,count，'
        '且只含 raw_rows,duplicate_rows,cross_split_subjects,cross_split_rows,missing_score_rows,eligible_test_rows 六行；'
        'missing_score_rows 在删除跨 split 受试者后统计。②读取两个前序文件，仅用清洗后的 test 行，'
        '固定阈值 score >= 0.5 为阳性，生成 heldout_metrics.csv，列名 metric,value，'
        '且只含 n,tp,fp,tn,fn,accuracy,precision,recall,f1 九行，保留充分精度（至少 10 位有效数字）；'
        '不能用测试集选择阈值，不计算 AUROC。③读取审计表和指标表，生成 figure.svg 与 report.md，'
        '报告必须写明“模拟数据”“固定阈值”“不代表临床有效性”，解释数据泄漏风险与复用边界。'
        '每步只负责本步交付，使用 depends_on、input_files、output_files 传递真实文件。\nCSV：\n' + DATA)
    return dict(id='research-reproducibility-v1', title='科研复现 · 样本泄漏与指标核验', task=task,
        task_sha256=hashlib.sha256(task.strip().encode()).hexdigest(), data=DATA,
        scope='模拟预测数据的样本去重、跨集合受试者排除、固定阈值测试集混淆矩阵与派生指标；不评价模型或临床有效性')


def oracle():
    rows = list(csv.DictReader(io.StringIO(DATA)))
    seen, unique = set(), []
    for row in rows:
        if row['sample_id'] not in seen:
            unique.append(row)
            seen.add(row['sample_id'])
    splits = {}
    for row in unique:
        splits.setdefault(row['subject_id'], set()).add(row['split'])
    crossed = {subject for subject, values in splits.items() if len(values) > 1}
    separated = [r for r in unique if r['subject_id'] not in crossed]
    clean = [r for r in separated if r['score'] != '']
    test = [r for r in clean if r['split'] == 'test']
    tp = sum(r['label'] == '1' and float(r['score']) >= .5 for r in test)
    fp = sum(r['label'] == '0' and float(r['score']) >= .5 for r in test)
    tn = sum(r['label'] == '0' and float(r['score']) < .5 for r in test)
    fn = sum(r['label'] == '1' and float(r['score']) < .5 for r in test)
    return dict(cohort_audit=dict(raw_rows=len(rows), duplicate_rows=len(rows)-len(unique),
        cross_split_subjects=len(crossed), cross_split_rows=len(unique)-len(separated),
        missing_score_rows=len(separated)-len(clean), eligible_test_rows=len(test)),
        heldout_metrics=dict(n=len(test), tp=tp, fp=fp, tn=tn, fn=fn,
            accuracy=(tp+tn)/len(test), precision=tp/(tp+fp), recall=tp/(tp+fn), f1=2*tp/(2*tp+fp+fn)),
        clean_predictions=clean)


def evaluate_artifacts(run, workspace: Path):
    expected = oracle()
    files = {a.logical_name or Path(a.name).name.removeprefix(f'step{(a.from_step or 0)+1}_'):
             workspace/'artifacts'/a.name for a in run.artifacts if a.kind != '跨轮输入'}
    checks = []
    for name, key in [('cohort_audit', 'check'), ('heldout_metrics', 'metric')]:
        actual, rows, columns = {}, [], []
        try:
            with files[name+'.csv'].open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                columns = reader.fieldnames
                rows = list(reader)
            actual = {r[key]: r['count' if key == 'check' else 'value'] for r in rows}
        except (KeyError, OSError, UnicodeError, csv.Error):
            pass
        checks.append(dict(name=f'{name}.schema', output=name+'.csv', passed=
            columns == [key, 'count' if key == 'check' else 'value'] and len(rows) == len(actual)
            and set(actual) == set(expected[name])))
        for metric, value in expected[name].items():
            found = actual.get(metric)
            try:
                passed = abs(float(found)-value) <= 1e-9
            except (ValueError, TypeError, OverflowError):
                passed = False
            checks.append(dict(name=f'{name}.{metric}', output=name+'.csv', passed=passed, expected=value, actual=found))
    try:
        with files['clean_predictions.csv'].open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            clean = list(reader)
            columns = reader.fieldnames
        passed = columns == ['sample_id','subject_id','split','label','score'] and clean == expected['clean_predictions']
    except (KeyError, OSError, UnicodeError, csv.Error):
        passed = False
    checks.append(dict(name='clean_predictions.original_values', output='clean_predictions.csv', passed=passed))
    try:
        report = files['report.md'].read_text(encoding='utf-8')
        marked = all(word in report for word in ('模拟数据','固定阈值','不代表临床有效性'))
    except (KeyError, OSError, UnicodeError):
        marked = False
    checks.append(dict(name='report.scope_labels', output=None, passed=marked))
    figure = files.get('figure.svg')
    checks.append(dict(name='figure.present', output=None, passed=bool(figure and figure.is_file() and figure.stat().st_size > 100)))
    for check in checks:
        target = files.get(check.get('output'))
        check['artifact_name'] = target.name if target else None
    return dict(score=sum(c['passed'] for c in checks)/len(checks), checks=checks,
        evaluator='independent synthetic cohort/threshold arithmetic; figure presence and scope labels only; no clinical validity',
        artifact_hashes={a.name: a.sha256 for a in run.artifacts})
