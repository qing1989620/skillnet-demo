# -*- coding: utf-8 -*-
"""
步骤3：建立错题台账并做数据清洗
- 读取真实前序产物（若不存在则用模拟数据并明确标注）
- 固定4类错因，未记录标记为待补
- 主键 = 真题年份 + 题号，保证唯一
- 产出数据字典 + 清洗审计日志
- 规避陷阱：错因固定、待补不删除、主键唯一、错题数守恒
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG = np.random.default_rng(42)
CAUSE_SET = ['概念不清', '计算失误', '审题', '记忆']
PENDING = '待补'
AUDIT = []


def log(msg):
    AUDIT.append(msg)
    print('[AUDIT]', msg)


def load_or_simulate():
    """读取真实文件；不存在则生成模拟数据（明确标注）"""
    if os.path.exists('error_ledger.csv'):
        import csv
        rows = []
        with open('error_ledger.csv', 'r', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                rows.append(r)
        log(f'读取真实 error_ledger.csv，共 {len(rows)} 条')
        return rows, False
    # ---- 模拟数据（明确标注）----
    log('未找到 error_ledger.csv，使用【模拟数据】进行演示')
    chapters = ['数据链路层', '网络层', '传输层', '应用层', '物理层']
    kps = {'数据链路层': ['CRC', '滑动窗口', '以太网帧'],
           '网络层': ['IP分片', '路由算法', '子网划分'],
           '传输层': ['TCP三次握手', '拥塞控制', 'UDP'],
           '应用层': ['DNS', 'HTTP', 'SMTP'],
           '物理层': ['奈氏准则', '香农定理', '编码']}
    types = ['选择', '计算', '简答']
    rows = []
    for i in range(120):
        ch = RNG.choice(chapters)
        kp = RNG.choice(kps[ch])
        year = int(RNG.choice([2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]))
        qno = int(RNG.integers(1, 40))
        correct = int(RNG.random() < 0.45)
        t = round(float(RNG.uniform(1, 12)), 1)
        if correct:
            cause = ''
        else:
            cause = str(RNG.choice(CAUSE_SET + ['', '']))
        rows.append({'真题年份': str(year), '题号': str(qno), '章节': ch,
                     '知识点': kp, '题型': str(RNG.choice(types)),
                     '对错': '对' if correct else '错',
                     '用时分钟': str(t), '错因': cause})
    return rows, True


def clean(rows):
    """数据清洗：主键唯一、错因规范化、待补标记"""
    seen = {}
    cleaned = []
    dup = 0
    for r in rows:
        key = (str(r.get('真题年份', '')).strip(), str(r.get('题号', '')).strip())
        if key in seen:
            dup += 1
            continue
        seen[key] = True
        cause = str(r.get('错因', '')).strip()
        is_wrong = str(r.get('对错', '')).strip() == '错'
        if is_wrong:
            if cause not in CAUSE_SET:
                cause = PENDING  # 未记录/非法 -> 待补，不删除
        else:
            cause = ''  # 做对无错因
        try:
            t = float(r.get('用时分钟', 0))
        except Exception:
            t = 0.0
        cleaned.append({'真题年份': key[0], '题号': key[1],
                        '章节': str(r.get('章节', '')).strip(),
                        '知识点': str(r.get('知识点', '')).strip(),
                        '题型': str(r.get('题型', '')).strip(),
                        '对错': '错' if is_wrong else '对',
                        '用时分钟': t, '错因': cause})
    log(f'主键去重：删除重复 {dup} 条，保留 {len(cleaned)} 条')
    return cleaned


def main():
    rows, is_sim = load_or_simulate()
    data = clean(rows)

    n_total = len(data)
    wrong = [d for d in data if d['对错'] == '错']
    n_wrong = len(wrong)
    pending = [d for d in wrong if d['错因'] == PENDING]
    log(f'总记录 {n_total} 条，错题 {n_wrong} 条，待补错因 {len(pending)} 条（保留未删除）')

    # 错因分布
    cause_cnt = {c: 0 for c in CAUSE_SET}
    cause_cnt[PENDING] = 0
    for d in wrong:
        cause_cnt[d['错因']] = cause_cnt.get(d['错因'], 0) + 1
    print('\n=== 错因分布（固定4类+待补）===')
    for c in CAUSE_SET + [PENDING]:
        print(f'  {c}: {cause_cnt.get(c, 0)}')

    # 各章错题数守恒检查
    ch_wrong = {}
    for d in wrong:
        ch_wrong[d['章节']] = ch_wrong.get(d['章节'], 0) + 1
    print('\n=== 各章错题数 ===')
    for ch, c in sorted(ch_wrong.items(), key=lambda x: -x[1]):
        print(f'  {ch}: {c}')
    print(f'  各章错题数之和 = {sum(ch_wrong.values())}，总错题数 = {n_wrong}，'
          f'守恒={"通过" if sum(ch_wrong.values()) == n_wrong else "失败"}')

    # 主键唯一性
    keys = [(d['真题年份'], d['题号']) for d in data]
    print(f'\n主键唯一性检查：{len(keys)} 条 / 唯一 {len(set(keys))} 个 -> '
          f'{"通过" if len(keys) == len(set(keys)) else "失败"}')

    # 随机抽5条回溯
    print('\n=== 随机抽5条记录（可回溯到原始试卷）===')
    idx = RNG.choice(len(data), size=min(5, len(data)), replace=False)
    for i in idx:
        d = data[i]
        print(f'  {d["真题年份"]}年 第{d["题号"]}题 | {d["章节"]}/{d["知识点"]} | '
              f'{d["题型"]} | {d["对错"]} | {d["用时分钟"]}min | 错因={d["错因"] or "-"}')

    # 数据字典
    print('\n=== 数据字典 ===')
    dd = [('真题年份', 'int/str', '试卷年份，主键组成'),
          ('题号', 'int/str', '试卷内题号，主键组成'),
          ('章节', 'str', '考纲章节名'),
          ('知识点', 'str', '章节下细分考点'),
          ('题型', 'str', '选择/计算/简答'),
          ('对错', 'str', '对/错'),
          ('用时分钟', 'float', '本题实际用时'),
          ('错因', 'str', f'固定4类{CAUSE_SET}；未记录={PENDING}；做对为空')]
    for name, typ, desc in dd:
        print(f'  {name:8s} | {typ:8s} | {desc}')

    # 出图：错因分布 + 各章错题数
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = CAUSE_SET + [PENDING]
    vals = [cause_cnt.get(c, 0) for c in labels]
    axes[0].bar(labels, vals, color=['#e74c3c', '#f39c12', '#3498db', '#9b59b6', '#95a5a6'])
    axes[0].set_title('错因分布（固定4类+待补）')
    axes[0].set_ylabel('错题数')
    chs = list(ch_wrong.keys())
    axes[1].bar(chs, [ch_wrong[c] for c in chs], color='#2ecc71')
    axes[1].set_title('各章错题数')
    axes[1].set_ylabel('错题数')
    plt.tight_layout()
    plt.savefig('figure.png', dpi=120)
    print('\n已生成 figure.png')

    # 落盘
    import csv
    with open('error_ledger_clean.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['真题年份', '题号', '章节', '知识点',
                                          '题型', '对错', '用时分钟', '错因'])
        w.writeheader()
        w.writerows(data)
    with open('data_dictionary.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['字段', '类型', '口径说明'])
        for row in dd:
            w.writerow(row)
    with open('clean_audit_log.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(AUDIT))
    print('已落盘：error_ledger_clean.csv / data_dictionary.csv / clean_audit_log.txt')
    if is_sim:
        print('\n*** 注意：本次结果为【模拟数据】演示，非真实实验结论 ***')


if __name__ == '__main__':
    main()