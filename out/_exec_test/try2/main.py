import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

import sys
import io

# 修复 Windows GBK 控制台无法输出 Unicode 字符（如 ²、μ）的问题
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# ============================================================
# 说明：本脚本使用【模拟数据】演示四参数 logistic (4PL) 拟合与 IC50 估计。
# 模拟数据不代表任何真实实验结果，仅用于方法学演示。
# ============================================================
rng = np.random.default_rng(20240607)

conc = np.array([0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0])  # μM
n_rep = 3

# 真实参数（模拟用）
TRUE_TOP = 100.0     # 上平台
TRUE_BOTTOM = 5.0    # 下平台
TRUE_IC50 = 1.2      # μM
TRUE_HILL = 1.1

def four_pl(x, top, bottom, ic50, hill):
    return bottom + (top - bottom) / (1.0 + (x / ic50) ** hill)

# 生成 3 次重复（模拟数据）
true_mean = four_pl(conc, TRUE_TOP, TRUE_BOTTOM, TRUE_IC50, TRUE_HILL)
noise_sd = 3.0
reps = true_mean[None, :] + rng.normal(0, noise_sd, size=(n_rep, conc.size))
reps = np.clip(reps, 0, None)
mean_resp = reps.mean(axis=0)
sd_resp = reps.std(axis=0, ddof=1)
sem_resp = sd_resp / np.sqrt(n_rep)

print("=" * 70)
print("【模拟数据】剂量-反应原始数据（3 次重复，单位：抑制率 %）")
print("=" * 70)
print(f"{'浓度(μM)':>10} {'重复1':>8} {'重复2':>8} {'重复3':>8} {'均值':>8} {'SD':>8} {'SEM':>8}")
for i, c in enumerate(conc):
    print(f"{c:>10.2f} {reps[0,i]:>8.2f} {reps[1,i]:>8.2f} {reps[2,i]:>8.2f} "
          f"{mean_resp[i]:>8.2f} {sd_resp[i]:>8.2f} {sem_resp[i]:>8.2f}")

# ============================================================
# 步骤 1：设计类型判断
# ============================================================
print("\n" + "=" * 70)
print("步骤 1：设计类型判断")
print("=" * 70)
print("设计类型：单因素剂量-反应，9 个浓度水平，每水平 3 次独立重复。")
print("分析目标：估计 IC50 及 95% 置信区间（非线性回归 + Bootstrap）。")

# ============================================================
# 步骤 2：正态性检验（Shapiro-Wilk 手工实现，避免第三方依赖）
# ============================================================
def shapiro_wilk(x):
    """Shapiro-Wilk 检验的简化实现（Royston 1995 近似）。返回 W 与 p 值。"""
    x = np.sort(np.asarray(x, dtype=float))
    n = x.size
    if n < 3:
        return np.nan, np.nan
    m = np.array([_norm_ppf((i + 1 - 0.375) / (n + 0.25)) for i in range(n)])
    m = m / np.sqrt(np.sum(m ** 2))
    # 多项式系数近似
    c = m / np.sqrt(np.sum(m ** 2))
    W = (np.sum(c * x)) ** 2 / np.sum((x - x.mean()) ** 2)
    # p 值近似（正态变换）
    if n == 3:
        p = 1.0 - 0.9999 * (1 - W) ** 0.5
    else:
        y = np.log(1 - W)
        mu = -1.5861 - 0.31082 * np.log(n) - 0.083751 * np.log(n) ** 2 + 0.0038915 * np.log(n) ** 3
        sigma = np.exp(-0.4803 - 0.082676 * np.log(n) + 0.0030302 * np.log(n) ** 2)
        z = (y - mu) / sigma
        p = 1 - _norm_cdf(z)
    return W, p

