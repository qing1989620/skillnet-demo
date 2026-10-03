import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv, os

# ============ 读取前序产物（真实文件） ============
def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

exam_matrix = read_csv('exam_matrix.csv')      # 章节-知识点-题型-年份-分值-掌握度
paper_scores = read_csv('paper_scores.csv')    # 套卷成绩
error_ledger = read_csv('error_ledger.csv')    # 错题台账

print("=== 输入文件读取 ===")
print(f"exam_matrix 行数: {len(exam_matrix)}")
print(f"paper_scores 行数: {len(paper_scores)}")
print(f"error_ledger 行数: {len(error_ledger)}")

# ============ 1. 章节分值占比 & 掌握度聚合 ============
def to_float(x):
    try: return float(x)
    except: return 0.0

chapters = {}
for r in exam_matrix:
    ch = r.get('章节') or r.get('chapter')
    score = to_float(r.get('分值') or r.get('score'))
    mast = to_float(r.get('掌握度') or r.get('mastery'))
    if ch not in chapters:
        chapters[ch] = {'score': 0.0, 'mast_sum': 0.0, 'n': 0}
    chapters[ch]['score'] += score
    chapters[ch]['mast_sum'] += mast
    chapters[ch]['n'] += 1

total_score = sum(v['score'] for v in chapters.values())
print(f"\n=== 章节分值核对 ===")
print(f"各章分值合计: {total_score:.1f}")
# 卷面总分（从 paper_scores 推断或默认100）
paper_total = 100.0
if paper_scores:
    for k in paper_scores[0]:
        if '总分' in k or 'total' in k.lower():
            paper_total = to_float(paper_scores[0][k]); break
err = abs(total_score - paper_total)
print(f"卷面总分: {paper_total:.1f}, 误差: {err:.1f} -> {'通过(≤2)' if err<=2 else '超限!'}")

# 占比
for ch in chapters:
    chapters[ch]['ratio'] = chapters[ch]['score'] / total_score if total_score else 0
    chapters[ch]['mast'] = chapters[ch]['mast_sum'] / chapters[ch]['n'] if chapters[ch]['n'] else 0

ratio_sum = sum(v['ratio'] for v in chapters.values())
print(f"各章分值占比合计: {ratio_sum*100:.2f}% -> {'通过(=100%)' if abs(ratio_sum-1)<1e-6 else '异常'}")

# ============ 2. 优先级分数 = 占比 × (6 - 掌握度) ============
for ch, v in chapters.items():
    v['priority'] = v['ratio'] * (6 - v['mast'])

ranked = sorted(chapters.items(), key=lambda kv: kv[1]['priority'], reverse=True)
print("\n=== 优先级排序（降序） ===")
for ch, v in ranked:
    print(f"{ch}: 占比={v['ratio']*100:.1f}% 掌握度={v['mast']:.1f} 优先级={v['priority']:.3f}")

# ============ 3. 周计划：前2/3周期给高优先级低掌握度章节 ============
TOTAL_WEEKS = 12
front_weeks = int(TOTAL_WEEKS * 2 / 3)   # 前2/3周期
print(f"\n=== 周计划（总{TOTAL_WEEKS}周，前{front_weeks}周为强化期） ===")

# 单章时间上限 ≤ 总复习时长15%
MAX_TIME_RATIO = 0.15
plan = []
front_chs = [ch for ch, v in ranked if v['mast'] <= 3]
back_chs  = [ch for ch, v in ranked if v['mast'] >= 4]

# 分配周数：按优先级权重
def alloc_weeks(chs, weeks):
    if not chs: return {}
    wsum = sum(chapters[c]['priority'] for c in chs)
    raw = {c: chapters[c]['priority']/wsum*weeks for c in chs}
    # 单章时间上限15%
    cap = TOTAL_WEEKS * MAX_TIME_RATIO
    alloc = {c: min(raw[c], cap) for c in chs}
    return alloc

front_alloc = alloc_weeks(front_chs, front_weeks)
back_alloc  = alloc_weeks(back_chs, TOTAL_WEEKS - front_weeks)

print("强化期章节（掌握度≤3）:")
for ch, w in sorted(front_alloc.items(), key=lambda kv:-kv[1]):
    print(f"  {ch}: {w:.2f}周 ({w/TOTAL_WEEKS*100:.1f}% 总时长) 闭环判据: 近5年真题正确率≥80% 且 大题步骤完整率100%")
