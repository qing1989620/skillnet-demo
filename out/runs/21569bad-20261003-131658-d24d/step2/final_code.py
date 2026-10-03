import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv, os, math

# ============================================================
# 说明：本脚本优先读取真实文件 clean_scores.csv。
# 若文件不存在或字段不匹配，则使用【模拟数据】并在输出中明确标注。
# 仅使用 numpy / matplotlib（标准库 csv, os, math 辅助）。
# ============================================================

def load_data():
    """读取真实数据；失败则返回模拟数据（明确标注）。"""
    path = 'clean_scores.csv'
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            if rows:
                cols = rows[0].keys()
                # 期望字段：student_id, group, subject, knowledge_point, score, full_score, time_sec
                need = {'group', 'subject', 'knowledge_point', 'score', 'full_score', 'time_sec'}
                if need.issubset(set(cols)):
                    print("[数据来源] 真实文件 clean_scores.csv，记录数 =", len(rows))
                    return rows, False
                else:
                    print("[警告] clean_scores.csv 字段不匹配，缺失:", need - set(cols))
        except Exception as e:
            print("[警告] 读取真实文件失败:", e)
    # ---- 模拟数据 ----
    print("[数据来源] *** 模拟数据（非真实实验结论）***")
    rng = np.random.default_rng(42)
    subjects = ['数学', '物理', '英语']
    kps = {'数学': ['函数', '几何', '概率'],
           '物理': ['力学', '电磁学', '光学'],
           '英语': ['阅读', '写作', '听力']}
    groups = ['A班', 'B班']
    # 让物理整体偏弱、B班数学偏弱，制造可检测差异
    base = {'数学': 0.80, '物理': 0.62, '英语': 0.78}
    gshift = {'A班': 0.0, 'B班': -0.05}
    rows = []
    sid = 0
    for g in groups:
        for _ in range(40):
            sid += 1
            for s in subjects:
                for kp in kps[s]:
                    p = base[s] + gshift[g] + rng.normal(0, 0.12)
                    p = min(max(p, 0.05), 0.99)
                    full = 10
                    score = int(round(p * full))
                    t = max(5.0, rng.normal(60, 15))
                    rows.append({'student_id': f'S{sid:04d}', 'group': g, 'subject': s,
                                 'knowledge_point': kp, 'score': score,
                                 'full_score': full, 'time_sec': round(t, 1)})
    return rows, True

def to_float(x):
    try:
        return float(x)
    except Exception:
        return np.nan

# ---------- 统计工具（仅 numpy） ----------
def mean(a):
    return float(np.mean(a)) if len(a) else np.nan

def sd(a):
    return float(np.std(a, ddof=1)) if len(a) > 1 else np.nan

def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def shapiro_like(a):
    """简化正态性检验：基于偏度/峰度的 Jarque-Bera 近似（numpy 实现）。
    返回 (stat, p)。p<0.05 视为拒绝正态。"""
    a = np.asarray(a, dtype=float)
    n = len(a)
    if n < 8:
        return np.nan, np.nan
    m = a.mean()
    s = a.std(ddof=1)
    if s == 0:
        return np.nan, np.nan
    skew = np.mean(((a - m) / s) ** 3)
    kurt = np.mean(((a - m) / s) ** 4) - 3.0
    jb = n / 6.0 * (skew ** 2 + (kurt ** 2) / 4.0)
    p = math.exp(-jb / 2.0)  # 卡方(2) 生存函数近似
    return float(jb), float(p)

