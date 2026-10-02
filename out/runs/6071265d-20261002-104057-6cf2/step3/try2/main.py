import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv, os, glob

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 定位输入文件（容错：当前目录 / 上级目录 / 递归搜索） ----------
def locate(name):
    cands = [name, os.path.join('..', name), os.path.join('..', '..', name)]
    for c in cands:
        if os.path.exists(c):
            return c
    hits = glob.glob(os.path.join('**', name), recursive=True)
    if hits:
        return hits[0]
    return None

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def load_any(names):
    for n in names:
        p = locate(n)
        if p:
            print("[定位] %s -> %s" % (n, p))
            return read_csv(p)
    return None

clean = load_any(['step1_clean_data.csv', 'clean_data.csv'])
audit = load_any(['step1_audit_log.csv', 'audit_log.csv'])
ddict = load_any(['step1_data_dictionary.csv', 'data_dictionary.csv'])
gstats = load_any(['step2_step2_group_stats.csv', 'step2_group_stats.csv', 'group_stats.csv'])

if clean is None:
    raise FileNotFoundError("未找到 step1_clean_data.csv，请确认输入文件已生成")

print("=== 输入文件读取 ===")
print("clean_data 行数:", len(clean), "列:", list(clean[0].keys()))
print("audit_log 行数:", len(audit) if audit else 0)
print("data_dictionary 行数:", len(ddict) if ddict else 0)
print("group_stats 行数:", len(gstats) if gstats else 0)

# ---------- 识别列名 ----------
cols = list(clean[0].keys())
def find_col(cands):
    for c in cols:
        for k in cands:
            if k.lower() in c.lower():
                return c
    return None

dose_col = find_col(['dose', 'conc', '剂量'])
resp_col = find_col(['response', 'inhib', 'viab', '抑制', '存活'])
rep_col  = find_col(['replicate', 'rep', '孔'])
grp_col  = find_col(['group', 'batch', '组'])

print("识别列 -> dose:", dose_col, "response:", resp_col, "replicate:", rep_col, "group:", grp_col)
if dose_col is None or resp_col is None:
    raise ValueError("无法识别剂量或响应列，请检查列名")

# ---------- 解析数据 ----------
dose = np.array([float(r[dose_col]) for r in clean])
resp = np.array([float(r[resp_col]) for r in clean])
rep  = np.array([r[rep_col] for r in clean]) if rep_col else np.array(['R']*len(clean))
grp  = np.array([r[grp_col] for r in clean]) if grp_col else np.array(['G']*len(clean))

# 单位统一：若剂量最大值 > 1000 视为 nM -> μM
if dose.max() > 1000:
    print("[单位统一] 剂量最大值 %.1f > 1000，判定为 nM，转换为 μM" % dose.max())
    dose = dose / 1000.0
else:
    print("[单位统一] 剂量范围 [%.4g, %.4g]，按 μM 处理" % (dose.min(), dose.max()))

# 抑制率统一为 0-1
if resp.max() > 1.5:
    print("[响应统一] 响应最大值 %.2f > 1.5，判定为百分数，除以 100" % resp.max())
    resp = resp / 100.0
else:
    print("[响应统一] 响应范围 [%.3f, %.3f]，按 0-1 处理" % (resp.min(), resp.max()))

# 剂量必须为正才能取 log
if dose.min() <= 0:
    print("[警告] 存在非正剂量，剔除 %d 个点" % int((dose <= 0).sum()))
    keep = dose > 0
    dose, resp, rep, grp = dose[keep], resp[keep], rep[keep], grp[keep]

# 异常点标记（不删除）：|z|>3 基于同剂量分组
logd = np.log10(dose)
outlier = np.zeros(len(resp), dtype=bool)
for d in np.unique(dose):
    m = dose == d
    if m.sum() >= 3:
        mu, sd = resp[m].mean(), resp[m].std()
        if sd > 0:
            outlier[m] = np.abs((resp[m]-mu)/sd) > 3
print("[异常点] 标记 %d 个异常点（保留不删除）" % outlier.sum())

# ---------- 分组统计 ----------
udoses = np.unique(dose)
means, sds, ns = [], [], []
for d in udoses:
    m = dose == d
    means.append(resp[m].mean())
    sds.append(resp[m].std() if m.sum() > 1 else 0.0)
    ns.append(m.sum())
means, sds, ns = np.array(means), np.array(sds), np.array(ns)
print("[分组] 剂量点数 %d, n<3 的低置信点: %d" % (len(udoses), int((ns < 3).sum())))

