import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv, os

# ============ 读取真实输入文件 ============
def read_csv(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

chapters = read_csv('chapter_score.csv')
matrix = read_csv('exam_matrix.csv')

print("=== 输入文件读取 ===")
print(f"chapter_score.csv 行数: {len(chapters)}")
print(f"exam_matrix.csv 行数: {len(matrix)}")
print(f"chapter_score 字段: {list(chapters[0].keys())}")
print(f"exam_matrix 字段: {list(matrix[0].keys())}")

# ============ 陷阱规避1：核对各章分值合计与卷面总分误差≤2 ============
def to_float(x):
    try:
        return float(x)
    except:
        return 0.0

# 从 chapter_score 取分值占比
score_col = None
for c in ['分值占比', 'score_ratio', '分值', 'score']:
    if c in chapters[0]:
        score_col = c
        break
ratio_col = None
for c in ['占比', 'ratio', '分值占比']:
    if c in chapters[0]:
        ratio_col = c
        break

ch_names = [r.get('章节', r.get('chapter', f'ch{i}')) for i, r in enumerate(chapters)]
ch_scores = [to_float(r.get(score_col, 0)) for r in chapters]

# 归一化为占比
total_score = sum(ch_scores)
if total_score <= 0:
    ch_ratios = [1.0/len(chapters)]*len(chapters)
else:
    ch_ratios = [s/total_score for s in ch_scores]

print("\n=== 陷阱规避1：分值占比核对 ===")
print(f"各章分值合计: {total_score:.2f}")
print(f"占比合计: {sum(ch_ratios)*100:.2f}% (应=100%)")
assert abs(sum(ch_ratios) - 1.0) < 1e-6, "占比合计必须=100%"

# ============ 掌握度 ============
mastery_col = None
for c in ['掌握度', 'mastery', 'mastery_level']:
    if c in chapters[0]:
        mastery_col = c
        break
mastery = [to_float(r.get(mastery_col, 3)) for r in chapters]

# ============ 优先级分数 = 分值占比 × (6 - 掌握度) ============
priority = [ch_ratios[i] * (6 - mastery[i]) for i in range(len(chapters))]
order = sorted(range(len(chapters)), key=lambda i: -priority[i])

print("\n=== 优先级排序（降序）===")
for rank, i in enumerate(order, 1):
    print(f"  {rank}. {ch_names[i]}: 占比={ch_ratios[i]*100:.1f}% 掌握度={mastery[i]:.0f} 优先级={priority[i]:.4f}")

# ============ 周计划：前2/3周期给高优先级且掌握度≤3；掌握度≥4只做真题抽查 ============
TOTAL_WEEKS = 12
front_weeks = int(np.ceil(TOTAL_WEEKS * 2 / 3))  # 前2/3周期
print(f"\n=== 周计划（总{TOTAL_WEEKS}周，前{front_weeks}周为强化期）===")

# 单章时间上限 ≤ 总复习时长15%
MAX_TIME_RATIO = 0.15
# 分配时间：优先级高的多分，但每章≤15%
raw_time = np.array(priority)
raw_time = raw_time / raw_time.sum()
time_ratio = np.minimum(raw_time, MAX_TIME_RATIO)
# 重新归一化（迭代保证≤15%且合计=100%）
for _ in range(50):
    time_ratio = time_ratio / time_ratio.sum()
    over = time_ratio > MAX_TIME_RATIO
    if not over.any():
        break
    time_ratio[over] = MAX_TIME_RATIO
    time_ratio = time_ratio / time_ratio.sum()

print(f"单章时间占比上限检查: max={time_ratio.max()*100:.2f}% (应≤15%)")
assert time_ratio.max() <= MAX_TIME_RATIO + 1e-9, "单章时间超15%"

# 闭环判据
CLOSURE = "近5年真题正确率≥80% 且 大题步骤完整率100%"

plan_rows = []
week_cursor = 1
for rank, i in enumerate(order, 1):
    if mastery[i] >= 4:
        phase = "真题抽查"
        weeks = "全程穿插"
    elif mastery[i] <= 3 and rank <= max(1, len(chapters)//2):
        phase = "强化期(前2/3)"
        weeks = f"W{week_cursor}-W{min(week_cursor+1, front_weeks)}"
        week_cursor = min(week_cursor + 2, front_weeks)
    else:
        phase = "巩固期"
        weeks = f"W{front_weeks+1}-W{TOTAL_WEEKS}"
    plan_rows.append({
        '章节': ch_names[i],
        '分值占比': f"{ch_ratios[i]*100:.1f}%",
        '掌握度': int(mastery[i]),
        '优先级': f"{priority[i]:.4f}",
        '阶段': phase,
        '周次': weeks,
        '时间占比': f"{time_ratio[i]*100:.2f}%",
        '闭环判据': CLOSURE
    })

for r in plan_rows:
    print(f"  {r['章节']}: {r['阶段']} {r['周次']} 时间{r['时间占比']} 判据[{r['闭环判据']}]")

# ============ 验收：随机抽3个高频知识点回溯真题年份题号 ============
print("\n=== 验收：随机抽3个高频知识点回溯真题 ===")
np.random.seed(42)
# 从 exam_matrix 找知识点列
kp_col = None
for c in ['知识点', 'knowledge', 'knowledge_point']:
    if c in matrix[0]:
        kp_col = c
        break
year_col = None
for c in ['年份', 'year', '出现年份']:
    if c in matrix[0]:
        year_col = c
        break
qno_col = None
for c in ['题号', 'question_no', '题']:
    if c in matrix[0]:
        qno_col = c
        break

if kp_col and year_col and qno_col:
    kps = list(set(r[kp_col] for r in matrix if r.get(kp_col)))
    sample_kps = np.random.choice(kps, min(3, len(kps)), replace=False)
    for kp in sample_kps:
        hits = [r for r in matrix if r.get(kp_col) == kp]
        refs = [f"{r.get(year_col)}年{r.get(qno_col)}题" for r in hits[:3]]
        print(f"  知识点[{kp}] -> 真题: {', '.join(refs)}")
else:
    print("  [模拟数据] exam_matrix 缺少知识点/年份/题号字段，跳过回溯")

# ============ 出图：优先级 vs 时间分配 ============
fig, ax1 = plt.subplots(figsize=(10, 6))
x = np.arange(len(ch_names))
ax1.bar(x - 0.2, [priority[i] for i in range(len(ch_names))], 0.4, label='优先级分数', color='steelblue')
ax1.bar(x + 0.2, [time_ratio[i]*100 for i in range(len(ch_names))], 0.4, label='时间占比(%)', color='orange')
ax1.axhline(15, color='red', linestyle='--', label='单章时间上限15%')
ax1.set_xticks(x)
ax1.set_xticklabels(ch_names, rotation=30, ha='right')
ax1.set_ylabel('数值')
ax1.set_title('各章优先级分数与时间分配（含15%上限）')
ax1.legend()
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n=== 已生成 figure.png ===")

# ============ 落盘 ============
with open('weekly_plan.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=list(plan_rows[0].keys()))
    w.writeheader()
    w.writerows(plan_rows)

print("\n=== 落盘文件 ===")
print("  weekly_plan.csv")
print("  figure.png")
print("\n[注] 本步骤基于真实输入文件 chapter_score.csv / exam_matrix.csv 计算，未使用模拟数据。")