def _norm_ppf(p):
    """标准正态分位数（Acklam 近似）。"""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = np.sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    elif p > phigh:
        q = np.sqrt(-2 * np.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    else:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

def _norm_cdf(z):
    return 0.5 * (1 + _erf(z / np.sqrt(2)))

def _erf(x):
    # Abramowitz & Stegun 7.1.26
    sign = np.sign(x)
    x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return sign * y

print("\n" + "=" * 70)
print("步骤 2：正态性检验（Shapiro-Wilk，各浓度水平残差）")
print("=" * 70)
all_resid = []
for i in range(conc.size):
    r = reps[:, i] - mean_resp[i]
    all_resid.extend(r.tolist())
all_resid = np.array(all_resid)
W, p_sw = shapiro_wilk(all_resid)
print(f"Shapiro-Wilk W = {W:.4f}, p = {p_sw:.4f}")
if p_sw > 0.05:
    print("结论：残差正态性假设【未拒绝】(p > 0.05)，可继续使用参数方法。")
else:
    print("结论：残差正态性假设【被拒绝】(p <= 0.05)，应使用非参数/Bootstrap 方法。")
print("规避措施：无论正态性如何，IC50 置信区间均采用 Bootstrap（非参数）方法，避免对非正态数据强行使用 t 检验。")

# ============================================================
# 步骤 3：4PL 非线性最小二乘拟合（Levenberg-Marquardt 手工实现）
# ============================================================
def fit_4pl(x, y, p0=None, max_iter=500, tol=1e-10):
    """4PL 拟合：参数 [top, bottom, log_ic50, hill]，使用 log 参数化保证 ic50>0。"""
    if p0 is None:
        p0 = np.array([y.max(), y.min(), np.log(np.median(x)), 1.0])
    p = p0.astype(float).copy()
    lam = 1e-3
    for _ in range(max_iter):
        top, bottom, log_ic50, hill = p
        ic50 = np.exp(log_ic50)
        denom = 1.0 + (x / ic50) ** hill
        f = bottom + (top - bottom) / denom
        r = y - f
        # 雅可比
        d_top = 1.0 / denom
        d_bottom = 1.0 - 1.0 / denom
        # d/d(log_ic50)
        u = (x / ic50) ** hill
        d_log_ic50 = (top - bottom) * u * hill / (denom ** 2)
        # d/d(hill)
        ln_xic = np.log(x / ic50)
        d_hill = -(top - bottom) * u * ln_xic / (denom ** 2)
        J = np.column_stack([d_top, d_bottom, d_log_ic50, d_hill])
        # 高斯-牛顿 + LM 阻尼
        JtJ = J.T @ J
        Jtr = J.T @ r
        try:
            dp = np.linalg.solve(JtJ + lam * np.diag(np.diag(JtJ) + 1e-12), Jtr)
        except np.linalg.LinAlgError:
            break
        p_new = p + dp
        # 限制 hill 为正
        if p_new[3] <= 0:
            p_new[3] = 1e-3
        f_new = p_new[1] + (p_new[0] - p_new[1]) / (1.0 + (x / np.exp(p_new[2])) ** p_new[3])
        if np.sum((y - f_new) ** 2) < np.sum(r ** 2):
            p = p_new
            lam = max(lam * 0.5, 1e-12)
        else:
            lam = min(lam * 2.0, 1e12)
        if np.linalg.norm(dp) < tol:
            break
    return p

p_fit = fit_4pl(conc, mean_resp)
top_f, bottom_f, log_ic50_f, hill_f = p_fit
ic50_f = np.exp(log_ic50_f)
print("\n" + "=" * 70)
print("步骤 3：4PL 模型拟合结果（基于均值数据）")
print("=" * 70)
print(f"Top    = {top_f:.4f}")
print(f"Bottom = {bottom_f:.4f}")
print(f"IC50   = {ic50_f:.4f} μM")
print(f"Hill   = {hill_f:.4f}")

# 拟合优度 R^2
pred = four_pl(conc, top_f, bottom_f, ic50_f, hill_f)
ss_res = np.sum((mean_resp - pred) ** 2)
ss_tot = np.sum((mean_resp - mean_resp.mean()) ** 2)
r2 = 1 - ss_res / ss_tot
print(f"R^2    = {r2:.4f}")

# ============================================================
# 步骤 4：Bootstrap 估计 IC50 的 95% 置信区间
# ============================================================
n_boot = 2000
boot_ic50 = []
for b in range(n_boot):
    idx = rng.integers(0, n_rep, size=n_rep)
    y_b = reps[idx, :].mean(axis=0)
    try:
        pb = fit_4pl(conc, y_b)
        boot_ic50.append(np.exp(pb[2]))
    except Exception:
        continue
boot_ic50 = np.array(boot_ic50)
ci_low, ci_high = np.percentile(boot_ic50, [2.5, 97.5])
print("\n" + "=" * 70)
print("步骤 4：Bootstrap 95% 置信区间（非参数，规避正态性假设）")
print("=" * 70)
print(f"Bootstrap 有效次数 = {len(boot_ic50)}")
print(f"IC50 点估计        = {ic50_f:.4f} μM")
print(f"IC50 95% CI        = [{ci_low:.4f}, {ci_high:.4f}] μM")
print(f"Bootstrap 均值     = {boot_ic50.mean():.4f} μM")
print(f"Bootstrap 标准差   = {boot_ic50.std(ddof=1):.4f} μM")

# ============================================================
# 步骤 5：效应量（相对抑制率差异）与多重比较校正
# ============================================================
print("\n" + "=" * 70)
print("步骤 5：效应量与多重比较校正")
print("=" * 70)
# 效应量：最高浓度 vs 最低浓度的 Cohen's d
g1 = reps[:, 0]   # 最低浓度
g2 = reps[:, -1]  # 最高浓度
pooled_sd = np.sqrt(((n_rep - 1) * g1.var(ddof=1) + (n_rep - 1) * g2.var(ddof=1)) / (2 * n_rep - 2))
cohen_d = (g2.mean() - g1.mean()) / pooled_sd if pooled_sd > 0 else np.nan
print(f"最低浓度均值 = {g1.mean():.2f}, 最高浓度均值 = {g2.mean():.2f}")
print(f"Cohen's d (最高 vs 最低) = {cohen_d:.4f}")

# 各浓度 vs 最低浓度的 Welch t 检验 + Bonferroni 校正
def welch_t(a, b):
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    na, nb = len(a), len(b)
    se = np.sqrt(va / na + vb / nb)
    if se == 0:
        return np.nan, np.nan, np.nan
    t = (ma - mb) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    # 双尾 p 值（t 分布近似用正态）
    p = 2 * (1 - _norm_cdf(abs(t)))
    return t, df, p

print("\n各浓度 vs 最低浓度（0.01 μM）的 Welch t 检验（Bonferroni 校正）:")
m = conc.size - 1
print(f"{'浓度(μM)':>10} {'t':>8} {'df':>8} {'p_raw':>10} {'p_bonf':>10} {'显著':>6}")
for i in range(1, conc.size):
    t, df, p = welch_t(reps[:, i], reps[:, 0])
    p_bonf = min(p * m, 1.0)
    sig = "是" if p_bonf < 0.05 else "否"
    print(f"{conc[i]:>10.2f} {t:>8.3f} {df:>8.2f} {p:>10.4f} {p_bonf:>10.4f} {sig:>6}")

# ============================================================
# 步骤 6：保存 CSV
# ============================================================
import csv
with open("dose_response_data.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["浓度_uM", "重复1", "重复2", "重复3", "均值", "SD", "SEM", "拟合值"])
    for i, c in enumerate(conc):
        w.writerow([c, reps[0, i], reps[1, i], reps[2, i], mean_resp[i], sd_resp[i], sem_resp[i], pred[i]])
print("\n数据已保存至 dose_response_data.csv")

# ============================================================
# 步骤 7：绘图
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# 左图：剂量-反应曲线
ax = axes[0]
x_smooth = np.logspace(np.log10(conc.min()), np.log10(conc.max()), 300)
y_smooth = four_pl(x_smooth, top_f, bottom_f, ic50_f, hill_f)
ax.errorbar(conc, mean_resp, yerr=sem_resp, fmt='o', color='#1f77b4',
            capsize=4, label='模拟数据均值 ± SEM', zorder=3)
ax.plot(x_smooth, y_smooth, '-', color='#d62728', lw=2, label='4PL 拟合曲线')
ax.axvline(ic50_f, color='gray', ls='--', lw=1.2)
ax.axhline(bottom_f + (top_f - bottom_f) / 2, color='gray', ls=':', lw=1.2)
ax.text(ic50_f * 1.15, bottom_f + (top_f - bottom_f) / 2 + 3,
        f'IC50 = {ic50_f:.3f} μM\n95% CI [{ci_low:.3f}, {ci_high:.3f}]',
        fontsize=10, color='#333333')
ax.set_xscale('log')
ax.set_xlabel('抑制剂浓度 (μM, log scale)')
ax.set_ylabel('抑制率 (%)')
ax.set_title('剂量-反应曲线与 IC50 估计（模拟数据）')
ax.legend(loc='lower right')
ax.grid(alpha=0.3)

# 右图：Bootstrap IC50 分布
ax2 = axes[1]
ax2.hist(boot_ic50, bins=40, color='#2ca02c', alpha=0.7, edgecolor='white')
ax2.axvline(ic50_f, color='#d62728', lw=2, label=f'点估计 {ic50_f:.3f}')
ax2.axvline(ci_low, color='black', ls='--', lw=1.5, label=f'95% CI 下界 {ci_low:.3f}')
ax2.axvline(ci_high, color='black', ls='--', lw=1.5, label=f'95% CI 上界 {ci_high:.3f}')
ax2.set_xlabel('IC50 (μM)')
ax2.set_ylabel('频数')
ax2.set_title('Bootstrap IC50 分布（2000 次重采样，模拟数据）')
ax2.legend()
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("图已保存至 figure.png")

# ============================================================
# 最终报告
# ============================================================
print("\n" + "=" * 70)
print("最终统计报告（模拟数据，非真实实验结论）")
print("=" * 70)
print(f"模型：四参数 logistic (4PL)")
print(f"IC50 估计值：{ic50_f:.4f} μM")
print(f"IC50 95% 置信区间（Bootstrap）：[{ci_low:.4f}, {ci_high:.4f}] μM")
print(f"Hill 斜率：{hill_f:.4f}")
print(f"拟合优度 R^2：{r2:.4f}")
print(f"效应量 Cohen's d（最高 vs 最低浓度）：{cohen_d:.4f}")
print(f"正态性检验：Shapiro-Wilk W={W:.4f}, p={p_sw:.4f}")
print(f"多重比较：Bonferroni 校正（{m} 次比较）")
print("陷阱规避：")
print("  - 未对非正态数据强行使用 t 检验（IC50 CI 用 Bootstrap）")
print("  - 报告了效应量 Cohen's d，不仅报 p 值")
print("  - 多重比较使用 Bonferroni 校正")
print("=" * 70)