# 平台期检查
low_ok = means[0] < 0.15
high_ok = means[-1] > 0.85
print("[平台期] 最低剂量抑制率 %.3f (接近0: %s), 最高剂量抑制率 %.3f (接近100%%: %s)"
      % (means[0], low_ok, means[-1], high_ok))

# ---------- 4PL 模型 ----------
def pl4(x, bottom, top, logIC50, hill):
    return bottom + (top-bottom)/(1.0 + 10.0**((logIC50-x)*hill))

def pl3_bottom0(x, top, logIC50, hill):
    return top/(1.0 + 10.0**((logIC50-x)*hill))

def pl3_top100(x, bottom, logIC50, hill):
    return bottom + (1.0-bottom)/(1.0 + 10.0**((logIC50-x)*hill))

def sse(fn, params, x, y):
    return float(np.sum((y - fn(x, *params))**2))

def nelder_mead(fn, x0, x, y, maxiter=2000, tol=1e-10):
    n = len(x0)
    simplex = [np.array(x0, dtype=float)]
    for i in range(n):
        p = np.array(x0, dtype=float)
        p[i] += 0.1 if p[i] == 0 else 0.1*abs(p[i]) + 0.01
        simplex.append(p)
    simplex = np.array(simplex)
    fvals = np.array([sse(fn, s, x, y) for s in simplex])
    for _ in range(maxiter):
        idx = np.argsort(fvals); simplex = simplex[idx]; fvals = fvals[idx]
        if abs(fvals[-1]-fvals[0]) < tol*(abs(fvals[0])+tol):
            break
        centroid = simplex[:-1].mean(axis=0)
        xr = centroid + (centroid - simplex[-1]); fr = sse(fn, xr, x, y)
        if fr < fvals[0]:
            xe = centroid + 2*(centroid - simplex[-1]); fe = sse(fn, xe, x, y)
            simplex[-1], fvals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < fvals[-2]:
            simplex[-1], fvals[-1] = xr, fr
        else:
            xc = centroid + 0.5*(simplex[-1]-centroid); fc = sse(fn, xc, x, y)
            if fc < fvals[-1]:
                simplex[-1], fvals[-1] = xc, fc
            else:
                for i in range(1, n+1):
                    simplex[i] = simplex[0] + 0.5*(simplex[i]-simplex[0])
                    fvals[i] = sse(fn, simplex[i], x, y)
    idx = np.argsort(fvals)
    return simplex[idx[0]], fvals[idx[0]]

# 初始值
b0 = float(np.clip(means[0], 0, 0.2))
t0 = float(np.clip(means[-1], 0.8, 1.0))
li0 = float(np.median(logd))
h0 = 1.0

# 4PL 拟合
p4, sse4 = nelder_mead(pl4, [b0, t0, li0, h0], logd, resp)
print("\n=== 4PL 拟合 ===")
print("Bottom=%.4f Top=%.4f logIC50=%.4f HillSlope=%.4f SSE=%.6f" % (p4[0], p4[1], p4[2], p4[3], sse4))
print("IC50 = %.4f μM" % (10**p4[2]))

# 嵌套模型选择
use3pl = None
if low_ok and not high_ok:
    use3pl = 'bottom0'
elif high_ok and not low_ok:
    use3pl = 'top100'
elif low_ok and high_ok:
    use3pl = 'bottom0'

p3, sse3, k3, k4 = None, None, None, 4
if use3pl == 'bottom0':
    p3, sse3 = nelder_mead(pl3_bottom0, [t0, li0, h0], logd, resp); k3 = 3
    print("\n=== 3PL (Bottom=0) 拟合 ===")
    print("Top=%.4f logIC50=%.4f HillSlope=%.4f SSE=%.6f" % (p3[0], p3[1], p3[2], sse3))
    print("IC50 = %.4f μM" % (10**p3[1]))
elif use3pl == 'top100':
    p3, sse3 = nelder_mead(pl3_top100, [b0, li0, h0], logd, resp); k3 = 3
    print("\n=== 3PL (Top=100) 拟合 ===")
    print("Bottom=%.4f logIC50=%.4f HillSlope=%.4f SSE=%.6f" % (p3[0], p3[1], p3[2], sse3))
    print("IC50 = %.4f μM" % (10**p3[1]))

