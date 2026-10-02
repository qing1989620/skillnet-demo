# -*- coding: utf-8 -*-
"""
生存分析：5年随访肿瘤患者复发数据（模拟数据）
仅使用 numpy / matplotlib 实现：
  - KM 曲线 + log-rank 检验
  - 删失独立性检查（简化：比较删失者与事件者的协变量分布）
  - Cox 比例风险模型（Newton-Raphson 拟合，Breslow 处理并列）
  - 比例风险(PH)假设检验（Schoenfeld 残差与时间相关检验）
  - 报告 HR、95%CI、中位生存期
注意：本脚本数据为【模拟数据】，结论仅用于演示流程，不代表真实临床结论。
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(20240517)

# ============================================================
# 1. 模拟数据（明确标注：模拟数据）
# ============================================================
N = 600
# 检验指标特征（电子病历常见指标，标准化后）
age = rng.normal(60, 10, N)                 # 年龄
CEA = rng.normal(5, 3, N)                   # 肿瘤标志物
ALB = rng.normal(40, 5, N)                  # 白蛋白
NLR = rng.lognormal(0.5, 0.4, N)            # 中性粒/淋巴比
LDH = rng.normal(200, 50, N)                # 乳酸脱氢酶

# 真实风险（log-hazard 线性预测子）
lp = (0.030 * (age - 60) + 0.060 * (CEA - 5)
      - 0.040 * (ALB - 40) + 0.500 * (NLR - 1.6)
      + 0.004 * (LDH - 200))
base_scale = 0.35  # 基线风险尺度
T_event = rng.exponential(1.0 / (base_scale * np.exp(lp)))  # 事件时间
C_censor = rng.uniform(0, 5, N)                             # 5年随访删失
time = np.minimum(T_event, C_censor)
event = (T_event <= C_censor).astype(int)
print("【模拟数据】样本量=%d, 复发事件数=%d, 删失数=%d" % (N, event.sum(), N - event.sum()))

X = np.column_stack([age, CEA, ALB, NLR, LDH])
names = ["age", "CEA", "ALB", "NLR", "LDH"]
# 标准化（避免量纲影响数值稳定性）
mu, sd = X.mean(0), X.std(0)
Xs = (X - mu) / sd

# ============================================================
# 2. KM 曲线 + log-rank 检验（按 NLR 高低分组）
# ============================================================
def km_estimate(t, e):
    order = np.argsort(t)
    t, e = t[order], e[order]
    ut = np.unique(t[e == 1])
    S, times, surv = 1.0, [0.0], [1.0]
    for u in ut:
        n_risk = np.sum(t >= u)
        d = np.sum((t == u) & (e == 1))
        S *= (1 - d / n_risk)
        times.append(u); surv.append(S)
    return np.array(times), np.array(surv)

def logrank(t, e, g):
    """两组 log-rank 检验，返回 chi2 与 p（卡方1自由度）"""
    ut = np.unique(t[e == 1])
    O1 = E1 = V = 0.0
    for u in ut:
        n1 = np.sum((t >= u) & (g == 1)); n0 = np.sum((t >= u) & (g == 0))
        d1 = np.sum((t == u) & (e == 1) & (g == 1))
        d0 = np.sum((t == u) & (e == 1) & (g == 0))
        n, d = n1 + n0, d1 + d0
        if n < 2 or d == 0: continue
        O1 += d1; E1 += d * n1 / n
        V += d * (n1 / n) * (1 - n1 / n) * (n - d) / (n - 1)
    chi2 = (O1 - E1) ** 2 / V if V > 0 else 0.0
    # 卡方(1) 的 p 值：p = erfc(sqrt(chi2/2))
    from math import erfc, sqrt
    p = erfc(sqrt(chi2 / 2.0))
    return chi2, p

grp = (NLR > np.median(NLR)).astype(int)
chi2, pval = logrank(time, event, grp)
print("【log-rank】NLR高低分组 chi2=%.3f, p=%.4f" % (chi2, pval))

# 中位生存期（KM 反推）
def median_surv(t, e):
    tt, ss = km_estimate(t, e)
    idx = np.where(ss <= 0.5)[0]
    return tt[idx[0]] if len(idx) else np.nan

print("【中位复发时间】全体=%.3f 年, NLR高组=%.3f 年, NLR低组=%.3f 年" % (
    median_surv(time, event),
    median_surv(time[grp == 1], event[grp == 1]),
    median_surv(time[grp == 0], event[grp == 0])))

# ============================================================
# 3. 删失独立性检查（简化：比较删失者 vs 事件者协变量均值）
# ============================================================
print("【删失独立性检查】比较删失组与事件组协变量均值（模拟数据）")
for j, nm in enumerate(names):
    m_c = Xs[event == 0, j].mean(); m_e = Xs[event == 1, j].mean()
    print("  %-4s 删失组均值=%+.3f 事件组均值=%+.3f 差异=%+.3f" % (nm, m_c, m_e, m_c - m_e))
print("  提示：若差异显著，提示删失可能非独立，需考虑竞争风险模型（此处仅演示检查）")

# ============================================================
# 4. Cox 比例风险模型（Newton-Raphson, Breslow 并列处理）
# ============================================================
def cox_fit(X, t, e, max_iter=50, tol=1e-8):
    n, p = X.shape
    beta = np.zeros(p)
    order = np.argsort(-t)  # 从大到小，便于累积风险集
    Xo, to, eo = X[order], t[order], e[order]
    for it in range(max_iter):
        eta = Xo @ beta
        eta -= eta.max()
        w = np.exp(eta)
        # 风险集累积（按时间从大到小）
        cum_w = np.cumsum(w)
        cum_wx = np.cumsum(w[:, None] * Xo, axis=0)
        cum_wxx = np.cumsum(w[:, None, None] * (Xo[:, :, None] * Xo[:, None, :]), axis=0)
        grad = np.zeros(p); hess = np.zeros((p, p))
        for i in range(n):
            if eo[i] == 0: continue
            S0 = cum_w[i]; S1 = cum_wx[i]; S2 = cum_wxx[i]
            mu = S1 / S0
            grad += Xo[i] - mu
            hess -= (S2 / S0 - np.outer(mu, mu))
        # Newton 步
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            break
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new; break
        beta = beta_new
    # 方差：-Hessian 的逆
    cov = np.linalg.inv(-hess)
    se = np.sqrt(np.diag(cov))
    return beta, se

beta, se = cox_fit(Xs, time, event)
z = beta / se
from math import erfc, sqrt
pvals = np.array([erfc(abs(zz) / sqrt(2)) for zz in z])
HR = np.exp(beta)
CI_lo = np.exp(beta - 1.96 * se)
CI_hi = np.exp(beta + 1.96 * se)

print("【Cox 模型】HR (95%CI), p 值（标准化后每 1 SD 变化）")
for j, nm in enumerate(names):
    print("  %-4s HR=%.3f (%.3f-%.3f), p=%.4f" % (nm, HR[j], CI_lo[j], CI_hi[j], pvals[j]))

# ============================================================
# 5. PH 假设检验（Schoenfeld 残差与时间相关，简化版）
# ============================================================
def ph_test(X, t, e, beta):
    """简化：Schoenfeld 残差与 log(t) 的相关性检验"""
    n, p = X.shape
    order = np.argsort(-t)
    Xo, to, eo = X[order], t[order], e[order]
    eta = Xo @ beta; eta -= eta.max(); w = np.exp(eta)
    cum_w = np.cumsum(w); cum_wx = np.cumsum(w[:, None] * Xo, axis=0)
    res = []; tt = []
    for i in range(n):
        if eo[i] == 0: continue
        S0 = cum_w[i]; S1 = cum_wx[i]
        res.append(Xo[i] - S1 / S0)
        tt.append(to[i])
    res = np.array(res); tt = np.log(np.array(tt) + 1e-9)
    out = []
    for j in range(p):
        r = res[:, j]
        if r.std() < 1e-12:
            out.append((0.0, 1.0)); continue
        c = np.corrcoef(r, tt)[0, 1]
        # 近似：chi2 = (n-1)*c^2
        chi2 = (len(r) - 1) * c ** 2
        p = erfc(sqrt(chi2 / 2.0))
        out.append((chi2, p))
    return out

print("【PH 假设检验】Schoenfeld 残差与 log(t) 相关（p<0.05 提示违反 PH）")
ph_res = ph_test(Xs, time, event, beta)
for j, nm in enumerate(names):
    print("  %-4s chi2=%.3f, p=%.4f %s" % (nm, ph_res[j][0], ph_res[j][1],
          "<-- 违反PH，建议时变系数/分层" if ph_res[j][1] < 0.05 else ""))

# ============================================================
# 6. 出图：KM 曲线（NLR 高低分组）
# ============================================================
fig, ax = plt.subplots(figsize=(7, 5))
for g, lab, col in [(0, "NLR 低组", "tab:blue"), (1, "NLR 高组", "tab:red")]:
    tt, ss = km_estimate(time[grp == g], event[grp == g])
    ax.step(tt, ss, where="post", label=lab, color=col)
ax.set_xlabel("随访时间（年）")
ax.set_ylabel("无复发生存概率")
ax.set_title("KM 曲线（模拟数据）NLR 高低分组\nlog-rank p=%.4f" % pval)
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("figure.png", dpi=150)
plt.close()

# ============================================================
# 7. 落盘
# ============================================================
import csv
with open("cox_results.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["variable", "HR", "CI_low", "CI_high", "p_value", "PH_p"])
    for j, nm in enumerate(names):
        w.writerow([nm, "%.4f" % HR[j], "%.4f" % CI_lo[j],
                    "%.4f" % CI_hi[j], "%.4f" % pvals[j], "%.4f" % ph_res[j][1]])

with open("survival_data.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["time", "event"] + names)
    for i in range(N):
        w.writerow(["%.4f" % time[i], event[i]] + ["%.4f" % X[i, j] for j in range(len(names))])

print("已保存: figure.png, cox_results.csv, survival_data.csv")
print("【声明】以上结果基于模拟数据，仅用于演示生存分析流程，非真实临床结论。")