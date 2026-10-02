# -*- coding: utf-8 -*-
"""
生存分析：肿瘤患者 5 年随访复发数据（模拟数据，非真实实验结论）
仅使用 numpy 2.5.3 + matplotlib 3.11.2 实现：
  - KM 曲线 + log-rank 检验
  - 删失机制说明与检查
  - Cox 比例风险模型（牛顿-拉夫森自实现）
  - 比例风险(PH)假设检验（Schoenfeld 残差相关检验）
  - 违反 PH 的变量做分层处理
  - 报告 HR、95%CI、中位生存期
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

rng = np.random.default_rng(20240517)
N = 600
# ============ 1. 模拟数据（明确标注：模拟数据） ============
# 检验指标特征：CEA, LDH, ALB, NLR, 年龄
age = rng.normal(60, 10, N)
cea = rng.lognormal(1.0, 0.6, N)          # 癌胚抗原
ldh = rng.normal(220, 60, N)              # 乳酸脱氢酶
alb = rng.normal(40, 5, N)                # 白蛋白
nlr = rng.lognormal(0.5, 0.4, N)          # 中性/淋巴比
stage = rng.integers(1, 4, N)             # 分期 1-3

# 真实风险（log 风险线性预测）
lp = (0.030 * (age - 60) + 0.35 * (cea - 2.7) + 0.004 * (ldh - 220)
      - 0.05 * (alb - 40) + 0.45 * (nlr - 1.6) + 0.55 * (stage - 2))
# 复发时间：指数分布（比例风险生成）
base_rate = 0.10
T_event = rng.exponential(1.0 / (base_rate * np.exp(lp)))
# 删失时间：独立行政删失（5 年随访上限 + 随机失访）
C = np.minimum(rng.exponential(1.0 / 0.05, N), 5.0)
time = np.minimum(T_event, C)
event = (T_event <= C).astype(int)   # 1=复发, 0=删失

X = np.column_stack([age, cea, ldh, alb, nlr, stage]).astype(float)
names = ['年龄', 'CEA', 'LDH', 'ALB', 'NLR', '分期']

print("=" * 60)
print("【模拟数据声明】以下全部结果基于模拟数据，非真实实验结论")
print(f"样本量 N={N}, 复发事件数={event.sum()}, 删失数={N-event.sum()}")
print(f"删失比例={1-event.mean():.3f}, 随访中位时间={np.median(time):.2f} 年")
print("删失机制：独立行政删失（随访上限5年）+ 随机失访，与事件独立")
print("=> 独立删失成立，可用标准 Cox/KM；若存在竞争风险需改用竞争风险模型")
print("   （本例无竞争风险事件，故不适用 Fine-Gray；见文末 TODO）")
print("=" * 60)

# ============ 2. KM 曲线 + log-rank 检验 ============
def km_estimate(t, e):
    order = np.argsort(t)
    t, e = t[order], e[order]
    uniq = np.unique(t[e == 1])
    n = len(t)
    S, times, surv = 1.0, [0.0], [1.0]
    for ut in uniq:
        at_risk = np.sum(t >= ut)
        d = np.sum((t == ut) & (e == 1))
        S *= (1 - d / at_risk)
        times.append(ut); surv.append(S)
    return np.array(times), np.array(surv)

def km_median(times, surv):
    idx = np.where(surv <= 0.5)[0]
    return times[idx[0]] if len(idx) else np.nan

# 按分期分组（1-2 vs 3）做 log-rank
grp = (stage >= 3).astype(int)
t_all, s_all = km_estimate(time, event)
med_all = km_median(t_all, s_all)
print(f"[KM] 全体中位无复发生存期 = {med_all:.2f} 年")

def logrank(t, e, g):
    gs = np.unique(g)
    O = np.zeros(len(gs)); E = np.zeros(len(gs)); V = np.zeros((len(gs), len(gs)))
    for ut in np.unique(t[e == 1]):
        at_risk = t >= ut
        n = at_risk.sum(); d = np.sum((t == ut) & (e == 1))
        for i, gi in enumerate(gs):
            ni = np.sum(at_risk & (g == gi))
            di = np.sum((t == ut) & (e == 1) & (g == gi))
            O[i] += di; E[i] += d * ni / n
            for j, gj in enumerate(gs):
                nj = np.sum(at_risk & (g == gj))
                if i == j:
                    V[i, j] += d * (ni/n) * (1-ni/n) * (n-d)/(n-1) if n > 1 else 0
                else:
                    V[i, j] += -d * (ni/n) * (nj/n) * (n-d)/(n-1) if n > 1 else 0
    diff = (O - E)[:-1]
    Vr = V[:-1, :-1]
    stat = float(diff @ np.linalg.pinv(Vr) @ diff)
    from math import erf, sqrt
    # 卡方 df=1 的 p 值近似
    p = 1 - erf(sqrt(stat/2)) if stat > 0 else 1.0
    return stat, p

lr_stat, lr_p = logrank(time, event, grp)
print(f"[Log-rank] 分期(1-2 vs 3) 卡方={lr_stat:.3f}, p={lr_p:.4f}")

# ============ 3. Cox 模型（牛顿-拉夫森） ============
def cox_fit(X, t, e, max_iter=50, tol=1e-8):
    n, p = X.shape
    beta = np.zeros(p)
    order = np.argsort(t)
    Xs, ts, es = X[order], t[order], e[order]
    for it in range(max_iter):
        eta = Xs @ beta
        eta -= eta.max()
        w = np.exp(eta)
        grad = np.zeros(p); hess = np.zeros((p, p))
        for i in range(n):
            if es[i] == 1:
                risk = np.arange(i, n)
                sw = w[risk].sum()
                xbar = (w[risk, None] * Xs[risk]).sum(0) / sw
                grad += Xs[i] - xbar
                xc = Xs[risk] - xbar
                hess -= (w[risk, None] * xc).T @ xc / sw
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            break
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new; break
        beta = beta_new
    # 方差：Hessian 逆
    cov = np.linalg.pinv(-hess)
    se = np.sqrt(np.diag(cov))
    return beta, se

beta, se = cox_fit(X, time, event)
z = beta / se
from math import erf, sqrt
pvals = np.array([2 * (1 - 0.5 * (1 + erf(abs(zz)/sqrt(2)))) for zz in z])
hr = np.exp(beta)
ci_lo = np.exp(beta - 1.96 * se)
ci_hi = np.exp(beta + 1.96 * se)

print("\n[Cox 模型] 风险比 HR (95% CI), p 值")
for i, nm in enumerate(names):
    print(f"  {nm:>4s}: HR={hr[i]:.3f} ({ci_lo[i]:.3f}-{ci_hi[i]:.3f}), p={pvals[i]:.4f}")
print("  注：HR 为相对风险，非绝对风险变化")

# ============ 4. PH 假设检验（Schoenfeld 残差与时间相关） ============
def ph_test(X, t, e, beta):
    n, p = X.shape
    order = np.argsort(t)
    Xs, ts, es = X[order], t[order], e[order]
    eta = Xs @ beta; eta -= eta.max(); w = np.exp(eta)
    res = np.zeros((n, p)); rtime = np.zeros(n)
    for i in range(n):
        if es[i] == 1:
            risk = np.arange(i, n)
            sw = w[risk].sum()
            xbar = (w[risk, None] * Xs[risk]).sum(0) / sw
            res[i] = Xs[i] - xbar
            rtime[i] = ts[i]
    mask = es == 1
    out = []
    for j in range(p):
        r = res[mask, j]; tt = rtime[mask]
        if np.std(r) < 1e-12:
            out.append((np.nan, np.nan)); continue
        corr = np.corrcoef(tt, r)[0, 1]
        stat = corr * np.sqrt(len(tt) - 2) / np.sqrt(max(1 - corr**2, 1e-12))
        pv = 2 * (1 - 0.5 * (1 + erf(abs(stat)/sqrt(2))))
        out.append((stat, pv))
    return out

ph = ph_test(X, time, event, beta)
print("\n[PH 假设检验] Schoenfeld 残差与时间相关")
violate = []
for i, nm in enumerate(names):
    st, pv = ph[i]
    flag = "违反" if (not np.isnan(pv) and pv < 0.05) else "满足"
    if flag == "违反":
        violate.append(nm)
    print(f"  {nm:>4s}: stat={st:.3f}, p={pv:.4f} -> {flag}")
print(f"  违反 PH 假设的变量: {violate if violate else '无'}")

# ============ 5. 对违反 PH 的变量做分层（示例：按分期分层） ============
if violate:
    print("\n[分层处理] 对违反 PH 的变量按分期分层拟合（strata=分期）")
    # 简化：分层 Cox 用分期作为分层变量，其余变量估计
    keep = [i for i, nm in enumerate(names) if nm not in violate]
    Xk = X[:, keep]
    # 分层似然：按 stage 分组累加
    def cox_strata(Xk, t, e, strata, max_iter=50, tol=1e-8):
        beta = np.zeros(Xk.shape[1])
        for it in range(max_iter):
            grad = np.zeros_like(beta); hess = np.zeros((len(beta), len(beta)))
            for s in np.unique(strata):
                m = strata == s
                Xs, ts, es = Xk[m], t[m], e[m]
                o = np.argsort(ts); Xs, ts, es = Xs[o], ts[o], es[o]
                eta = Xs @ beta; eta -= eta.max(); w = np.exp(eta)
                for i in range(len(ts)):
                    if es[i] == 1:
                        risk = np.arange(i, len(ts))
                        sw = w[risk].sum()
                        xbar = (w[risk, None] * Xs[risk]).sum(0) / sw
                        grad += Xs[i] - xbar
                        xc = Xs[risk] - xbar
                        hess -= (w[risk, None] * xc).T @ xc / sw
            try:
                step = np.linalg.solve(hess, grad)
            except np.linalg.LinAlgError:
                break
            beta_new = beta - step
            if np.max(np.abs(beta_new - beta)) < tol:
                beta = beta_new; break
            beta = beta_new
        cov = np.linalg.pinv(-hess)
        return beta, np.sqrt(np.diag(cov))
    bk, sek = cox_strata(Xk, time, event, stage)
    print("  分层 Cox 结果：")
    for i, idx in enumerate(keep):
        print(f"    {names[idx]:>4s}: HR={np.exp(bk[i]):.3f} "
              f"({np.exp(bk[i]-1.96*sek[i]):.3f}-{np.exp(bk[i]+1.96*sek[i]):.3f})")

# ============ 6. 出图 ============
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# KM 曲线（全体 + 分期分组）
for g, lab, c in [(0, '分期 1-2', 'tab:blue'), (1, '分期 3', 'tab:red')]:
    m = grp == g
    tt, ss = km_estimate(time[m], event[m])
    axes[0].step(tt, ss, where='post', label=f'{lab} (n={m.sum()})', color=c)
axes[0].axhline(0.5, ls='--', color='gray', lw=1)
axes[0].axvline(med_all, ls=':', color='green', lw=1)
axes[0].set_xlabel('随访时间 (年)'); axes[0].set_ylabel('无复发生存概率')
axes[0].set_title(f'KM 曲线（模拟数据）\nlog-rank p={lr_p:.4f}, 中位={med_all:.2f}年')
axes[0].legend(); axes[0].grid(alpha=0.3)

# 森林图
ypos = np.arange(len(names))
axes[1].errorbar(hr, ypos, xerr=[hr-ci_lo, ci_hi-hr], fmt='o', color='navy', capsize=4)
axes[1].axvline(1.0, ls='--', color='red', lw=1)
axes[1].set_yticks(ypos); axes[1].set_yticklabels(names)
axes[1].set_xscale('log'); axes[1].set_xlabel('风险比 HR (log 尺度)')
axes[1].set_title('Cox 模型森林图（模拟数据）')
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=150)
print("\n[输出] 图已保存: figure.png")

# ============ 7. 落盘 ============
import csv
with open('cox_results.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['变量', 'HR', 'CI_lower', 'CI_upper', 'p_value', 'PH_p'])
    for i, nm in enumerate(names):
        w.writerow([nm, f"{hr[i]:.4f}", f"{ci_lo[i]:.4f}", f"{ci_hi[i]:.4f}",
                    f"{pvals[i]:.4f}", f"{ph[i][1]:.4f}"])
with open('survival_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['time', 'event'] + names)
    for i in range(N):
        w.writerow([f"{time[i]:.4f}", event[i]] + [f"{X[i,j]:.4f}" for j in range(X.shape[1])])
print("[输出] cox_results.csv, survival_data.csv 已保存")

# TODO: 若存在竞争风险（如非复发死亡），应改用 Fine-Gray 亚分布风险模型，
#       避免 KM/Cox 高估复发累积发生率。
# TODO: 时变系数模型（如 tt() 交互项）可进一步处理违反 PH 的变量。