# F 检验比较嵌套模型
n_obs = len(resp)
if p3 is not None:
    df1 = k4 - k3
    df2 = n_obs - k4
    if df2 > 0 and sse3 > sse4:
        F = ((sse3 - sse4)/df1) / (sse4/df2)
        rng = np.random.default_rng(42)
        Fsim = (rng.chisquare(df1, 20000)/df1) / (rng.chisquare(df2, 20000)/df2)
        pval = float((Fsim > F).mean())
        print("\n=== F 检验 (4PL vs 3PL) ===")
        print("F=%.4f, df1=%d, df2=%d, p=%.4f (Monte Carlo 近似)" % (F, df1, df2, pval))
        print("α=0.05, 结论: %s" % ("拒绝 3PL，采用 4PL" if pval < 0.05 else "不拒绝 3PL，采用更简模型"))
    else:
        print("\n[F检验] SSE3 <= SSE4 或 df2<=0，跳过")

# 最终模型
if p3 is not None and sse3 <= sse4:
    final_fn = pl3_bottom0 if use3pl == 'bottom0' else pl3_top100
    final_p, final_name = p3, '3PL'
    logIC50_hat = p3[1]; hill_hat = p3[2]
else:
    final_fn, final_p, final_name = pl4, p4, '4PL'
    logIC50_hat = p4[2]; hill_hat = p4[3]
print("\n最终模型: %s, logIC50=%.4f, HillSlope=%.4f" % (final_name, logIC50_hat, hill_hat))

# ---------- Bootstrap IC50 区间（分层按 group） ----------
def fit_ic50(xb, yb, init):
    if final_name == '4PL':
        pb, _ = nelder_mead(pl4, init, xb, yb, maxiter=500)
        return 10**pb[2]
    elif use3pl == 'bottom0':
        pb, _ = nelder_mead(pl3_bottom0, init, xb, yb, maxiter=500)
        return 10**pb[1]
    else:
        pb, _ = nelder_mead(pl3_top100, init, xb, yb, maxiter=500)
        return 10**pb[1]

def bootstrap_ic50(seed, B):
    rng = np.random.default_rng(seed)
    groups = np.unique(grp)
    out = []
    for _ in range(B):
        idx = []
        for g in groups:
            gi = np.where(grp == g)[0]
            idx.extend(rng.choice(gi, size=len(gi), replace=True))
        idx = np.array(idx)
        try:
            out.append(fit_ic50(logd[idx], resp[idx], final_p))
        except Exception:
            pass
    return np.array(out)

B = 10000
boot_ic50 = bootstrap_ic50(20240607, B)
if len(boot_ic50) == 0:
    raise RuntimeError("Bootstrap 全部失败")
ci_lo, ci_hi = np.percentile(boot_ic50, [2.5, 97.5])
print("\n=== Bootstrap IC50 (B=%d, 分层按 group) ===" % B)
print("有效 bootstrap 样本: %d" % len(boot_ic50))
print("IC50 点估计 = %.4f μM" % (10**logIC50_hat))
print("95%% CI = [%.4f, %.4f] μM" % (ci_lo, ci_hi))

print("\n=== Bootstrap 收敛检查 (n 梯度) ===")
for nb in [10, 100, 1000, 10000]:
    sub = boot_ic50[:min(nb, len(boot_ic50))]
    if len(sub) > 1:
        print("n=%5d: IC50 均值=%.4f, SD=%.4f" % (nb, sub.mean(), sub.std()))

boot2 = bootstrap_ic50(999, 2000)
ci2 = np.percentile(boot2, [2.5, 97.5])
print("\n=== 换种子稳健性 (seed=999, B=2000) ===")
print("95%% CI = [%.4f, %.4f] μM, 方向一致: %s" % (ci2[0], ci2[1], (ci2[0] < 10**logIC50_hat < ci2[1])))

print("\n=== HillSlope 敏感性 ===")
print("HillSlope=%.4f, |Hill| 接近0: %s, |Hill|>10: %s" % (hill_hat, abs(hill_hat) < 0.1, abs(hill_hat) > 10))

# 残差诊断
resid = resp - final_fn(logd, *final_p)
print("\n=== 残差诊断 ===")
print("残差均值=%.5f, SD=%.5f, 最大|残差|=%.5f" % (resid.mean(), resid.std(), np.abs(resid).max()))
if resid.std() > 0:
    corr = np.corrcoef(logd, resid)[0, 1]
    print("残差 vs log10(dose) 相关系数 = %.4f (系统趋势: %s)" % (corr, abs(corr) > 0.3))

