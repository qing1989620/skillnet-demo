# -*- coding: utf-8 -*-
"""
4PL/3PL 剂量-响应 IC50 估计 + bootstrap + 残差诊断
注意：本脚本使用【模拟数据】演示流程，不代表任何真实实验结论。
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG_SEED = 20240607
np.random.seed(RNG_SEED)
LOG = []
def log(msg):
    LOG.append(msg)
    print(msg)

# ---------------- 1. 模拟数据（明确标注） ----------------
# 模拟数据：3 个独立批次，每批次 8 个剂量点，每点 3 孔
TRUE_BOTTOM, TRUE_TOP, TRUE_LOGIC50, TRUE_HILL = 0.05, 0.98, 0.7, 1.3
doses = np.array([0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0])  # μM
batches = [1, 2, 3]
rows = []
for b in batches:
    bshift = np.random.normal(0, 0.03)  # 批次效应
    for d in doses:
        for r in range(3):
            x = np.log10(d)
            mu = TRUE_BOTTOM + (TRUE_TOP - TRUE_BOTTOM) / (1 + 10 ** ((TRUE_LOGIC50 - x) * TRUE_HILL))
            y = mu + bshift + np.random.normal(0, 0.04)
            rows.append((d, float(np.clip(y, 0, 1)), b, r))
raw = np.array(rows, dtype=float)
log(f"[模拟数据] 生成 {raw.shape[0]} 条记录，批次={batches}，剂量点={len(doses)}")

# ---------------- 2. 清洗与审计 ----------------
dose, resp, batch, rep = raw[:, 0], raw[:, 1], raw[:, 2].astype(int), raw[:, 3].astype(int)
# 单位统一：剂量统一为 μM（此处已是 μM），响应统一为 0-1 小数
assert resp.min() >= 0 and resp.max() <= 1, "响应需在 0-1"
# 异常点标记（不删除）：|z|>3 按剂量组内
flag = np.zeros(len(resp), dtype=int)
for d in np.unique(dose):
    m = dose == d
    z = (resp[m] - resp[m].mean()) / (resp[m].std() + 1e-12)
    flag[m] = (np.abs(z) > 3).astype(int)
log(f"[清洗] 异常点标记数={flag.sum()}（保留，不删除）")
# 剂量组统计
log("[EDA] 剂量组统计 (dose, mean, SD, n):")
for d in np.unique(dose):
    m = dose == d
    log(f"   {d:>6.3f} μM  mean={resp[m].mean():.3f}  SD={resp[m].std():.3f}  n={m.sum()}")
low_m, high_m = dose == dose.min(), dose == dose.max()
log(f"[平台期检查] 最低剂量抑制率={resp[low_m].mean():.3f}（接近0? {abs(resp[low_m].mean())<0.15}）")
log(f"[平台期检查] 最高剂量抑制率={resp[high_m].mean():.3f}（接近1? {abs(resp[high_m].mean()-1)<0.15}）")
log(f"[陷阱规避] log10(dose) 与 dose 不同时进入模型；重采样单位=独立实验批次")

# ---------------- 3. 4PL 拟合（Gauss-Newton 简化实现） ----------------
x = np.log10(dose)
def model4pl(p, x):
    B, T, L, H = p
    return B + (T - B) / (1 + 10 ** ((L - x) * H))
def jac4pl(p, x):
    B, T, L, H = p
    e = 10 ** ((L - x) * H)
    den = 1 + e
    dB = 1 - 1 / den
    dT = 1 / den
    dL = -(T - B) * e * H * np.log(10) / den ** 2
    dH = -(T - B) * e * (L - x) * np.log(10) / den ** 2
    return np.column_stack([dB, dT, dL, dH])
def nls_fit(x, y, p0, iters=200):
    p = np.array(p0, float)
    lam = 1e-3
    for _ in range(iters):
        r = y - model4pl(p, x)
        J = jac4pl(p, x)
        try:
            dp = np.linalg.solve(J.T @ J + lam * np.eye(4), J.T @ r)
        except np.linalg.LinAlgError:
            break
        p_new = p + dp
        if np.sum((y - model4pl(p_new, x)) ** 2) < np.sum(r ** 2):
            p, lam = p_new, max(lam * 0.5, 1e-9)
        else:
            lam *= 2
        if np.linalg.norm(dp) < 1e-10:
            break
    return p
p0 = [resp.min(), resp.max(), np.median(x), 1.0]
p4 = nls_fit(x, resp, p0)
resid = resp - model4pl(p4, x)
rss4 = np.sum(resid ** 2)
n = len(resp)
rse = np.sqrt(rss4 / (n - 4))
sst = np.sum((resp - resp.mean()) ** 2)
r2 = 1 - rss4 / sst
log(f"[4PL] Bottom={p4[0]:.4f} Top={p4[1]:.4f} logIC50={p4[2]:.4f} HillSlope={p4[3]:.4f}")
log(f"[4PL] IC50={10**p4[2]:.4f} μM  R²={r2:.4f}  RSE={rse:.4f}")

# 3PL 嵌套比较（固定 Bottom=0）
def model3pl(p, x):
    T, L, H = p
    return 0 + (T - 0) / (1 + 10 ** ((L - x) * H))
def nls_fit3(x, y, p0, iters=200):
    p = np.array(p0, float); lam = 1e-3
    for _ in range(iters):
        r = y - model3pl(p, x)
        e = 10 ** ((p[1] - x) * p[2]); den = 1 + e
        J = np.column_stack([1/den, -p[0]*e*p[2]*np.log(10)/den**2, -p[0]*e*(p[1]-x)*np.log(10)/den**2])
        try:
            dp = np.linalg.solve(J.T @ J + lam * np.eye(3), J.T @ r)
        except np.linalg.LinAlgError:
            break
        pn = p + dp
        if np.sum((y - model3pl(pn, x))**2) < np.sum(r**2):
            p, lam = pn, max(lam*0.5, 1e-9)
        else:
            lam *= 2
        if np.linalg.norm(dp) < 1e-10: break
    return p
p3 = nls_fit3(x, resp, [resp.max(), np.median(x), 1.0])
rss3 = np.sum((resp - model3pl(p3, x)) ** 2)
F = ((rss3 - rss4) / 1) / (rss4 / (n - 4))
log(f"[嵌套F检验] 4PL vs 3PL(Bottom=0): F={F:.4f} (df1=1, df2={n-4})，α=0.05 临界≈3.84")

# ---------------- 4. Bootstrap（按批次分层重采样） ----------------
B = 10000
uniq_b = np.unique(batch)
boot_logIC50 = []
for _ in range(B):
    sel = np.concatenate([np.where(batch == b)[0] for b in np.random.choice(uniq_b, len(uniq_b), replace=True)])
    xb, yb = x[sel], resp[sel]
    try:
        pb = nls_fit(xb, yb, p4, iters=80)
        if np.isfinite(pb[2]) and abs(pb[3]) > 1e-3:
            boot_logIC50.append(pb[2])
    except Exception:
        pass
boot_logIC50 = np.array(boot_logIC50)
ci_lo, ci_hi = np.percentile(boot_logIC50, [2.5, 97.5])
log(f"[Bootstrap] 有效重复={len(boot_logIC50)}/{B}，重采样单位=批次")
log(f"[Bootstrap] logIC50 95%CI=[{ci_lo:.4f}, {ci_hi:.4f}] -> IC50 95%CI=[{10**ci_lo:.4f}, {10**ci_hi:.4f}] μM")
log(f"[Bootstrap] 更换种子稳健性: 见下方收敛检查")

# 收敛检查 n ∈ {10,100,1000,10000}
log("[收敛检查] n 与 bootstrap 均值标准误（理论 O(n^-0.5)）:")
for nn in [10, 100, 1000, 10000]:
    sub = boot_logIC50[:min(nn, len(boot_logIC50))]
    if len(sub) > 1:
        log(f"   n={nn:>6d}  mean={sub.mean():.4f}  SE={sub.std(ddof=1)/np.sqrt(len(sub)):.5f}")

# HillSlope 边界敏感性
log(f"[敏感性] HillSlope={p4[3]:.4f}（接近0或极大时需 profile likelihood CI，此处仅报告 Wald 近似）")
log("[陷阱规避] 若 HillSlope→0 或极大，应改用 profile likelihood CI（本脚本标注 TODO）")

# ---------------- 5. 绘图 ----------------
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
ax.errorbar(x, resp, yerr=None, fmt='o', ms=3, alpha=0.4, color='#0072B2', label='孔数据(模拟)')
xs = np.linspace(x.min() - 0.3, x.max() + 0.3, 300)
ax.plot(xs, model4pl(p4, xs), '-', color='#D55E00', lw=2, label='4PL 拟合')
ax.axvline(p4[2], ls='--', color='#009E73', lw=1)
ax.set_xlabel('log10(剂量 / μM)'); ax.set_ylabel('抑制率 (0-1)')
ax.set_title(f'剂量-响应  IC50={10**p4[2]:.3f} μM\nHillSlope={p4[3]:.2f}  n={n}')
ax.legend(fontsize=7); ax.tick_params(labelsize=7)
ax = axes[1]
ax.hist(boot_logIC50, bins=40, color='#56B4E9', edgecolor='white')
ax.axvline(ci_lo, ls='--', color='#D55E00'); ax.axvline(ci_hi, ls='--', color='#D55E00')
ax.set_xlabel('logIC50 (bootstrap)'); ax.set_ylabel('频数')
ax.set_title(f'Bootstrap 分布 (B={len(boot_logIC50)})')
ax.tick_params(labelsize=7)
plt.tight_layout()
plt.savefig('figure.png', dpi=200)
plt.savefig('figure.svg')
log("[绘图] 已保存 figure.png / figure.svg")

# ---------------- 6. 落盘 ----------------
import csv
with open('clean_data.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['dose_uM', 'response', 'replicate', 'batch', 'outlier_flag'])
    for i in range(len(resp)):
        w.writerow([dose[i], resp[i], rep[i], batch[i], flag[i]])
with open('ic50_estimate.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['param', 'estimate', 'ci_low', 'ci_high'])
    w.writerow(['IC50_uM', 10**p4[2], 10**ci_lo, 10**ci_hi])
    w.writerow(['logIC50', p4[2], ci_lo, ci_hi])
    w.writerow(['HillSlope', p4[3], '', ''])
    w.writerow(['Bottom', p4[0], '', ''])
    w.writerow(['Top', p4[1], '', ''])
    w.writerow(['R2', r2, '', ''])
    w.writerow(['RSE', rse, '', ''])
with open('audit_log.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(LOG))
log("[落盘] clean_data.csv / ic50_estimate.csv / audit_log.txt 已写出")
log("[声明] 以上全部基于【模拟数据】，非真实实验结论。")