print("抽查期章节（掌握度≥4，仅真题抽查）:")
for ch, w in sorted(back_alloc.items(), key=lambda kv:-kv[1]):
    print(f"  {ch}: {w:.2f}周 ({w/TOTAL_WEEKS*100:.1f}% 总时长) 闭环判据: 近5年真题正确率≥80%")

# 单章时间上限检查
over = [ch for ch, w in {**front_alloc, **back_alloc}.items() if w/TOTAL_WEEKS > MAX_TIME_RATIO + 1e-9]
print(f"单章时间占比超15%的章节: {over if over else '无 -> 通过'}")

# ============ 4. 错题台账检查（陷阱规避） ============
print("\n=== 错题台账审计 ===")
if error_ledger:
    keys = []
    for r in error_ledger:
        y = r.get('真题年份') or r.get('year')
        n = r.get('题号') or r.get('qno')
        keys.append(f"{y}-{n}")
    dup = len(keys) - len(set(keys))
    print(f"主键(年份+题号)总数={len(keys)}, 唯一={len(set(keys))}, 重复={dup} -> {'通过' if dup==0 else '有重复!'}")

    # 错因固定4类
    valid_causes = {'概念不清','计算失误','审题','记忆','待补'}
    causes = [r.get('错因') or r.get('cause') for r in error_ledger]
    bad = [c for c in causes if c not in valid_causes]
    print(f"错因非法值数量: {len(bad)} -> {'通过' if not bad else '存在自由文本!'}")
    from collections import Counter
    print(f"错因分布: {dict(Counter(causes))}")

    # 各章错题数之和 = 总错题数
    ch_err = Counter(r.get('章节') or r.get('chapter') for r in error_ledger)
    print(f"各章错题数之和={sum(ch_err.values())}, 总错题数={len(error_ledger)} -> {'通过' if sum(ch_err.values())==len(error_ledger) else '异常'}")
else:
    print("error_ledger 为空，跳过")

# ============ 5. 套卷成绩收敛检查 ============
print("\n=== 套卷成绩收敛 ===")
if paper_scores:
    accs = []
    for r in paper_scores:
        for k in r:
            if '正确率' in k or 'acc' in k.lower():
                accs.append(to_float(r[k])); break
    if len(accs) >= 3:
        last3 = accs[-3:]
        print(f"最近3套正确率: {[f'{a:.1f}%' for a in last3]}")
        print(f"波动(极差): {max(last3)-min(last3):.1f}% -> {'收敛(≤5%)' if max(last3)-min(last3)<=5 else '未收敛'}")
        print(f"均≥目标线75%: {'是' if min(last3)>=75 else '否'}")
    else:
        print(f"套卷数={len(accs)}，不足3套，无法判定收敛")
else:
    print("paper_scores 为空")

# ============ 6. 出图：优先级 vs 掌握度 ============
fig, ax = plt.subplots(figsize=(9, 5))
chs = [c for c, _ in ranked]
pris = [chapters[c]['priority'] for c in chs]
masts = [chapters[c]['mast'] for c in chs]
colors = ['#d62728' if m <= 3 else '#1f77b4' for m in masts]
bars = ax.barh(chs[::-1], pris[::-1], color=colors[::-1])
for i, (p, m) in enumerate(zip(pris[::-1], masts[::-1])):
    ax.text(p + 0.005, i, f"掌握度{m:.1f}", va='center', fontsize=9)
ax.set_xlabel('优先级分数 = 分值占比 × (6 − 掌握度)')
ax.set_title('章节优先级排序（红=掌握度≤3需强化，蓝=≥4仅抽查）')
ax.axvline(0, color='gray', lw=0.5)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ============ 落盘 ============
with open('priority_plan.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['章节','分值占比','掌握度','优先级分数','分配周数','阶段','闭环判据'])
    for ch, v in ranked:
        if ch in front_alloc:
            wk, stage = front_alloc[ch], '强化期'
        else:
            wk, stage = back_alloc.get(ch, 0), '抽查期'
        w.writerow([ch, f"{v['ratio']*100:.2f}%", f"{v['mast']:.1f}",
                    f"{v['priority']:.4f}", f"{wk:.2f}", stage,
                    '近5年真题正确率≥80%且大题步骤完整率100%'])
print("已保存: priority_plan.csv")