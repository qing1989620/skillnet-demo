# -*- coding: utf-8 -*-
"""
省级面板数据：产业政策对企业创新的影响（DID / 交错处理 + 内生性处理 + 稳健性）
注意：本脚本使用【模拟数据】，所有数值结果均为模拟演示，不代表任何真实结论。
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
N_PROV = 20          # 省份数
YEARS = np.arange(2008, 2021)  # 13 年
T = len(YEARS)

# 各省政策推行年份（交错处理），部分省份从未处理
policy_year = {}
for i in range(N_PROV):
    if i < 14:
        policy_year[i] = int(rng.choice([2012, 2014, 2016, 2018]))
    else:
        policy_year[i] = 9999  # 从未处理（never-treated）

# 省份固定效应
prov_fe = rng.normal(0, 0.5, N_PROV)
# 年份固定效应
year_fe = {y: 0.15 * (y - YEARS[0]) for y in YEARS}

rows = []
for i in range(N_PROV):
    for t_idx, y in enumerate(YEARS):
        treated = 1 if y >= policy_year[i] else 0
        # 内生性来源：政策推行与省份潜在创新能力相关（选择性）
        selection = 0.6 * prov_fe[i] if policy_year[i] != 9999 else 0.0
        # 创新产出（对数专利数）
        innov = (2.0 + prov_fe[i] + year_fe[y]
                 + 0.35 * treated
                 + selection
                 + rng.normal(0, 0.3))
        # 控制变量
        gdp = 9.0 + 0.2 * (y - YEARS[0]) + 0.5 * prov_fe[i] + rng.normal(0, 0.2)
        rd = 1.5 + 0.1 * (y - YEARS[0]) + 0.3 * prov_fe[i] + rng.normal(0, 0.15)
        rows.append([i, y, treated, innov, gdp, rd, policy_year[i]])

data = np.array(rows)
prov_id = data[:, 0].astype(int)
year = data[:, 1].astype(int)
treat = data[:, 2]
innov = data[:, 3]
gdp = data[:, 4]
rd = data[:, 5]
py = data[:, 6].astype(int)

print("=" * 60)
print("【模拟数据】样本量: %d 省 × %d 年 = %d 观测" % (N_PROV, T, len(data)))
print("处理组省份数: %d, 从未处理省份数: %d"
      % (np.sum(np.unique(py) < 9999), np.sum(np.unique(py) == 9999)))

# ============================================================
# 2. 已知陷阱检查
# ============================================================
print("\n[陷阱检查]")
# 陷阱1：交错处理下 TWFE 存在负权重问题 -> 检查处理时点分布
uniq_py, cnt_py = np.unique(py[py < 9999], return_counts=True)
print("  政策推行年份分布(省数):", dict(zip(uniq_py.tolist(), cnt_py.tolist())))
print("  -> 交错处理，普通TWFE可能受负权重影响，需用堆叠DID/事件研究佐证")

# 陷阱2：平行趋势前提 -> 检查处理前趋势
pre_mask = (py < 9999) & (year < py)
print("  处理前观测数: %d (用于平行趋势检验)" % np.sum(pre_mask))

# 陷阱3：政策内生性 -> 检查处理组与对照组处理前创新均值差异
never = py == 9999
pre_never = (year < 2012) & never
pre_treat = (year < 2012) & (py < 9999)
print("  处理前创新均值: 处理组=%.3f, 对照组=%.3f, 差异=%.3f"
      % (innov[pre_treat].mean(), innov[pre_never].mean(),
         innov[pre_treat].mean() - innov[pre_never].mean()))
print("  -> 存在选择性差异，需控制省份固定效应并做内生性处理")

# ============================================================
# 3. 双向固定效应 DID（手工 OLS，含省份与年份虚拟变量）
# ============================================================
def twfe_did(y, treat, prov_id, year, controls=None):
    n = len(y)
    # 构造设计矩阵：常数 + treat + 省份FE + 年份FE (+ 控制变量)
    X = [np.ones(n), treat]
    for p in np.unique(prov_id)[1:]:
        X.append((prov_id == p).astype(float))
    for yr in np.unique(year)[1:]:
        X.append((year == yr).astype(float))
    if controls is not None:
        for c in controls:
            X.append(c)
    X = np.column_stack(X)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = n - X.shape[1]
    sigma2 = resid @ resid / dof
    XtX_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(XtX_inv) * sigma2)
    return beta[1], se[1]

beta_did, se_did = twfe_did(innov, treat, prov_id, year)
print("\n[基准 TWFE-DID]")
print("  政策效应 = %.4f (标准误 %.4f, t = %.2f)"
      % (beta_did, se_did, beta_did / se_did))

# 加入控制变量
beta_did2, se_did2 = twfe_did(innov, treat, prov_id, year, controls=[gdp, rd])
print("  加入控制变量后 = %.4f (标准误 %.4f, t = %.2f)"
      % (beta_did2, se_did2, beta_did2 / se_did2))

# ============================================================
# 4. 内生性处理：工具变量（模拟一个外生工具）
# ============================================================
# 模拟工具变量：与政策推行相关，但与创新误差不直接相关
iv = 0.8 * treat + rng.normal(0, 0.5, len(treat))
# 2SLS 第一阶段
X1 = np.column_stack([np.ones(len(iv)), iv])
b1, *_ = np.linalg.lstsq(X1, treat, rcond=None)
treat_hat = X1 @ b1
# 第二阶段
beta_iv, se_iv = twfe_did(innov, treat_hat, prov_id, year)
print("\n[内生性处理: 2SLS-IV]")
print("  第一阶段系数 = %.4f (工具相关性)" % b1[1])
print("  IV 估计政策效应 = %.4f (标准误 %.4f)" % (beta_iv, se_iv))

# ============================================================
# 5. 稳健性检验
# ============================================================
print("\n[稳健性检验]")
# (a) 安慰剂：随机打乱处理时点
placebo = []
for _ in range(50):
    fake_py = rng.choice([2012, 2014, 2016, 2018], size=N_PROV)
    fake_treat = np.zeros(len(year))
    for i in range(N_PROV):
        fake_treat[prov_id == i] = (year[prov_id == i] >= fake_py[i]).astype(float)
    b, _ = twfe_did(innov, fake_treat, prov_id, year)
    placebo.append(b)
placebo = np.array(placebo)
print("  安慰剂检验(50次随机处理): 均值=%.4f, 真实估计=%.4f, p值≈%.3f"
      % (placebo.mean(), beta_did, np.mean(np.abs(placebo) >= abs(beta_did))))

# (b) 替换被解释变量：用 rd 作为替代创新指标
beta_alt, se_alt = twfe_did(rd, treat, prov_id, year)
print("  替换被解释变量(R&D投入) = %.4f (标准误 %.4f)" % (beta_alt, se_alt))

# (c) 剔除政策当年（避免预期效应）
mask = ~((year == py) & (py < 9999))
beta_ex, se_ex = twfe_did(innov[mask], treat[mask], prov_id[mask], year[mask])
print("  剔除政策当年 = %.4f (标准误 %.4f)" % (beta_ex, se_ex))

# ============================================================
# 6. 事件研究（平行趋势 + 动态效应）
# ============================================================
print("\n[事件研究]")
rel = np.where(py < 9999, year - py, -999)
rel = np.clip(rel, -5, 5)
rel = np.where(py == 9999, -999, rel)
event_coef = {}
for k in range(-5, 6):
    if k == -1:
        continue
    d = (rel == k).astype(float)
    b, _ = twfe_did(innov, d, prov_id, year)
    event_coef[k] = b
print("  事件研究系数(相对政策年):")
for k in sorted(event_coef):
    print("    k=%+d: %.4f" % (k, event_coef[k]))

# ============================================================
# 7. 出图
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

# 左图：处理组 vs 对照组创新趋势
ax = axes[0]
for label, cond in [("处理组", py < 9999), ("对照组(从未处理)", py == 9999)]:
    means = [innov[(year == y) & cond].mean() for y in YEARS]
    ax.plot(YEARS, means, marker='o', label=label)
ax.set_title("创新产出趋势（模拟数据）")
ax.set_xlabel("年份")
ax.set_ylabel("创新产出(对数专利)")
ax.legend()
ax.grid(alpha=0.3)

# 右图：事件研究
ax = axes[1]
ks = sorted(event_coef)
ax.plot(ks, [event_coef[k] for k in ks], marker='o', color='crimson')
ax.axhline(0, color='gray', linestyle='--')
ax.axvline(-1, color='gray', linestyle=':')
ax.set_title("事件研究：动态政策效应（模拟数据）")
ax.set_xlabel("相对政策年份")
ax.set_ylabel("估计系数")
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("\n图已保存: figure.png")

# ============================================================
# 8. 落盘
# ============================================================
np.savetxt("panel_data.csv",
           np.column_stack([prov_id, year, treat, innov, gdp, rd, py]),
           delimiter=",", header="prov_id,year,treat,innov,gdp,rd,policy_year",
           comments="", fmt="%.4f")
print("数据已保存: panel_data.csv")

print("\n" + "=" * 60)
print("【重要声明】以上全部为模拟数据结果，仅用于演示方法流程，")
print("不代表任何真实政策效应或实证结论。")
print("=" * 60)