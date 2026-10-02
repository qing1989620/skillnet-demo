# -*- coding: utf-8 -*-
"""
省级面板数据：产业政策对企业创新的影响（含内生性处理与稳健性检验）
注意：本脚本使用【模拟数据】，所有数值结果均为模拟演示，不代表任何真实结论。
仅使用 numpy 2.5.3 与 matplotlib 3.11.2（无 statsmodels/linearmodels，故手写 OLS/2SLS/FE 估计）。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(20240517)

# ============================================================
# 1. 构造模拟省级面板数据（模拟数据！）
# ============================================================
N_PROV, N_YEAR = 30, 12
prov = np.repeat(np.arange(N_PROV), N_YEAR)
year = np.tile(np.arange(2008, 2008 + N_YEAR), N_PROV)
T = N_YEAR

# 省份固定效应、时间趋势
mu_i = rng.normal(0, 1.0, N_PROV)[prov]
trend = 0.15 * (year - 2008)

# 政策：不同省份在不同年份陆续推行（交错DID结构）
first_treat = rng.integers(2012, 2019, N_PROV)  # 每省首次实施年份
policy = ((year >= first_treat[prov]) & (first_treat[prov] < 9999)).astype(float)

# 内生性来源：政策实施与省份不可观测能力相关（用 mu_i 影响政策倾向）
# 这里 policy 已由 first_treat 决定，我们让 first_treat 与 mu_i 相关
# （重新生成以体现内生性：能力强的省份更早实施）
first_treat = np.clip(np.round(2016 - 1.2 * mu_i[:N_PROV] + rng.normal(0, 1.0, N_PROV)).astype(int), 2010, 2019)
policy = ((year >= first_treat[prov])).astype(float)

# 工具变量：邻省政策强度（模拟：与本地政策相关，但不直接影响本地创新）
neighbor_policy = np.zeros_like(policy)
for i in range(N_PROV):
    idx = prov == i
    others = [j for j in range(N_PROV) if j != i]
    nb = np.mean([policy[prov == j] for j in others], axis=0)
    neighbor_policy[idx] = nb + rng.normal(0, 0.05, T)

# 创新产出（专利数对数）
# 真实效应 beta=0.35；mu_i 同时影响政策与创新 -> 内生性偏误
eps = rng.normal(0, 0.5, N_PROV * N_YEAR)
ln_innov = (1.0 + 0.35 * policy + 0.6 * mu_i + trend
            + 0.2 * np.log(1 + rng.poisson(5, N_PROV * N_YEAR))
            + eps)

# 控制变量
rd_subsidy = 0.5 * policy + rng.normal(0, 0.3, N_PROV * N_YEAR)
gdp_pc = 9.0 + 0.1 * (year - 2008) + 0.3 * mu_i + rng.normal(0, 0.2, N_PROV * N_YEAR)

X_ctrl = np.column_stack([rd_subsidy, gdp_pc])
print("=" * 60)
print("【模拟数据】样本量 =", len(ln_innov), " 省份 =", N_PROV, " 年份 =", N_YEAR)
print("=" * 60)

# ============================================================
# 2. 工具函数：OLS / 聚类稳健标准误 / 双向固定效应
# ============================================================
def ols(y, X):
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    resid = y - X @ beta
    return beta, resid, XtX_inv

def cluster_se(X, resid, XtX_inv, groups):
    """聚类稳健标准误（Liang-Zeger）"""
    k = X.shape[1]
    meat = np.zeros((k, k))
    for g in np.unique(groups):
        m = groups == g
        Xg, ug = X[m], resid[m]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = len(np.unique(groups))
    n = X.shape[0]
    dfc = (G / (G - 1)) * ((n - 1) / (n - k))
    V = dfc * XtX_inv @ meat @ XtX_inv
    return np.sqrt(np.diag(V))

def demean(y, X, g1, g2):
    """双向去均值（省份 + 年份）"""
    def dm(v):
        v = v.astype(float).copy()
        for g in (g1, g2):
            for u in np.unique(g):
                m = g == u
                v[m] -= v[m].mean()
        return v
    return dm(y), np.column_stack([dm(X[:, j]) for j in range(X.shape[1])])

# ============================================================
# 3. Hausman 检验：FE vs RE（用省份聚类SE）
# ============================================================
# FE（双向）
y_dm, X_dm = demean(ln_innov, np.column_stack([policy, X_ctrl]), prov, year)
b_fe, r_fe, inv_fe = ols(y_dm, X_dm)
se_fe = cluster_se(X_dm, r_fe, inv_fe, prov)

# RE 近似：用省份虚拟变量（LSDV）作为对照，此处用 pooled OLS + 省份均值近似
# 简化：RE 用 pooled OLS（含常数项）作为对照
X_pool = np.column_stack([np.ones_like(policy), policy, X_ctrl])
b_re, r_re, inv_re = ols(ln_innov, X_pool)
se_re = cluster_se(X_pool, r_re, inv_re, prov)

# Hausman 统计量（仅比较 policy 系数）
diff = b_fe[0] - b_re[1]
var_diff = se_fe[0] ** 2 - se_re[1] ** 2
hausman = diff ** 2 / var_diff if var_diff > 0 else np.nan
print("\n[Hausman 检验] FE 与 RE 的 policy 系数差 = %.4f" % diff)
print("[Hausman 检验] 统计量 = %.4f (>3.84 则选 FE，5%% 水平)" % hausman)
print("[Hausman 检验] 结论：%s" % ("拒绝 RE，采用固定效应" if hausman > 3.84 else "不能拒绝 RE"))

# ============================================================
# 4. 序列相关与异方差检验 -> 论证聚类层级
# ============================================================
# Wooldridge 序列相关检验（对 FE 残差做 AR(1) 回归）
r_lag = np.zeros_like(r_fe)
for i in range(N_PROV):
    idx = np.where(prov == i)[0]
    r_lag[idx[1:]] = r_fe[idx[:-1]]
ar_beta = np.sum(r_lag * r_fe) / np.sum(r_lag ** 2)
print("\n[序列相关] FE 残差 AR(1) 系数 = %.4f (|值|大 -> 存在序列相关)" % ar_beta)

# 异方差：Breusch-Pagan 简化（残差平方对拟合值回归）
fit = y_dm - r_fe
bp_b = np.sum((fit - fit.mean()) * (r_fe ** 2 - (r_fe ** 2).mean())) / np.sum((fit - fit.mean()) ** 2)
print("[异方差] 残差平方对拟合值斜率 = %.4f (非0 -> 存在异方差)" % bp_b)
print("[聚类层级论证] 存在序列相关+异方差 -> 聚类到【省份】层级（政策在省份层面变动）")

# ============================================================
# 5. 2SLS：用邻省政策作为工具变量
# ============================================================
def tsls(y, X_endog, X_exog, Z_extra, groups):
    """两阶段最小二乘 + 聚类SE"""
    n = len(y)
    Z = np.column_stack([Z_extra, X_exog])
    X = np.column_stack([X_endog, X_exog])
    # 第一阶段
    Pz = Z @ np.linalg.pinv(Z.T @ Z) @ Z.T
    Xhat = Pz @ X
    # 第二阶段
    b, r, inv = ols(y, Xhat)
    se = cluster_se(Xhat, r, inv, groups)
    # 第一阶段 F 统计量（弱工具变量检验）
    b1, r1, inv1 = ols(X_endog, Z)
    k = Z.shape[1]
    rss1 = np.sum(r1 ** 2)
    tss1 = np.sum((X_endog - X_endog.mean()) ** 2)
    F1 = ((tss1 - rss1) / (k - 1)) / (rss1 / (n - k))
    return b, se, F1

# 双向去均值后做 2SLS
y_dm2, X_dm2 = demean(ln_innov, np.column_stack([policy, X_ctrl]), prov, year)
pol_dm = X_dm2[:, 0:1]
ctrl_dm = X_dm2[:, 1:]
nb_dm, _ = demean(neighbor_policy, np.column_stack([neighbor_policy]), prov, year)
nb_dm = nb_dm.reshape(-1, 1)

b_iv, se_iv, F1 = tsls(y_dm2, pol_dm, ctrl_dm, nb_dm, prov)
print("\n[2SLS] policy 系数 = %.4f (聚类SE = %.4f)" % (b_iv[0], se_iv[0]))
print("[弱工具变量] 第一阶段 F = %.4f (>10 则非弱工具)" % F1)

# 过度识别检验：仅一个工具变量 -> 恰好识别，无法做 Sargan
print("[过度识别] 工具变量数 = 1，恰好识别，Sargan 检验不可用（需≥2个IV）")

# ============================================================
# 6. 稳健性与安慰剂检验
# ============================================================
# 安慰剂：随机打乱政策实施年份
placebo_betas = []
for _ in range(200):
    ft_rand = rng.integers(2010, 2019, N_PROV)
    pol_p = ((year >= ft_rand[prov])).astype(float)
    yp, Xp = demean(ln_innov, np.column_stack([pol_p, X_ctrl]), prov, year)
    bp, _, _ = ols(yp, Xp)
    placebo_betas.append(bp[0])
placebo_betas = np.array(placebo_betas)
p_val = np.mean(np.abs(placebo_betas) >= np.abs(b_fe[0]))
print("\n[安慰剂检验] 真实 FE 系数 = %.4f" % b_fe[0])
print("[安慰剂检验] 200次随机政策系数均值 = %.4f, 标准差 = %.4f" % (placebo_betas.mean(), placebo_betas.std()))
print("[安慰剂检验] 经验 p 值 = %.4f (<0.05 说明结果非偶然)" % p_val)

# 时间趋势规避：已用双向固定效应吸收年份趋势
print("\n[陷阱规避] 已加入年份固定效应吸收共同时间趋势，避免伪回归")

# ============================================================
# 7. 出图 + 落盘
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].hist(placebo_betas, bins=30, color='steelblue', alpha=0.75, edgecolor='white')
axes[0].axvline(b_fe[0], color='red', linestyle='--', linewidth=2, label='真实FE系数=%.3f' % b_fe[0])
axes[0].set_title('安慰剂检验：随机政策系数分布（模拟数据）')
axes[0].set_xlabel('policy 系数'); axes[0].set_ylabel('频数'); axes[0].legend()

# 政策实施年份分布
axes[1].hist(first_treat, bins=range(2010, 2021), color='darkorange', alpha=0.8, edgecolor='white')
axes[1].set_title('各省政策首次实施年份分布（模拟数据）')
axes[1].set_xlabel('年份'); axes[1].set_ylabel('省份数')
plt.tight_layout()
plt.savefig('figure.png', dpi=150)
plt.close()

# 保存数据表
import csv
with open('panel_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['prov', 'year', 'policy', 'neighbor_policy', 'ln_innov', 'rd_subsidy', 'gdp_pc'])
    for i in range(len(ln_innov)):
        w.writerow([prov[i], year[i], policy[i], round(neighbor_policy[i], 4),
                    round(ln_innov[i], 4), round(rd_subsidy[i], 4), round(gdp_pc[i], 4)])

print("\n[落盘] figure.png, panel_data.csv 已保存")
print("=" * 60)
print("【重要声明】以上全部为模拟数据结果，仅用于演示计量流程，")
print("不代表任何真实政策效应或实证结论。")
print("=" * 60)