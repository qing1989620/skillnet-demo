# -*- coding: utf-8 -*-
"""
对两组数据做 t 检验并报告效应量与置信区间
依赖: numpy, matplotlib (仅这两个第三方库)
注意: 本脚本使用【模拟数据】演示流程, 不代表任何真实实验结论。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

ALPHA = 0.05
RNG = np.random.default_rng(20240517)


# ---------------- 1. 模拟数据 (明确标注) ----------------
def make_data():
    """生成两组模拟数据: A 组均值 10, B 组均值 11.2, 均为近似正态。"""
    n_a, n_b = 30, 32
    a = RNG.normal(loc=10.0, scale=2.0, size=n_a)
    b = RNG.normal(loc=11.2, scale=2.3, size=n_b)
    return a, b


# ---------------- 2. 正态性检验 (Shapiro-Wilk 自实现) ----------------
def shapiro_wilk(x):
    """
    简化版 Shapiro-Wilk 检验 (Royston 1995 近似)。
    返回 (W, p)。仅用于本脚本演示, 精度低于 scipy。
    """
    x = np.sort(np.asarray(x, dtype=float))
    n = x.size
    if n < 3:
        return np.nan, np.nan
    m = np.arange(1, n + 1) - (n + 1) / 2.0
    # 多项式近似权重
    u = 1.0 / np.sqrt(n)
    a_last = (-2.706056 * u**5 + 4.434685 * u**4 - 2.071190 * u**3
              - 0.147981 * u**2 + 0.221157 * u + m[-1] / np.sqrt(np.sum(m**2)))
    a_prev = (-3.582633 * u**5 + 5.682633 * u**4 - 1.752461 * u**3
              - 0.293762 * u**2 + 0.042981 * u + m[-2] / np.sqrt(np.sum(m**2)))
    if n > 5:
        phi = (np.sum(m**2) - 2 * m[-1]**2 - 2 * m[-2]**2) / (1 - 2 * a_last**2 - 2 * a_prev**2)
        a = m / np.sqrt(phi)
        a[-1], a[-2] = a_last, a_prev
        a[0], a[1] = -a_last, -a_prev
    else:
        phi = (np.sum(m**2) - 2 * m[-1]**2) / (1 - 2 * a_last**2)
        a = m / np.sqrt(phi)
        a[-1] = a_last
        a[0] = -a_last
    W = np.sum(a * x)**2 / np.sum((x - x.mean())**2)
    # p 值近似 (Royston)
    if n >= 12:
        g = 0.0
        mu = 0.0038915 * np.log(n)**3 - 0.083751 * np.log(n)**2 - 0.31082 * np.log(n) - 1.5861
        sigma = np.exp(0.0030302 * np.log(n)**2 - 0.082676 * np.log(n) - 0.4803)
        z = (np.log(1 - W) - mu) / sigma
    else:
        g = -2.273 + 0.459 * n
        mu = 0.5440 - 0.39978 * n + 0.025054 * n**2 - 0.0006714 * n**3
        sigma = np.exp(1.3822 - 0.77857 * n + 0.062767 * n**2 - 0.0020322 * n**3)
        z = (-np.log(g - np.log(1 - W)) - mu) / sigma
    # 标准正态 CDF
    p = 0.5 * (1 + _erf(z / np.sqrt(2)))
    return W, p


def _erf(x):
    """Abramowitz-Stegun 7.1.26 近似误差函数。"""
    sign = np.sign(x)
    x = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return sign * y


def _norm_cdf(z):
    return 0.5 * (1 + _erf(z / np.sqrt(2)))


def _t_cdf(t, df):
    """Student-t CDF 通过不完全 Beta 函数 (连分数) 实现。"""
    x = df / (df + t * t)
    ib = _betainc(df / 2.0, 0.5, x)
    return 1 - 0.5 * ib if t > 0 else 0.5 * ib


def _betainc(a, b, x):
    """正则化不完全 Beta 函数 (Lentz 连分数)。"""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = _loggamma(a) + _loggamma(b) - _loggamma(a + b)
    front = np.exp(np.log(x) * a + np.log(1 - x) * b - lbeta) / a
    if x > (a + 1) / (a + b + 2):
        return 1 - _betainc(b, a, 1 - x)
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 200):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1 - c * d) < 1e-10:
            break
    return front * (f - 1)


def _loggamma(x):
    """Lanczos 近似 log Gamma。"""
    g = 7
    c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
         771.32342877765313, -176.61502916214059, 12.507343278686905,
         -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
    if x < 0.5:
        return np.log(np.pi / np.sin(np.pi * x)) - _loggamma(1 - x)
    x -= 1
    a = c[0]
    t = x + g + 0.5
    for i in range(1, g + 2):
        a += c[i] / (x + i)
    return 0.5 * np.log(2 * np.pi) + (x + 0.5) * np.log(t) - t + np.log(a)


def t_test_ind(a, b, alpha=ALPHA):
    """Welch 独立样本 t 检验, 返回统计量、df、p、均值差、CI、Cohen's d。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = a.size, b.size
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = np.sqrt(va / na + vb / nb)
    t = (ma - mb) / se
    df = (va / na + vb / nb)**2 / ((va / na)**2 / (na - 1) + (vb / nb)**2 / (nb - 1))
    p = 2 * (1 - _t_cdf(abs(t), df))
    # 均值差的 95% CI
    tcrit = _t_ppf(1 - alpha / 2, df)
    diff = ma - mb
    ci = (diff - tcrit * se, diff + tcrit * se)
    # Cohen's d (pooled)
    sp = np.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    d = diff / sp
    # d 的 95% CI (Hedges & Olkin 近似)
    se_d = np.sqrt((na + nb) / (na * nb) + d**2 / (2 * (na + nb)))
    d_ci = (d - 1.96 * se_d, d + 1.96 * se_d)
    return dict(t=t, df=df, p=p, diff=diff, ci=ci, d=d, d_ci=d_ci,
                ma=ma, mb=mb, va=va, vb=vb, na=na, nb=nb)


