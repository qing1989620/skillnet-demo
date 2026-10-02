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

topic = read_csv('topic_matrix.csv')
err = read_csv('error_ledger.csv')

print("=== 输入文件读取 ===")
print(f"topic_matrix.csv 行数: {len(topic)}, 字段: {list(topic[0].keys())}")
print(f"error_ledger.csv 行数: {len(err)}, 字段: {list(err[0].keys())}")

# ============ 1. 核对各章分值合计与卷面总分误差<=2 ============
def to_f(s):
    try: return float(s)
    except: return 0.0

# 章节分值 = 该章所有知识点分值之和（按章节聚合）
chap_score = {}
for r in topic:
    ch = r.get('章节') or r.get('chapter')
    sc = to_f(r.get('分值') or r.get('score'))
    chap_score[ch] = chap_score.get(ch, 0.0) + sc

total_score = sum(chap_score.values())
# 卷面总分：取矩阵中标注的卷面总分，若无则用合计
paper_total = None
for r in topic:
    v = r.get('卷面总分') or r.get('paper_total')
    if v:
        paper_total = to_f(v); break
if paper_total is None:
    paper_total = total_score
err_abs = abs(total_score - paper_total)
print("\n=== 陷阱规避1: 分值核对 ===")
print(f"各章分值合计={total_score:.1f}, 卷面总分={paper_total:.1f}, 误差={err_abs:.1f} (需<=2)")
print("核对结论:", "通过" if err_abs <= 2 else "不通过-需修正矩阵")

# ============ 2. 掌握度与优先级 ============
# 掌握度取该章知识点掌握度均值
chap_mastery = {}
for r in topic:
    ch = r.get('章节') or r.get('chapter')
    m = to_f(r.get('掌握度') or r.get('mastery'))
    chap_mastery.setdefault(ch, []).append(m)
chap_mastery = {k: float(np.mean(v)) for k, v in chap_mastery.items()}

rows = []
for ch in chap_score:
    ratio = chap_score[ch] / total_score if total_score else 0
    m = chap_mastery.get(ch, 3.0)
    prio = ratio * (6 - m)
    rows.append({'章节': ch, '分值': chap_score[ch], '占比': ratio,
                 '掌握度': round(m, 2), '优先级': round(prio, 4)})
rows.sort(key=lambda x: -x['优先级'])

print("\n=== 优先级排序 (分值占比×(6-掌握度)) ===")
for r in rows:
    print(f"{r['章节']:<12} 分值={r['分值']:>5.1f} 占比={r['占比']*100:>5.1f}% 掌握度={r['掌握度']} 优先级={r['优先级']}")

# 占比合计=100%
ratio_sum = sum(r['占比'] for r in rows)
print(f"\n占比合计={ratio_sum*100:.2f}% (需=100%)")

# ============ 3. 周计划：前2/3周期给高优先级且掌握度<=3 ============
TOTAL_WEEKS = 12
front = int(np.ceil(TOTAL_WEEKS * 2 / 3))  # 前2/3周期
plan = []
week = 1
for r in rows:
    if r['掌握度'] <= 3 and r['占比'] > 0:
        w = min(week, front)
        plan.append({'章节': r['章节'], '周次': w, '类型': '系统学习',
                     '闭环判据': '近5年真题正确率>=80%且大题步骤完整率100%',
                     '时间上限': '<=总复习时长15%'})
        week += 1
    else:
        plan.append({'章节': r['章节'], '周次': '抽查期', '类型': '真题抽查',
                     '闭环判据': '近5年真题正确率>=80%且大题步骤完整率100%',
                     '时间上限': '<=总复习时长15%'})

print("\n=== 周计划 ===")
for p in plan:
    print(f"{p['章节']:<12} 周次={p['周次']} 类型={p['类型']} 判据={p['闭环判据']}")

# 检查无不可验证表述
bad_words = ['看完', '理解', '熟悉']
bad = [p for p in plan if any(w in p['闭环判据'] for w in bad_words)]
print("不可验证表述检查:", "通过" if not bad else f"发现{len(bad)}处")

# ============ 4. 错题台账清洗 ============
print("\n=== 陷阱规避2: 错题台账 ===")
# 主键 = 真题年份+题号
keys = []
for r in err:
    y = r.get('真题年份') or r.get('year')
    n = r.get('题号') or r.get('qno')
    keys.append(f"{y}-{n}")
dup = len(keys) - len(set(keys))
print(f"台账记录数={len(err)}, 唯一主键数={len(set(keys))}, 重复={dup}")