# 含/不含异常点敏感性
mask = ~outlier
if mask.sum() > 5:
    ic50_s = fit_ic50(logd[mask], resp[mask], final_p)
    print("\n=== 含/不含异常点敏感性 ===")
    print("含异常点 IC50=%.4f, 不含异常点 IC50=%.4f, 相对偏差=%.2f%%"
          % (10**logIC50_hat, ic50_s, abs(ic50_s-10**logIC50_hat)/(10**logIC50_hat)*100))

# ---------- 绘图 ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
okabe = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#F0E442']

ax = axes[0]
ax.errorbar(udoses, means, yerr=sds, fmt='o', color=okabe[0], ecolor=okabe[0],
            capsize=3, markersize=6, label='均值±SD', zorder=3)
xs = np.linspace(logd.min()-0.3, logd.max()+0.3, 300)
ys = final_fn(xs, *final_p)
ax.plot(10**xs, ys, '-', color=okabe[1], lw=2, label='%s 拟合' % final_name)
ax.axvline(10**logIC50_hat, color=okabe[2], ls='--', lw=1.2,
           label='IC50=%.3f μM\n95%%CI [%.3f, %.3f]' % (10**logIC50_hat, ci_lo, ci_hi))
ax.set_xscale('log')
ax.set_xlabel('剂量 (μM, log scale)', fontsize=9)
ax.set_ylabel('抑制率', fontsize=9)
ax.set_title('剂量-响应曲线 (%s, HillSlope=%.2f, n=%d)' % (final_name, hill_hat, n_obs), fontsize=10)
ax.legend(fontsize=7, loc='best')
ax.grid(alpha=0.3)
ax.tick_params(labelsize=8)

ax2 = axes[1]
ax2.scatter(logd, resid, c=okabe[0], s=25, alpha=0.7, label='残差')
ax2.axhline(0, color='gray', ls='--', lw=1)
ax2.set_xlabel('log10(剂量 μM)', fontsize=9)
ax2.set_ylabel('残差', fontsize=9)
ax2.set_title('残差诊断 (均值=%.4f, SD=%.4f)' % (resid.mean(), resid.std()), fontsize=10)
ax2.legend(fontsize=7)
ax2.grid(alpha=0.3)
ax2.tick_params(labelsize=8)

plt.tight_layout()
plt.savefig('figure.png', dpi=150, bbox_inches='tight')
plt.savefig('figure.pdf', bbox_inches='tight')
print("\n[输出] figure.png / figure.pdf 已保存")

# ---------- 落盘 ----------
with open('step3_ic50_estimates.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['model', 'Bottom', 'Top', 'logIC50', 'IC50_uM', 'IC50_CI_low', 'IC50_CI_high', 'HillSlope', 'SSE', 'n_obs'])
    if final_name == '4PL':
        w.writerow(['4PL', p4[0], p4[1], p4[2], 10**p4[2], ci_lo, ci_hi, p4[3], sse4, n_obs])
    elif use3pl == 'bottom0':
        w.writerow(['3PL_Bottom0', 0.0, p3[0], p3[1], 10**p3[1], ci_lo, ci_hi, p3[2], sse3, n_obs])
    else:
        w.writerow(['3PL_Top100', p3[0], 1.0, p3[1], 10**p3[1], ci_lo, ci_hi, p3[2], sse3, n_obs])

with open('step3_bootstrap_audit.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['item', 'value'])
    w.writerow(['bootstrap_B', B])
    w.writerow(['resample_unit', 'group (独立实验批次)'])
    w.writerow(['seed', 20240607])
    w.writerow(['IC50_point', 10**logIC50_hat])
    w.writerow(['IC50_CI_low', ci_lo])
    w.writerow(['IC50_CI_high', ci_hi])
    w.writerow(['seed2_CI_low', ci2[0]])
    w.writerow(['seed2_CI_high', ci2[1]])
    w.writerow(['n_outliers', int(outlier.sum())])
    w.writerow(['n_obs', n_obs])

with open('step3_clean_with_flags.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['dose_uM', 'response', 'replicate', 'group', 'outlier_flag'])
    for i in range(len(dose)):
        w.writerow([dose[i], resp[i], rep[i], grp[i], int(outlier[i])])

print("\n[输出] step3_ic50_estimates.csv / step3_bootstrap_audit.csv / step3_clean_with_flags.csv 已保存")
print("\n=== 完成 ===")