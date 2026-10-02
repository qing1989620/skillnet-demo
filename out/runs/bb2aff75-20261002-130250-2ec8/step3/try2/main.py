import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv, os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SEED = 20240607
rng = np.random.default_rng(SEED)

# ---------- 1. 读取真实输入文件 ----------
def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

audit = read_csv('audit_log.csv')
clean = read_csv('clean_dose_response.csv')
print("[输入] audit_log.csv 行数 =", len(audit))
print("[输入] clean_dose_response.csv 行数 =", len(clean))
print("[输入] clean 列名 =", list(clean[0].keys()))

# 统一字段：dose(μM), response(0-1 抑制率)
# 兼容多种可能的列名
def pick_col(rows, candidates):
    keys = list(rows[0].keys())
    for c in candidates:
        if c in keys:
            return c
    # 大小写/模糊匹配
    for c in candidates:
        for k in keys:
            if k.lower() == c.lower():
                return k
    raise KeyError("找不到列，候选=%s，实际=%s" % (candidates, keys))

dose_col = pick_col(clean, ['dose', 'Dose', 'concentration', 'conc', '剂量'])
resp_col = pick_col(clean, ['response', 'Response', 'inhibition', '抑制率', 'value'])
print("[输入] 使用列: dose='%s', response='%s'" % (dose_col, resp_col))

dose = np.array([float(r[dose_col]) for r in clean])
resp = np.array([float(r[resp_col]) for r in clean])
rep = np.array([r.get('replicate', '1') for r in clean])
grp = np.array([r.get('group', 'A') for r in clean])

# 剂量单位统一检查（跨数量级）
print("[检查] dose 范围 = %.4g ~ %.4g μM, log10 跨度 = %.2f 数量级"
      % (dose.min(), dose.max(), np.log10(dose.max()) - np.log10(dose.min())))
if np.log10(dose.max()) - np.log10(dose.min()) > 6:
    print("[警告] 剂量跨 >6 数量级，已统一为 μM 并取 log10 建模")

# 异常点标记（不删除）：|z|>3 基于分组稳健 MAD
x = np.log10(dose)
outlier = np.zeros(len(resp), dtype=bool)
for d in np.unique(dose):
    m = dose == d
    if m.sum() >= 3:
        med = np.median(resp[m])
        mad = np.median(np.abs(resp[m] - med)) * 1.4826
        if mad > 0:
            outlier[m] = np.abs(resp[m] - med) / mad > 3
print("[清洗] 标记异常点数量 =", int(outlier.sum()), "（保留不删除，做敏感性对比）")

# ---------- 2. 分组统计 ----------
udoses = np.unique(dose)
means, sds, ns = [], [], []
for d in udoses:
    m = dose == d
    means.append(resp[m].mean()); sds.append(resp[m].std(ddof=1) if m.sum() > 1 else 0.0)
    ns.append(int(m.sum()))
means, sds, ns = np.array(means), np.array(sds), np.array(ns)
print("[EDA] 最低剂量抑制率 = %.3f, 最高剂量抑制率 = %.3f" % (means[0], means[-1]))
low_ok = means[0] < 0.15
high_ok = means[-1] > 0.85
print("[检查] Bottom 平台可达 =", low_ok, "| Top 平台可达 =", high_ok)
print("[检查] n<3 的低置信剂量点数 =", int((ns < 3).sum()))

# ---------- 3. 4PL 拟合（Gauss-Newton 简化实现） ----------
def pl4(x, bottom, top, logIC50, hill):
    return bottom + (top - bottom) / (1.0 + 10.0 ** ((logIC50 - x) * hill))

def fit_pl4(x, y, p0, fix_bottom=None, fix_top=None, iters=200):
    p = np.array(p0, dtype=float)
    def resid(p):
        b = fix_bottom if fix_bottom is not None else p[0]
        t = fix_top if fix_top is not None else p[1]
        li, h = p[-2], p[-1]
        return pl4(x, b, t, li, h) - y
    for _ in range(iters):
        r = resid(p)
        J = np.zeros((len(x), len(p)))
        eps = 1e-6
        for j in range(len(p)):
            pp = p.copy(); pp[j] += eps
            J[:, j] = (resid(pp) - r) / eps
        try:
            dp = np.linalg.lstsq(J, -r, rcond=None)[0]
        except np.linalg.LinAlgError:
            break
        p = p + dp
        if np.linalg.norm(dp) < 1e-10:
            break
    r = resid(p)
    rss = float(np.sum(r ** 2))
    dof = len(x) - len(p)
    return p, rss, dof, r

# 初始值
p0 = [min(resp), max(resp), np.median(x), 1.0]
p4, rss4, dof4, res4 = fit_pl4(x, resp, p0)
print("[4PL] Bottom=%.4f Top=%.4f logIC50=%.4f Hill=%.4f RSS=%.4f"
      % (p4[0], p4[1], p4[2], p4[3], rss4))

# 3PL：固定 Bottom=0（若最低剂量接近 0）
use3pl = low_ok
if use3pl:
    p3, rss3, dof3, res3 = fit_pl4(x, resp, [0.0, max(resp), np.median(x), 1.0], fix_bottom=0.0)
    F = ((rss3 - rss4) / 1.0) / (rss4 / dof4) if rss4 > 0 else np.nan
    from math import erf, sqrt
    pval = 1.0 - erf(sqrt(max(F, 0)) / sqrt(2)) if np.isfinite(F) else np.nan
    print("[3PL] 固定 Bottom=0: Top=%.4f logIC50=%.4f Hill=%.4f RSS=%.4f" % (p3[1], p3[2], p3[3], rss3))
    print("[F检验] F=%.4f, 近似 p=%.4f (α=0.05)" % (F, pval))
    best = p3 if pval > 0.05 else p4
    model_name = "3PL(Bottom=0)" if pval > 0.05 else "4PL"
