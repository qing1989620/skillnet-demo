import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv
import os

# ============================================================
# 说明：本脚本使用【模拟数据】演示成绩表清洗流程。
# 所有数值均为随机生成，不代表任何真实考试结论。
# ============================================================

rng = np.random.default_rng(42)

SUBJECTS = ['语文', '数学', '英语', '物理']
FULL_SCORE = {'语文': 150, '数学': 150, '英语': 150, '物理': 100}
BATCHES = ['2024期中', '2024期末']
N_STU = 60

# ---------- 1. 构造模拟原始数据（含脏数据） ----------
rows = []
sid = 0
for s in range(N_STU):
    stu = f"S{1000+s}"
    for subj in SUBJECTS:
        for batch in BATCHES:
            sid += 1
            full = FULL_SCORE[subj]
            base = rng.normal(full * 0.7, full * 0.12)
            score = float(np.clip(base, 0, full))
            dur = float(rng.normal(60, 10))
            rows.append({
                'record_id': f"R{sid:05d}",
                'stu_id': stu,
                'subject': subj,
                'batch': batch,
                'score': round(score, 1),
                'duration_min': round(dur, 1),
                'submit_ts': f"2024-0{rng.integers(1,3)}-{rng.integers(10,28):02d} "
                             f"{rng.integers(8,18):02d}:{rng.integers(0,60):02d}",
                'status': 'normal',
            })

# 注入脏数据
# (a) 缺考：score 为空
for i in rng.choice(len(rows), 8, replace=False):
    rows[i]['score'] = None
    rows[i]['status'] = 'absent'
# (b) 未作答：score=0 且 duration 很小
for i in rng.choice(len(rows), 5, replace=False):
    rows[i]['score'] = 0.0
    rows[i]['duration_min'] = round(float(rng.uniform(0.5, 2.0)), 1)
    rows[i]['status'] = 'no_answer'
# (c) 未录入：duration 为空
for i in rng.choice(len(rows), 4, replace=False):
    rows[i]['duration_min'] = None
    rows[i]['status'] = 'not_entered'
# (d) 异常：分数超满分
for i in rng.choice(len(rows), 3, replace=False):
    rows[i]['score'] = FULL_SCORE[rows[i]['subject']] + rng.uniform(1, 20)
# (e) 异常：用时为负
for i in rng.choice(len(rows), 3, replace=False):
    rows[i]['duration_min'] = -abs(rows[i]['duration_min'])
# (f) 重复提交：复制一条记录
dup = dict(rows[10])
rows.append(dup)

raw = rows
print("=" * 60)
print("【模拟数据】原始记录数:", len(raw))

# ---------- 2. 结构与类型探查 ----------
fields = ['record_id', 'stu_id', 'subject', 'batch', 'score', 'duration_min', 'submit_ts', 'status']
print("\n[结构探查] 字段与类型:")
for f in fields:
    vals = [r[f] for r in raw]
    nonnull = [v for v in vals if v is not None]
    t = type(nonnull[0]).__name__ if nonnull else 'all-null'
    print(f"  {f:14s} type={t:6s} null={len(vals)-len(nonnull)}/{len(vals)}")

# ---------- 3. 主键唯一性检查 ----------
def key_of(r):
    return (r['stu_id'], r['subject'], r['batch'])

from collections import Counter
kc = Counter(key_of(r) for r in raw)
dup_keys = {k: c for k, c in kc.items() if c > 1}
print("\n[主键检查] 学号+科目+批次 重复键数:", len(dup_keys))
for k, c in list(dup_keys.items())[:5]:
    print("   重复:", k, "出现", c, "次")

# ---------- 4. 缺失模式标记 ----------
miss_score = sum(1 for r in raw if r['score'] is None)
miss_dur = sum(1 for r in raw if r['duration_min'] is None)
print("\n[缺失模式] score 缺失:", miss_score, " duration_min 缺失:", miss_dur)
print("  缺失与 status 的关联（判断是否非随机缺失 MNAR）:")
for st in ['absent', 'no_answer', 'not_entered', 'normal']:
    sub = [r for r in raw if r['status'] == st]
    ms = sum(1 for r in sub if r['score'] is None)
    md = sum(1 for r in sub if r['duration_min'] is None)
    print(f"   status={st:12s} n={len(sub):3d} score缺失={ms:2d} dur缺失={md:2d}")

# ---------- 5. 业务规则异常识别 ----------
audit = []
def log(step, reason, n_before, n_after):
    audit.append({'step': step, 'reason': reason,
                  'rows_before': n_before, 'rows_after': n_after,
                  'rows_affected': n_before - n_after})

# 5.1 去重（保留首次出现）
seen = set()
dedup = []
for r in raw:
    k = key_of(r)
    if k in seen:
        continue
    seen.add(k)
    dedup.append(r)
log('去重', '主键重复提交，保留首次', len(raw), len(dedup))
print("\n[清洗1-去重] 前:", len(raw), "后:", len(dedup), "影响:", len(raw)-len(dedup))