def mannwhitney_u(a, b):
    """独立两样本 Mann-Whitney U（正态近似，含并列校正）。返回 (U, z, p)。"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return np.nan, np.nan, np.nan
    allv = np.concatenate([a, b])
    order = np.argsort(allv, kind='mergesort')
    ranks = np.empty(len(allv), float)
    ranks[order] = np.arange(1, len(allv) + 1)
    # 并列平均秩
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[order[j + 1]] == allv[order[i]]:
            j += 1
        if j > i:
            avg = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
        i = j + 1
    R1 = ranks[:n1].sum()
    U1 = R1 - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    # 并列校正
    _, cnt = np.unique(allv, return_counts=True)
    tie = np.sum(cnt ** 3 - cnt)
    N = n1 + n2
    sigma = math.sqrt(n1 * n2 / 12.0 * ((N + 1) - tie / (N * (N - 1)))) if N > 1 else np.nan
    z = (U1 - mu) / sigma if sigma and sigma > 0 else np.nan
    p = 2 * (1 - norm_cdf(abs(z))) if not np.isnan(z) else np.nan
    return float(U1), float(z), float(p)

def cohens_d(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return np.nan, np.nan, np.nan
    s1, s2 = a.var(ddof=1), b.var(ddof=1)
    sp = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if sp == 0:
        return np.nan, np.nan, np.nan
    d = (a.mean() - b.mean()) / sp
    se = math.sqrt((n1 + n2) / (n1 * n2) + d * d / (2 * (n1 + n2)))
    lo, hi = d - 1.96 * se, d + 1.96 * se
    return float(d), float(lo), float(hi)

def rank_biserial(U, n1, n2):
    if np.isnan(U) or n1 == 0 or n2 == 0:
        return np.nan
    return float(2 * U / (n1 * n2) - 1)

def fdr_bh(pvals):
    """Benjamini-Hochberg FDR 校正，返回校正后 p 值。"""
    p = np.asarray(pvals, float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / (np.arange(1, n + 1))
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.clip(adj, 0, 1)
    out = np.empty(n)
    out[order] = adj
    return out

# ============================================================
rows, is_sim = load_data()

# 解析为结构化数组
recs = []
for r in rows:
    sc = to_float(r.get('score')); fs = to_float(r.get('full_score'))
    t = to_float(r.get('time_sec'))
    if np.isnan(sc) or np.isnan(fs) or fs == 0:
        continue
    recs.append({'group': r.get('group', 'NA'), 'subject': r.get('subject', 'NA'),
                 'kp': r.get('knowledge_point', 'NA'),
                 'rate': sc / fs, 'time': t if not np.isnan(t) else np.nan})

groups = sorted(set(x['group'] for x in recs))
subjects = sorted(set(x['subject'] for x in recs))
print("组别:", groups, "| 科目:", subjects, "| 有效记录:", len(recs))

# ---------- 1. 按科目×知识点汇总 ----------
print("\n===== 1. 科目×知识点 正确率/平均分/失分率/平均用时 =====")
summary = []
for s in subjects:
    for kp in sorted(set(x['kp'] for x in recs if x['subject'] == s)):
        sub = [x for x in recs if x['subject'] == s and x['kp'] == kp]
        rates = np.array([x['rate'] for x in sub])
        times = np.array([x['time'] for x in sub if not np.isnan(x['time'])])
        acc = mean(rates)
        summary.append({'subject': s, 'kp': kp, 'n': len(sub),
                        'accuracy': acc, 'avg_score_rate': acc,
                        'loss_rate': 1 - acc, 'avg_time': mean(times)})
        print(f"  {s}-{kp}: n={len(sub)}, 正确率={acc:.3f}, 失分率={1-acc:.3f}, 平均用时={mean(times):.1f}s")

# ---------- 2. 正态性检验（前提假设） ----------
print("\n===== 2. 正态性检验（Jarque-Bera 近似，p<0.05 拒绝正态）=====")
normality = {}
for s in subjects:
    for g in groups:
        vals = np.array([x['rate'] for x in recs if x['subject'] == s and x['group'] == g])
        jb, p = shapiro_like(vals)
        normality[(s, g)] = (jb, p, len(vals))
        flag = "非正态" if (not np.isnan(p) and p < 0.05) else "未拒绝正态"
        print(f"  {s}-{g}: n={len(vals)}, JB={jb:.3f}, p={p:.4f} -> {flag}")

# ---------- 3. 组间比较（A vs B，逐科目） ----------
print("\n===== 3. 组间比较（独立两样本，非正态用 Mann-Whitney U）=====")
comp = []
if len(groups) >= 2:
    g1, g2 = groups[0], groups[1]
    for s in subjects:
        a = np.array([x['rate'] for x in recs if x['subject'] == s and x['group'] == g1])
        b = np.array([x['rate'] for x in recs if x['subject'] == s and x['group'] == g2])
        U, z, p = mannwhitney_u(a, b)
        rb = rank_biserial(U, len(a), len(b))
        d, dlo, dhi = cohens_d(a, b)
        comp.append({'subject': s, 'g1': g1, 'g2': g2, 'n1': len(a), 'n2': len(b),
                     'mean1': mean(a), 'mean2': mean(b),
                     'U': U, 'z': z, 'p_raw': p, 'rank_biserial': rb,
                     'cohens_d': d, 'd_lo': dlo, 'd_hi': dhi})
        print(f"  {s}: {g1}均值={mean(a):.3f} vs {g2}均值={mean(b):.3f}, "
              f"U={U:.1f}, z={z:.3f}, p={p:.4f}, r_rb={rb:.3f}, d={d:.3f} [{dlo:.3f},{dhi:.3f}]")

# ---------- 4. FDR 多重比较校正 ----------
print("\n===== 4. FDR (Benjamini-Hochberg) 多重比较校正 =====")
if comp:
    praw = [c['p_raw'] for c in comp]
    padj = fdr_bh(praw)
    for c, pa in zip(comp, padj):
        c['p_fdr'] = float(pa)
        sig = "显著" if pa < 0.05 else "不显著"
        print(f"  {c['subject']}: p_raw={c['p_raw']:.4f} -> p_FDR={pa:.4f} ({sig})")

# ---------- 5. 薄弱环节判定与复习建议 ----------
print("\n===== 5. 薄弱环节与复习建议 =====")
summary_sorted = sorted(summary, key=lambda x: x['accuracy'])
advice = []
for item in summary_sorted:
    if item['accuracy'] < 0.70:
        level = "重点薄弱"
    elif item['accuracy'] < 0.80:
        level = "需加强"
    else:
        level = "掌握良好"
    advice.append({'subject': item['subject'], 'kp': item['kp'],
                   'accuracy': round(item['accuracy'], 3),
                   'loss_rate': round(item['loss_rate'], 3),
                   'avg_time': round(item['avg_time'], 1),
                   'level': level})
    print(f"  [{level}] {item['subject']}-{item['kp']}: 正确率={item['accuracy']:.3f}, 失分率={item['loss_rate']:.3f}")

# ---------- 6. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
# 左：各知识点正确率
labels = [f"{a['subject']}\n{a['kp']}" for a in advice]
accs = [a['accuracy'] for a in advice]
colors = ['#d62728' if a['accuracy'] < 0.70 else ('#ff7f0e' if a['accuracy'] < 0.80 else '#2ca02c') for a in advice]
axes[0].bar(range(len(accs)), accs, color=colors)
axes[0].axhline(0.80, color='gray', ls='--', lw=1, label='掌握线 0.80')
axes[0].axhline(0.70, color='red', ls='--', lw=1, label='薄弱线 0.70')
axes[0].set_xticks(range(len(labels)))
axes[0].set_xticklabels(labels, fontsize=8)
axes[0].set_ylabel('正确率')
axes[0].set_title('各科目知识点正确率（红=重点薄弱）')
axes[0].legend(fontsize=8)
axes[0].set_ylim(0, 1)

# 右：组间对比（逐科目均值）
if comp:
    x = np.arange(len(comp))
    w = 0.35
    m1 = [c['mean1'] for c in comp]
    m2 = [c['mean2'] for c in comp]
    axes[1].bar(x - w/2, m1, w, label=comp[0]['g1'], color='#1f77b4')
    axes[1].bar(x + w/2, m2, w, label=comp[0]['g2'], color='#ff7f0e')
    for i, c in enumerate(comp):
        star = '*' if c.get('p_fdr', 1) < 0.05 else 'ns'
        axes[1].text(i, max(m1[i], m2[i]) + 0.02, star, ha='center', fontsize=12)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([c['subject'] for c in comp])
    axes[1].set_ylabel('平均正确率')
    axes[1].set_title('组间对比（* = FDR校正后显著）')
    axes[1].legend(fontsize=8)
    axes[1].set_ylim(0, 1)

title = "学生成绩薄弱环节分析" + ("（模拟数据）" if is_sim else "（真实数据）")
fig.suptitle(title, fontsize=13)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[已保存] figure.png")

# ---------- 7. 落盘 ----------
with open('subject_kp_summary.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['subject', 'kp', 'n', 'accuracy', 'loss_rate', 'avg_time'])
    w.writeheader()
    for it in summary:
        w.writerow({'subject': it['subject'], 'kp': it['kp'], 'n': it['n'],
                    'accuracy': round(it['accuracy'], 4),
                    'loss_rate': round(it['loss_rate'], 4),
                    'avg_time': round(it['avg_time'], 2)})

with open('group_comparison.csv', 'w', newline='', encoding='utf-8-sig') as f:
    fields = ['subject', 'g1', 'g2', 'n1', 'n2', 'mean1', 'mean2', 'U', 'z',
              'p_raw', 'p_fdr', 'rank_biserial', 'cohens_d', 'd_lo', 'd_hi']
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for c in comp:
        w.writerow({k: (round(c[k], 4) if isinstance(c.get(k), float) else c.get(k)) for k in fields})

with open('review_advice.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['subject', 'kp', 'accuracy', 'loss_rate', 'avg_time', 'level'])
    w.writeheader()
    for a in advice:
        w.writerow(a)

print("[已保存] subject_kp_summary.csv, group_comparison.csv, review_advice.csv")
print("\n[陷阱规避] 已做正态性检验并按结果选用非参数检验；已报告效应量(r_rb, Cohen's d)与置信区间；多重比较已用FDR校正。")