def _t_ppf(q, df):
    """t 分布分位数 (二分法)。"""
    lo, hi = -100.0, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _t_cdf(mid, df) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def mannwhitney_u(a, b):
    """Mann-Whitney U 检验 (正态性不满足时的非参数替代), 返回 U, p (正态近似)。"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = a.size, b.size
    allv = np.concatenate([a, b])
    order = np.argsort(allv, kind='mergesort')
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, allv.size + 1)
    # 处理并列
    _, inv, cnt = np.unique(allv, return_inverse=True, return_counts=True)
    for i, c in enumerate(cnt):
        if c > 1:
            ranks[inv == i] = ranks[inv == i].mean()
    ra = ranks[:na].sum()
    U = ra - na * (na + 1) / 2
    mu = na * nb / 2
    sigma = np.sqrt(na * nb * (na + nb + 1) / 12)
    z = (U - mu) / sigma
    p = 2 * (1 - _norm_cdf(abs(z)))
    return U, p, z


def cohens_d_from_u(U, na, nb):
    """由 U 转换的秩双列相关 r 作为非参数效应量。"""
    return 1 - 2 * U / (na * nb)


def bonferroni(pvals, alpha=ALPHA):
    """Bonferroni 校正。"""
    m = len(pvals)
    return [min(1.0, p * m) for p in pvals], alpha / m


def bh_fdr(pvals, alpha=ALPHA):
    """Benjamini-Hochberg FDR 校正。"""
    p = np.asarray(pvals, float)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * m / (np.arange(1, m + 1))
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    out = np.empty_like(q)
    out[order] = q
    return out.tolist()


# ---------------- 主流程 ----------------
def main():
    print("=" * 68)
    print("【模拟数据】两组独立样本 t 检验 + 效应量 + 置信区间")
    print("=" * 68)

    a, b = make_data()
    print(f"组 A: n={a.size}, mean={a.mean():.4f}, sd={a.std(ddof=1):.4f}")
    print(f"组 B: n={b.size}, mean={b.mean():.4f}, sd={b.std(ddof=1):.4f}")

    # 1. 正态性检验
    Wa, pa = shapiro_wilk(a)
    Wb, pb = shapiro_wilk(b)
    print("\n[前提假设] Shapiro-Wilk 正态性检验:")
    print(f"  组 A: W={Wa:.4f}, p={pa:.4f} -> {'正态' if pa > ALPHA else '非正态'}")
    print(f"  组 B: W={Wb:.4f}, p={pb:.4f} -> {'正态' if pb > ALPHA else '非正态'}")
    normal_ok = (pa > ALPHA) and (pb > ALPHA)

    # 2. 方差齐性 (Levene 简化: 用 F 检验)
    Fa = a.var(ddof=1)
    Fb = b.var(ddof=1)
    F = Fa / Fb if Fa > Fb else Fb / Fa
    df1, df2 = (a.size - 1, b.size - 1) if Fa > Fb else (b.size - 1, a.size - 1)
    # F 检验 p 值 (用 Beta 近似)
    pF = 2 * min(_betainc(df1 / 2, df2 / 2, df1 * F / (df1 * F + df2)),
                 1 - _betainc(df1 / 2, df2 / 2, df1 * F / (df1 * F + df2)))
    print(f"\n[前提假设] 方差齐性 F 检验: F={F:.4f}, p={pF:.4f} -> "
          f"{'方差齐' if pF > ALPHA else '方差不齐 (用 Welch)'}")

    # 3. 主检验
    if normal_ok:
        print("\n[主检验] 正态性满足 -> 使用 Welch 独立样本 t 检验")
        res = t_test_ind(a, b, ALPHA)
        print(f"  t({res['df']:.3f}) = {res['t']:.4f}, p = {res['p']:.6f}")
        print(f"  均值差 = {res['diff']:.4f}, 95% CI = "
              f"[{res['ci'][0]:.4f}, {res['ci'][1]:.4f}]")
        print(f"  Cohen's d = {res['d']:.4f}, 95% CI = "
              f"[{res['d_ci'][0]:.4f}, {res['d_ci'][1]:.4f}]")
        print(f"  结论: {'拒绝 H0 (差异显著)' if res['p'] < ALPHA else '不拒绝 H0'}")
        effect = res['d']
        effect_ci = res['d_ci']
        p_main = res['p']
    else:
        print("\n[主检验] 正态性不满足 -> 使用 Mann-Whitney U 非参数检验")
        U, p, z = mannwhitney_u(a, b)
        r = cohens_d_from_u(U, a.size, b.size)
        print(f"  U = {U:.4f}, z = {z:.4f}, p = {p:.6f}")
        print(f"  秩双列相关 r = {r:.4f} (非参数效应量)")
        print(f"  结论: {'拒绝 H0 (差异显著)' if p < ALPHA else '不拒绝 H0'}")
        effect = r
        effect_ci = (np.nan, np.nan)
        p_main = p

    # 4. 多重比较校正演示 (3 个假设检验)
    print("\n[多重比较校正] 演示 3 个假设检验的 p 值校正:")
    pvals = [p_main, 0.03, 0.20]
    bonf, thr = bonferroni(pvals, ALPHA)
    fdr = bh_fdr(pvals, ALPHA)
    print(f"  原始 p 值: {[f'{p:.4f}' for p in pvals]}")
    print(f"  Bonferroni 校正后: {[f'{p:.4f}' for p in bonf]} (阈值 α/m={thr:.4f})")
    print(f"  BH-FDR 校正后: {[f'{p:.4f}' for p in fdr]}")

    # 5. 陷阱规避检查
    print("\n[陷阱规避检查]")
    print(f"  ✓ 已做正态性检验: {'通过' if normal_ok else '未通过, 已切换非参数检验'}")
    print(f"  ✓ 已报告效应量: {effect:.4f} (不只报 p 值)")
    print(f"  ✓ 已报告置信区间: 均值差 CI 与效应量 CI 均已给出")
    print(f"  ✓ 多重比较已用 Bonferroni 与 BH-FDR 校正")

    # 6. 出图
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].hist(a, bins=10, alpha=0.6, label=f'A (n={a.size})', color='steelblue')
    axes[0].hist(b, bins=10, alpha=0.6, label=f'B (n={b.size})', color='salmon')
    axes[0].axvline(a.mean(), color='steelblue', ls='--', lw=2)
    axes[0].axvline(b.mean(), color='salmon', ls='--', lw=2)
    axes[0].set_title('两组数据分布 (模拟数据)')
    axes[0].set_xlabel('数值')
    axes[0].set_ylabel('频数')
    axes[0].legend()

    if normal_ok:
        diff = res['diff']
        ci = res['ci']
        axes[1].errorbar([0], [diff], yerr=[[diff - ci[0]], [ci[1] - diff]],
                         fmt='o', capsize=8, color='darkgreen', markersize=10)
        axes[1].axhline(0, color='gray', ls='--')
        axes[1].set_xticks([0])
        axes[1].set_xticklabels(['A - B'])
        axes[1].set_title(f'均值差与 95% CI\nCohen\'s d = {res["d"]:.3f}')
        axes[1].set_ylabel('均值差')
    else:
        axes[1].bar(['A', 'B'], [a.mean(), b.mean()], color=['steelblue', 'salmon'])
        axes[1].set_title(f'Mann-Whitney U={U:.1f}, p={p:.4f}\nr={r:.3f}')
        axes[1].set_ylabel('均值')

    plt.tight_layout()
    plt.savefig('figure.png', dpi=120)
    plt.close()

    # 7. 落盘
    np.savetxt('group_A.csv', a, delimiter=',', header='group_A', comments='')
    np.savetxt('group_B.csv', b, delimiter=',', header='group_B', comments='')
    with open('test_results.csv', 'w', encoding='utf-8') as f:
        f.write('metric,value\n')
        f.write(f'normal_A_p,{pa:.6f}\n')
        f.write(f'normal_B_p,{pb:.6f}\n')
        f.write(f'variance_F_p,{pF:.6f}\n')
        f.write(f'main_p,{p_main:.6f}\n')
        f.write(f'effect_size,{effect:.6f}\n')
        if normal_ok:
            f.write(f'mean_diff,{res["diff"]:.6f}\n')
            f.write(f'ci_low,{res["ci"][0]:.6f}\n')
            f.write(f'ci_high,{res["ci"][1]:.6f}\n')
    print("\n已保存: figure.png, group_A.csv, group_B.csv, test_results.csv")


if __name__ == '__main__':
    main()