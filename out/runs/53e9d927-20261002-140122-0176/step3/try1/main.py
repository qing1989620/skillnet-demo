# -*- coding: utf-8 -*-
"""
步骤：建立错题台账并做数据清洗
输入：error_ledger.csv（前序产物，真实文件）
产出：error_ledger_clean.csv, data_dictionary.csv, audit_log.csv, figure.png
说明：若输入文件不存在，则用模拟数据并在输出中明确标注「模拟数据」。
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

VALID_CAUSES = ['概念不清', '计算失误', '审题', '记忆']
PENDING = '待补'
AUDIT = []

def log(step, reason, before, after, note=''):
    AUDIT.append({'step': step, 'reason': reason,
                  'rows_before': before, 'rows_after': after, 'note': note})

def load_data():
    """读取真实文件；不存在则生成模拟数据（明确标注）。"""
    path = 'error_ledger.csv'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        return rows, False
    # ---- 模拟数据（非真实实验结论）----
    rng = np.random.default_rng(42)
    years = [2015, 2016, 2017, 2018, 2019, 2020]
    chapters = ['数据结构', '计算机组成', '操作系统', '计算机网络']
    kps = ['线性表', '树', '图', '排序', 'Cache', '流水线', '进程', '内存', 'TCP', 'IP']
    types = ['选择', '大题']
    rows = []
    for i in range(300):
        y = int(rng.choice(years))
        q = int(rng.integers(1, 46))
        cause = rng.choice(VALID_CAUSES + [PENDING, '', '其他'])
        rows.append({
            'year': str(y), 'qno': str(q),
            'chapter': str(rng.choice(chapters)),
            'knowledge': str(rng.choice(kps)),
            'qtype': str(rng.choice(types)),
            'correct': str(rng.choice(['对', '错'])),
            'time_min': str(round(float(rng.uniform(0.5, 25)), 1)),
            'cause': str(cause),
        })
    # 注入重复主键与异常用时
    rows.append(dict(rows[0]))
    rows.append({**rows[1], 'time_min': '-3'})
    return rows, True

def main():
    rows, is_sim = load_data()
    print('=' * 60)
    print('数据来源:', '模拟数据（非真实实验结论）' if is_sim else '真实文件 error_ledger.csv')
    print('原始行数:', len(rows))
    print('字段:', list(rows[0].keys()))

    # 1. 结构与类型探查 + 主键唯一性
    n0 = len(rows)
    keys = [(r['year'].strip(), r['qno'].strip()) for r in rows]
    dup = len(keys) - len(set(keys))
    print('主键(year+qno)重复数:', dup)
    # 去重：保留首次出现（主键唯一）
    seen, dedup = set(), []
    for r, k in zip(rows, keys):
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    log('去重', '主键=真题年份+题号必须唯一，重复保留首次', n0, len(dedup), f'删除{dup}行')
    print('去重后行数:', len(dedup))

    # 2. 缺失模式标记（不删除缺失行）
    miss_cause = sum(1 for r in dedup if r['cause'].strip() == '')
    miss_time = sum(1 for r in dedup if r['time_min'].strip() == '')
    print('cause 缺失行数:', miss_cause, '| time_min 缺失行数:', miss_time)
    print('缺失处理策略: 不删除，cause 缺失标记为「待补」（非随机缺失，禁止均值填补）')

    # 3. 业务规则识别异常值（非统计阈值）
    cleaned = []
    n_before = len(dedup)
    bad_time = 0
    for r in dedup:
        r = dict(r)
        # 错因规范化：仅允许4类，其余（含空、其他）标记待补
        c = r['cause'].strip()
        if c not in VALID_CAUSES:
            r['cause'] = PENDING
        # 用时业务规则：0 < time <= 60 分钟，否则视为异常置空并标记
        t = r['time_min'].strip()
        try:
            tv = float(t)
            if tv <= 0 or tv > 60:
                r['time_min'] = ''
                bad_time += 1
        except ValueError:
            r['time_min'] = ''
            bad_time += 1
        cleaned.append(r)
    log('错因规范化', '错因固定4类，其余标记待补（禁止自由文本）', n_before, len(cleaned),
        f'待补={sum(1 for r in cleaned if r["cause"]==PENDING)}')
    log('用时异常', '业务规则 0<time<=60 分钟，越界置空', n_before, len(cleaned), f'异常{bad_time}行')

    # 4. 分布变化记录
    def dist(rs, key):
        d = {}
        for r in rs:
            d[r[key]] = d.get(r[key], 0) + 1
        return d
    print('清洗前 cause 分布:', dist(dedup, 'cause'))
    print('清洗后 cause 分布:', dist(cleaned, 'cause'))
    print('清洗后 correct 分布:', dist(cleaned, 'correct'))

    # 5. 数据字典
    dd = [
        ('year', '真题年份', 'int', '年', '主键之一'),
        ('qno', '题号', 'int', '题', '主键之一'),
        ('chapter', '章节', 'str', '-', '408四门课'),
        ('knowledge', '知识点', 'str', '-', '细粒度考点'),
        ('qtype', '题型', 'str', '-', '选择/大题'),
        ('correct', '对错', 'str', '-', '对/错'),
        ('time_min', '用时', 'float', '分钟', '0<time<=60，越界置空'),
        ('cause', '错因', 'str', '-', '概念不清/计算失误/审题/记忆/待补'),
    ]
    with open('data_dictionary.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['字段', '含义', '类型', '单位', '口径'])
        w.writerows(dd)

    # 落盘清洗结果与审计日志
    fields = ['year', 'qno', 'chapter', 'knowledge', 'qtype', 'correct', 'time_min', 'cause']
    with open('error_ledger_clean.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in cleaned:
            w.writerow({k: r.get(k, '') for k in fields})
    with open('audit_log.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['step', 'reason', 'rows_before', 'rows_after', 'note'])
        w.writeheader()
        w.writerows(AUDIT)

    # 验收检查
    final_keys = [(r['year'], r['qno']) for r in cleaned]
    print('验收-清洗后主键唯一:', len(final_keys) == len(set(final_keys)))
    print('验收-审计日志条数:', len(AUDIT))
    print('验收-待补行数:', sum(1 for r in cleaned if r['cause'] == PENDING))

    # 图：清洗前后错因分布对比
    before_d = dist(dedup, 'cause')
    after_d = dist(cleaned, 'cause')
    labels = VALID_CAUSES + [PENDING]
    b = [before_d.get(l, 0) for l in labels]
    a = [after_d.get(l, 0) for l in labels]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - 0.2, b, 0.4, label='清洗前')
    ax.bar(x + 0.2, a, 0.4, label='清洗后')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('题数')
    ax.set_title('错因分布：清洗前后对比' + ('（模拟数据）' if is_sim else ''))
    ax.legend()
    plt.tight_layout()
    plt.savefig('figure.png', dpi=120)
    print('已保存: error_ledger_clean.csv, data_dictionary.csv, audit_log.csv, figure.png')

if __name__ == '__main__':
    main()