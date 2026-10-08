"""Step-scoped contracts and bounded factual evidence for independent judging."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace


def planning_data_facts(task: str) -> dict:
    """Observe an explicitly supplied CSV, without inventing cleaning policy or target answers."""
    match = re.search(r'```csv\s*\n(.*?)\n```', task, re.I | re.S)
    if not match:
        match = re.search(r'(?:^|\n)CSV\s*[:：]\s*\n(.+)$', task, re.I | re.S)
    if not match:
        return {}
    text = match.group(1).split('\n\n', 1)[0]
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error:
        return {}
    if not 2 <= len(rows) <= 512:
        return {}
    header, values = rows[0], rows[1:]
    if (len(header) < 2 or len(set(header)) != len(header)
            or any(len(row) != len(header) for row in values)):
        return {}
    return dict(source='explicit_user_csv', rows=len(values), columns=header,
                missing_cells={key:sum(not row[i].strip() for row in values) for i,key in enumerate(header)},
                exact_duplicate_rows=len(values)-len({tuple(row) for row in values}),
                boundary='输入观察值；未推断清洗策略、清洗后行数或业务结论')


def scoped_skill(skill, step):
    if skill is None:
        return None
    values = dict(vars(skill))
    if hasattr(skill, 'reference_body'):
        values['reference_body'] = skill.reference_body
    explicit = step.contract.get('verification')
    if isinstance(explicit, list):
        values['verification'] = [str(v) for v in explicit]
    values['contract_scope'] = step.contract
    return SimpleNamespace(**values)


def file_evidence(paths: list[Path]) -> list[dict]:
    facts = []
    for path in paths[:24]:
        if not path.is_file():
            continue
        sha = hashlib.sha256()
        with path.open('rb') as stream:
            while chunk := stream.read(65536):
                sha.update(chunk)
        with path.open('rb') as stream:
            raw = stream.read(12000)
        size = path.stat().st_size
        fact = dict(name=path.name, bytes=size, sha256=sha.hexdigest())
        suffix = path.suffix.lower()
        if suffix == '.csv':
            try:
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream)
                    sample, count = [], 0
                    for row in reader:
                        count += 1
                        if len(sample) < 8:
                            sample.append({k: str(v)[:400] for k, v in row.items() if k is not None})
                    fact.update(columns=reader.fieldnames or [], rows=count, sample=sample)
            except (UnicodeError, csv.Error):
                fact['parse_error'] = 'CSV decoding failed'
        elif suffix == '.png':
            from .checks import png_size
            fact['dimensions'] = png_size(path)
        elif suffix in ('.json', '.txt', '.md', '.svg'):
            fact['content_excerpt'] = raw[:12000].decode('utf-8', 'replace')
            fact['excerpt_truncated'] = size > 12000
        elif suffix == '.pdf':
            fact['pdf_header_valid'] = raw.startswith(b'%PDF-')
        facts.append(fact)
    return facts


def projection_check(spec: dict, inputs: dict[str, Path], outputs: dict[str, Path]) -> dict:
    """Compare immutable source bytes with a CSV projection, independently of generated assertions."""
    from decimal import Decimal, InvalidOperation
    label = 'CSV 原值投影与排序'
    try:
        if not isinstance(spec, dict) or spec.get('kind') != 'csv_projection':
            raise ValueError('未知数据检查类型')
        keys, columns = spec['keys'], spec['columns']
        if any(not isinstance(v,list) or not v or len(v)>32 or any(not isinstance(k,str) for k in v) for v in (keys,columns)):
            raise ValueError('键和列必须为非空字符串数组')
        names = keys + columns
        if len(set(names)) != len(names):
            raise ValueError('键或列重复')
        tolerance = Decimal(str(spec.get('atol',1e-9)))
        if not tolerance.is_finite() or not 0 <= tolerance <= Decimal('0.000001'):
            raise ValueError('原值投影容差必须在 0 到 1e-6 之间')
        def read(path):
            if path.stat().st_size > 16*1024*1024:
                raise ValueError('CSV 超过检查大小限制')
            with path.open(encoding='utf-8-sig',newline='') as stream:
                reader=csv.DictReader(stream,strict=True);rows=[]
                if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):
                    raise ValueError('CSV 表头缺失或重复')
                for row in reader:
                    if len(rows)>=50000:raise ValueError('CSV 超过检查行数限制')
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError('CSV 行宽与表头不一致')
                    rows.append(row)
            return reader.fieldnames, rows
        src_header, src = read(inputs[spec['input_file']])
        dst_header, dst = read(outputs[spec['output_file']])
        if not set(names) <= set(src_header or []) or dst_header != names:
            raise ValueError('投影列名或顺序不匹配')
        def keyed(rows):
            result={tuple(row[k] for k in keys):row for row in rows}
            if len(result)!=len(rows):raise ValueError('投影键重复')
            return result
        before, after = keyed(src), keyed(dst)
        if set(before)!=set(after):raise ValueError('投影丢失或增加记录')
        for key, row in before.items():
            for col in columns:
                left,right=row[col],after[key][col]
                try:
                    a,b=Decimal(left),Decimal(right)
                except InvalidOperation:
                    if left!=right:raise ValueError(f'{key} {col} 文本值改变')
                else:
                    if not a.is_finite() or not b.is_finite() or abs(a-b)>tolerance:
                        raise ValueError(f'{key} {col} 原值 {left}，输出 {right}，超出容差 {tolerance}')
        sort_by=spec.get('sort_by')
        if sort_by:
            if sort_by not in names or type(spec.get('ascending',True)) is not bool:
                raise ValueError('排序配置无效')
            raw_order=[row[sort_by] for row in dst]
            try:
                order=[Decimal(value) for value in raw_order]
                if any(not v.is_finite() for v in order):raise ValueError('排序值非有限数')
            except InvalidOperation:
                order=raw_order
            if order!=sorted(order,reverse=not spec.get('ascending',True)):
                raise ValueError('排序不满足契约')
        return dict(name=label,passed=True,detail=f'{len(dst)} 行逐格对照不可变输入，容差 {tolerance}')
    except (KeyError,TypeError,ValueError,OSError,UnicodeError,csv.Error,InvalidOperation) as exc:
        return dict(name=label,passed=False,detail=str(exc)[:500])


def contract_checks(contract: dict, paths: list[Path], carried: list[str], *, input_paths: dict[str, Path] | None = None) -> list[dict]:
    results = []
    outputs = contract.get('output_files') or []
    for name in outputs:
        present = any(p.name == name or p.name.endswith('_' + name) for p in paths)
        results.append(dict(name=f'步骤交付：{name}', passed=present, detail='存在' if present else '未生成约定产物'))
    for name in contract.get('input_files') or []:
        results.append(dict(name=f'输入版本：{name}', passed=name in carried,
                            detail='已携带已登记版本' if name in carried else '缺少输入，禁止重新编造数据'))
    specs=contract.get('data_checks',[])
    if not isinstance(specs,list) or len(specs)>8:
        results.append(dict(name='数据检查配置',passed=False,detail='必须为最多 8 项的数组'))
    else:
        for spec in specs:
            results.append(projection_check(spec,input_paths or {},{p.name:p for p in paths}))
    return results


def acceptance(run) -> dict:
    checks = [c for st in run.steps for c in st.checks if getattr(c, 'required', True)]
    semantic = [v for st in run.steps for v in st.verifications]
    failed = sum(not c.passed for c in checks) + sum(getattr(v, 'state', '') == 'failed' or
                 (not v.passed and getattr(v, 'state', '') not in ('unknown', 'not_applicable')) for v in semantic)
    unknown = sum(getattr(v, 'state', '') == 'unknown' for v in semantic)
    incomplete = any(st.status != 'done' for st in run.steps)
    state = 'failed' if failed else 'unknown' if unknown or incomplete or not checks else 'passed'
    return dict(state=state, failed=failed, unknown=unknown,
                checks_passed=sum(c.passed for c in checks), checks_total=len(checks),
                semantic_passed=sum(v.passed for v in semantic), semantic_total=len(semantic))