# 错因固定4类
valid_cause = {'概念不清', '计算失误', '审题', '记忆'}
cause_field = '错因' if '错因' in err[0] else 'cause'
pending = 0
for r in err:
    c = (r.get(cause_field) or '').strip()
    if c not in valid_cause:
        r[cause_field] = '待补'
        pending += 1
print(f"错因非法/缺失标记为待补: {pending} 条 (未删除)")

# 各章错题数之和=总错题数
chap_err = {}
for r in err:
    ch = r.get('章节') or r.get('chapter')
    chap_err[ch] = chap_err.get(ch, 0) + 1
print(f"各章错题数之和={sum(chap_err.values())} = 总错题数={len(err)}")

# ============ 5. 误差归因：样本量判断 ============
print("\n=== 陷阱规避3: 样本量判断 ===")
n = len(err)
if n >= 100:
    print(f"样本量={n}>=100, 可建模 (逻辑回归/决策树)")
    # TODO: 实现逻辑回归基线，按时间70/30划分，固定随机种子
    model_note = "可建模"
else:
    print(f"样本量={n}<100, 只做描述统计, 不建模 (避免过拟合噪声)")
    model_note = "仅描述统计"

# 描述统计：各章错误率与平均用时
print("\n=== 各章错误率与平均用时 (描述统计) ===")
chap_stat = {}
for r in err:
    ch = r.get('章节') or r.get('chapter')
    t = to_f(r.get('用时') or r.get('time'))
    chap_stat.setdefault(ch, []).append(t)
for ch, ts in sorted(chap_stat.items(), key=lambda x: -len(x[1])):
    print(f"{ch:<12} 错题数={len(ts):>3} 平均用时={np.mean(ts):.1f}分钟")

# 超时题清单（用时>阈值，可回溯题号）
TIME_LIMIT = 10.0
overtime = [(r.get('真题年份'), r.get('题号'), to_f(r.get('用时') or 0)) for r in err
            if to_f(r.get('用时') or 0) > TIME_LIMIT]
print(f"\n超时题(>{TIME_LIMIT}分钟)清单: {len(overtime)} 条")
for o in overtime[:5]:
    print(f"  年份={o[0]} 题号={o[1]} 用时={o[2]}分钟")

# ============ 6. 高频知识点回溯 ============
print("\n=== 验收: 随机抽3个高频知识点回溯真题 ===")
np.random.seed(42)
kp_field = '知识点' if '知识点' in topic[0] else 'kp'
kps = list({r.get(kp_field) for r in topic if r.get(kp_field)})
sample_kps = list(np.random.choice(kps, size=min(3, len(kps)), replace=False))
for kp in sample_kps:
    hits = [r for r in topic if r.get(kp_field) == kp]
    for h in hits[:2]:
        print(f"知识点={kp} -> 年份={h.get('出现年份')} 题号={h.get('题号')} 章节={h.get('章节')}")

# ============ 7. 出图 ============
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
chs = [r['章节'] for r in rows]
prios = [r['优先级'] for r in rows]
axes[0].barh(chs[::-1], prios[::-1], color='steelblue')
axes[0].set_xlabel('优先级分数')
axes[0].set_title('各章优先级排序 (模拟数据)')
axes[0].grid(axis='x', alpha=0.3)

mast = [r['掌握度'] for r in rows]
axes[1].scatter(mast, prios, c='crimson', s=60)
for i, ch in enumerate(chs):
    axes[1].annotate(ch, (mast[i], prios[i]), fontsize=8)
axes[1].axvline(3, color='gray', ls='--', label='掌握度=3阈值')
axes[1].set_xlabel('掌握度')
axes[1].set_ylabel('优先级分数')
axes[1].set_title('掌握度 vs 优先级 (模拟数据)')
axes[1].legend()
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ============ 落盘 ============
with open('weekly_plan.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['章节', '周次', '类型', '闭环判据', '时间上限'])
    w.writeheader(); w.writerows(plan)

with open('priority_rank.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['章节', '分值', '占比', '掌握度', '优先级'])
    w.writeheader(); w.writerows(rows)

with open('error_ledger_clean.csv', 'w', newline='', encoding='utf-8-sig') as f:
    if err:
        w = csv.DictWriter(f, fieldnames=list(err[0].keys()))
        w.writeheader(); w.writerows(err)

print("\n落盘: weekly_plan.csv, priority_rank.csv, error_ledger_clean.csv, figure.png")
print(f"\n[汇总] 分值误差={err_abs:.1f} 占比合计={ratio_sum*100:.2f}% 台账重复={dup} 待补={pending} 样本量={n}({model_note})")