# 5.2 分数超满分 -> 标记 invalid_score（不删除，置空并标记）
n_before = len(dedup)
invalid_score = 0
for r in dedup:
    if r['score'] is not None and (r['score'] < 0 or r['score'] > FULL_SCORE[r['subject']]):
        r['score'] = None
        r['status'] = 'invalid_score'
        invalid_score += 1
log('分数越界', '分数超出[0,满分]，置空并标记', n_before, n_before)
print("[清洗2-分数越界] 影响行数:", invalid_score)

# 5.3 用时为负 -> 标记 invalid_duration
invalid_dur = 0
for r in dedup:
    if r['duration_min'] is not None and r['duration_min'] < 0:
        r['duration_min'] = None
        r['status'] = 'invalid_duration'
        invalid_dur += 1
log('用时为负', 'duration<0，置空并标记', n_before, n_before)
print("[清洗3-用时为负] 影响行数:", invalid_dur)

# 5.4 未作答识别（score=0 且 duration 极短）
no_answer = 0
for r in dedup:
    if r['score'] == 0.0 and r['duration_min'] is not None and r['duration_min'] < 3:
        r['status'] = 'no_answer'
        no_answer += 1
log('未作答标记', 'score=0且用时<3min', n_before, n_before)
print("[清洗4-未作答] 影响行数:", no_answer)

clean = dedup
print("\n[清洗后] 记录数:", len(clean))

# ---------- 6. 清洗后主键唯一性复检 ----------
kc2 = Counter(key_of(r) for r in clean)
dup2 = {k: c for k, c in kc2.items() if c > 1}
print("[验收] 清洗后主键唯一:", len(dup2) == 0, " 重复键数:", len(dup2))

# ---------- 7. 关键字段分布变化 ----------
def score_stats(data):
    vals = [r['score'] for r in data if r['score'] is not None]
    if not vals:
        return (0, 0, 0, 0)
    return (len(vals), round(float(np.mean(vals)), 2),
            round(float(np.min(vals)), 2), round(float(np.max(vals)), 2))

print("\n[分布变化] score (n, mean, min, max):")
print("  清洗前:", score_stats(raw))
print("  清洗后:", score_stats(clean))

# ---------- 8. 审计日志 ----------
print("\n[审计日志]")
for a in audit:
    print(f"  {a['step']:10s} | {a['reason']:24s} | 影响 {a['rows_affected']} 行")

# ---------- 9. 数据字典 ----------
data_dict = [
    ('record_id', '记录唯一编号', '字符串', '-'),
    ('stu_id', '学号', '字符串', '-'),
    ('subject', '科目', '字符串', '-'),
    ('batch', '考试批次', '字符串', '-'),
    ('score', '得分', '浮点', '分，范围[0,满分]，空=缺考/越界'),
    ('duration_min', '作答用时', '浮点', '分钟，空=未录入/异常'),
    ('submit_ts', '提交时间', '字符串', 'YYYY-MM-DD HH:MM'),
    ('status', '记录状态', '字符串', 'normal/absent/no_answer/not_entered/invalid_score/invalid_duration'),
]
print("\n[数据字典]")
for f, desc, t, unit in data_dict:
    print(f"  {f:14s} {desc:12s} {t:6s} {unit}")

# ---------- 10. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
# 左：清洗前后 score 分布
raw_s = [r['score'] for r in raw if r['score'] is not None]
cln_s = [r['score'] for r in clean if r['score'] is not None]
axes[0].hist(raw_s, bins=20, alpha=0.6, label='清洗前', color='#d62728')
axes[0].hist(cln_s, bins=20, alpha=0.6, label='清洗后', color='#1f77b4')
axes[0].set_title('分数分布：清洗前后对比（模拟数据）')
axes[0].set_xlabel('分数'); axes[0].set_ylabel('频数'); axes[0].legend()

# 右：各状态记录数
statuses = ['normal', 'absent', 'no_answer', 'not_entered', 'invalid_score', 'invalid_duration']
cnt = [sum(1 for r in clean if r['status'] == s) for s in statuses]
axes[1].bar(range(len(statuses)), cnt, color='#2ca02c')
axes[1].set_xticks(range(len(statuses)))
axes[1].set_xticklabels(statuses, rotation=30, ha='right')
axes[1].set_title('清洗后记录状态分布（模拟数据）')
axes[1].set_ylabel('记录数')
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[输出] figure.png 已保存")

# ---------- 11. 落盘 ----------
with open('clean_scores.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in clean:
        w.writerow(r)

with open('audit_log.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['step', 'reason', 'rows_before', 'rows_after', 'rows_affected'])
    w.writeheader()
    for a in audit:
        w.writerow(a)

with open('data_dictionary.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['字段', '说明', '类型', '单位/口径'])
    for row in data_dict:
        w.writerow(row)

print("[输出] clean_scores.csv / audit_log.csv / data_dictionary.csv 已保存")
print("\n[陷阱规避] 未删除缺失行(仅标记)；未用均值填补；所有修改均记录于 audit_log。")