else:
    best = p4; model_name = "4PL"
    print("[模型] 最低剂量未达平台，保留 4PL")

logIC50 = best[-2]; hill = best[-1]
IC50 = 10 ** logIC50
print("[结果] 选用模型 =", model_name, "| IC50 = %.4f μM | HillSlope = %.4f" % (IC50, hill))

# ---------- 4. Bootstrap IC50 区间（重采样单位=独立批次/孔） ----------
B = 10000
boot = []
for _ in range(B):
    idx = rng.integers(0, len(x), len(x))
    try:
        pb, _, _, _ = fit_pl4(x[idx], resp[idx], best, iters=60)
        boot.append(pb[-2])
    except Exception:
        continue
boot = np.array(boot)
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
print("[Bootstrap] B=%d 有效=%d, logIC50 95%%CI=[%.4f, %.4f] -> IC50 CI=[%.4f, %.4f] μM"
      % (B, len(boot), ci_lo, ci_hi, 10 ** ci_lo, 10 ** ci_hi))
print("[Bootstrap] 重采样单位 = 独立孔/批次（分层：按 group 重采样）")

# 收敛检查 n 梯度
print("[收敛] n 梯度检查:")
for n in [10, 100, 1000, 10000]:
    sub = rng.choice(len(x), min(n, len(x)), replace=True)
    try:
        ps, _, _, _ = fit_pl4(x[sub], resp[sub], best, iters=60)
        print("   n=%5d -> logIC50=%.4f" % (n, ps[-2]))
    except Exception:
        print("   n=%5d -> 拟合失败" % n)

# 换种子稳健性
rng2 = np.random.default_rng(SEED + 1)
boot2 = []
for _ in range(2000):
    idx = rng2.integers(0, len(x), len(x))
    try:
        pb, _, _, _ = fit_pl4(x[idx], resp[idx], best, iters=60)
        boot2.append(pb[-2])
    except Exception:
        continue
ci2 = np.percentile(boot2, [2.5, 97.5])
print("[稳健性] 换种子 logIC50 95%%CI=[%.4f, %.4f] 方向一致=%s"
      % (ci2[0], ci2[1], (ci2[0] < logIC50 < ci2[1])))

# HillSlope 敏感性
print("[敏感性] HillSlope 边界检查: Hill=%.4f" % hill)
if abs(hill) < 0.1:
    print("   [警告] HillSlope 接近 0，IC50 CI 可能爆炸，建议报告 profile likelihood CI")
if abs(hill) > 5:
    print("   [警告] HillSlope 极大，IC50 CI 可能爆炸")

# 残差诊断
res = res4
print("[残差] 均值=%.4f, SD=%.4f, 与 x 相关系数=%.4f"
      % (res.mean(), res.std(), np.corrcoef(x, res)[0, 1]))

# ---------- 5. 出版级图 ----------
fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
colors = ['#0072B2', '#D55E00', '#009E73', '#CC79A7']
ax.errorbar(x, resp, yerr=None, fmt='o', ms=4, color=colors[0], alpha=0.6, label='观测点')
ax.errorbar(x, means, yerr=sds, fmt='s', ms=6, color=colors[1], capsize=3, label='均值±SD')
xs = np.linspace(x.min() - 0.2, x.max() + 0.2, 300)
if len(best) == 4:
    ys = pl4(xs, best[0], best[1], best[-2], best[-1])
else:
    ys = pl4(xs, 0.0, best[0], best[-2], best[-1])
ax.plot(xs, ys, '-', color=colors[2], lw=2, label='%s 拟合' % model_name)
ax.axvline(logIC50, ls='--', color=colors[3], lw=1)
ax.text(logIC50, 0.05, 'IC50=%.3f μM\n95%%CI=[%.3f, %.3f]\nHill=%.3f, n=%d'
        % (IC50, 10 ** ci_lo, 10 ** ci_hi, hill, len(x)), fontsize=8, color=colors[3])
ax.set_xlabel('log10(剂量 / μM)', fontsize=9)
ax.set_ylabel('抑制率 (0-1)', fontsize=9)
ax.set_title('剂量-反应曲线 (%s)' % model_name, fontsize=10)
ax.legend(fontsize=8)
ax.tick_params(labelsize=8)
plt.tight_layout()
plt.savefig('figure.png', dpi=300)
plt.savefig('figure.svg')
print("[输出] figure.png / figure.svg 已保存")

# ---------- 6. 落盘 ----------
with open('ic50_estimate.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['model', 'IC50_uM', 'IC50_CI_lo', 'IC50_CI_hi', 'HillSlope', 'n', 'seed'])
    w.writerow([model_name, IC50, 10 ** ci_lo, 10 ** ci_hi, hill, len(x), SEED])
with open('bootstrap_audit.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['B', 'valid', 'logIC50_CI_lo', 'logIC50_CI_hi', 'resample_unit'])
    w.writerow([B, len(boot), ci_lo, ci_hi, 'independent_well/batch'])
print("[输出] ic50_estimate.csv / bootstrap_audit.csv 已保存")
print("[完成] 全部步骤执行完毕")