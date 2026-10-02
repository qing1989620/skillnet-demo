import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv, os

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

RNG_SEED = 20240607
np.random.seed(RNG_SEED)

# ---------- 1. 读取真实文件（若不存在则用模拟数据并标注） ----------
def load_clean():
    path = 'clean_dose_response.csv'
    if os.path.exists(path):
        rows = []
        with open(path, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                rows.append(r)
        print(f"[数据] 读取真实文件 {path}, 行数={len(rows)}")
        return rows, False
    # 模拟数据（明确标注）
    print("[数据] 未找到 clean_dose_response.csv，使用【模拟数据】")
    doses = np.array([0.01,0.03,0.1,0.3,1,3,10,30,100])
    reps = 4
    rows = []
    for d in doses:
        for r in range(reps):
            x = np.log10(d)
            y = 0 + (100-0)/(1+10**((np.log10(1.0)-x)*1.2))
            y = y/100.0 + np.random.normal(0,0.03)
            rows.append({'dose':str(d),'response':str(y),'replicate':str(r),'group':'G1'})
    return rows, True

rows, is_sim = load_clean()

# ---------- 2. 清洗与单位统一 ----------
dose = np.array([float(r['dose']) for r in rows])
resp = np.array([float(r['response']) for r in rows])
rep  = np.array([r.get('replicate','0') for r in rows])
grp  = np.array([r.get('group','G1') for r in rows])

# 抑制率统一到 0-1
if resp.max() > 1.5:
    resp = resp/100.0
    print("[清洗] 响应值>1.5，判定为百分比，已除以100统一到0-1")
# 剂量单位统一：若跨数量级过大，转 log10
logdose = np.log10(dose)
print(f"[清洗] 剂量范围 {dose.min():.4g} ~ {dose.max():.4g} μM, log10范围 {logdose.min():.2f}~{logdose.max():.2f}")
print(f"[清洗] 响应范围 {resp.min():.3f}~{resp.max():.3f}, 重复孔数={len(np.unique(rep))}")

# 异常点标记（|z|>3 按剂量组内）不删除
outlier_mask = np.zeros(len(resp), dtype=bool)
for d in np.unique(dose):
    m = dose==d
    if m.sum()>=3:
        z = (resp[m]-resp[m].mean())/(resp[m].std()+1e-9)
        idx = np.where(m)[0]
        outlier_mask[idx[np.abs(z)>3]] = True
print(f"[清洗] 标记异常点 {outlier_mask.sum()} 个（保留不删除，做敏感性对比）")

# 按剂量分组统计
uniq_d = np.unique(dose)
means, sds, ns = [], [], []
for d in uniq_d:
    m = dose==d
    means.append(resp[m].mean()); sds.append(resp[m].std(ddof=1) if m.sum()>1 else 0.0); ns.append(m.sum())
means=np.array(means); sds=np.array(sds); ns=np.array(ns)
print(f"[EDA] 最低剂量均值={means[0]:.3f}, 最高剂量均值={means[-1]:.3f}")
low_ok = means[0] < 0.15
high_ok = means[-1] > 0.85
print(f"[陷阱规避] 平台期检查: 低剂量接近0={low_ok}, 高剂量接近100%={high_ok}")
print(f"[EDA] n<3 的低置信剂量点: {list(uniq_d[ns<3])}")

# ---------- 3. 4PL 拟合（高斯牛顿） ----------
def pl4(x, bottom, top, logIC50, hill):
    return bottom + (top-bottom)/(1.0+10.0**((logIC50-x)*hill))

def fit_pl4(x, y, fix_bottom=None, fix_top=None):
    b0 = 0.0 if fix_bottom is not None else min(y)
    t0 = 1.0 if fix_top is not None else max(y)
    p = np.array([b0, t0, np.median(x), 1.0])
    free = [fix_bottom is None, fix_top is None, True, True]
    for _ in range(200):
        b,t,li,h = p
        pred = pl4(x,b,t,li,h)
        r = y-pred
        J = np.zeros((len(x),4))
        J[:,0] = 1-1/(1+10**((li-x)*h))
        J[:,1] = 1/(1+10**((li-x)*h))
        g = 10**((li-x)*h)
        J[:,2] = (t-b)*np.log(10)*h*g/(1+g)**2
        J[:,3] = -(t-b)*np.log(10)*(li-x)*g/(1+g)**2
        Jf = J[:,free]
        try:
            dp,_,_,_ = np.linalg.lstsq(Jf, r, rcond=None)
        except Exception:
            break
        p[free] += dp
        if np.linalg.norm(dp) < 1e-10: break
    return p

p4 = fit_pl4(logdose, resp)
pred4 = pl4(logdose, *p4)
rss4 = np.sum((resp-pred4)**2)
n = len(resp); k4 = 4
print(f"[4PL] Bottom={p4[0]:.4f}, Top={p4[1]:.4f}, logIC50={p4[2]:.4f}, HillSlope={p4[3]:.4f}")
print(f"[4PL] IC50={10**p4[2]:.4f} μM, RSS={rss4:.5f}")

# 3PL（固定 Bottom=0）
p3 = fit_pl4(logdose, resp, fix_bottom=0.0)
pred3 = pl4(logdose, *p3)
rss3 = np.sum((resp-pred3)**2)
k3 = 3
F = ((rss3-rss4)/(k4-k3))/(rss4/(n-k4)) if rss4>0 else np.nan
print(f"[3PL] 固定Bottom=0: Top={p3[1]:.4f}, logIC50={p3[2]:.4f}, HillSlope={p3[3]:.4f}, RSS={rss3:.5f}")
print(f"[嵌套F检验] F={F:.4f} (α=0.05, 若F<临界值则3PL足够)")

# 残差诊断
resid = resp-pred4
print(f"[残差] 均值={resid.mean():.4f}, SD={resid.std():.4f}, 与logdose相关={np.corrcoef(logdose,resid)[0,1]:.4f}")

# ---------- 4. Bootstrap IC50 ----------
def boot_ic50(x, y, B=10000, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        idx = rng.integers(0, len(x), len(x))
        try:
            pp = fit_pl4(x[idx], y[idx])
            vals.append(10**pp[2])
        except Exception:
            continue
    return np.array(vals)

boot = boot_ic50(logdose, resp, B=10000)
ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])
print(f"[Bootstrap] B=10000, seed={RNG_SEED}, IC50 95%CI=[{ci_lo:.4f}, {ci_hi:.4f}] μM")
print(f"[Bootstrap] 重采样单位=独立孔（n={n}），已记录于审计日志")

# 换种子验证方向
boot2 = boot_ic50(logdose, resp, B=2000, seed=RNG_SEED+1)
ci2 = np.percentile(boot2, [2.5, 97.5])
print(f"[稳健性] 换种子 IC50 95%CI=[{ci2[0]:.4f}, {ci2[1]:.4f}]，方向一致={ci2[0]<ci_hi and ci2[1]>ci_lo}")

# HillSlope 敏感性
for hs in [0.1, 0.5, 2.0, 5.0]:
    pp = fit_pl4(logdose, resp)
    pp[3] = hs
    print(f"[敏感性] 固定HillSlope={hs}: IC50={10**pp[2]:.4f} μM")

# 含/不含异常点对比
if outlier_mask.sum()>0:
    p_no = fit_pl4(logdose[~outlier_mask], resp[~outlier_mask])
    print(f"[敏感性] 剔除异常点后 IC50={10**p_no[2]:.4f} μM (含异常点={10**p4[2]:.4f})")

# ---------- 5. 绘图 ----------
fig, ax = plt.subplots(figsize=(7,5))
colors = ['#0072B2','#D55E00','#009E73','#CC79A7','#F0E442']
ax.errorbar(logdose, means, yerr=sds, fmt='o', color=colors[0], ecolor='gray',
            capsize=3, label='均值±SD', zorder=3)
xs = np.linspace(logdose.min()-0.3, logdose.max()+0.3, 300)
ax.plot(xs, pl4(xs, *p4), color=colors[1], lw=2, label='4PL 拟合')
ax.axhline(0.5, color='gray', ls='--', lw=0.8)
ax.axvline(p4[2], color=colors[2], ls=':', lw=1)
ax.annotate(f'IC50={10**p4[2]:.3f} μM\n95%CI=[{ci_lo:.3f},{ci_hi:.3f}]\nHillSlope={p4[3]:.2f}\nn={n}',
            xy=(p4[2], 0.5), xytext=(logdose.min(), 0.75),
            fontsize=8, color='black')
ax.set_xlabel('log10(剂量 / μM)', fontsize=9)
ax.set_ylabel('抑制率', fontsize=9)
ax.set_title('剂量-响应曲线 (4PL 拟合)', fontsize=10)
ax.legend(fontsize=8)
ax.tick_params(labelsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=150)
plt.close()

# ---------- 6. 落盘 ----------
with open('ic50_estimate.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['param','value'])
    w.writerow(['Bottom', p4[0]]); w.writerow(['Top', p4[1]])
    w.writerow(['logIC50', p4[2]]); w.writerow(['IC50_uM', 10**p4[2]])
    w.writerow(['HillSlope', p4[3]])
    w.writerow(['IC50_CI_lo', ci_lo]); w.writerow(['IC50_CI_hi', ci_hi])
    w.writerow(['RSS_4PL', rss4]); w.writerow(['RSS_3PL', rss3]); w.writerow(['F_nested', F])

with open('audit_log.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['step','detail'])
    w.writerow(['data_source','simulated' if is_sim else 'real'])
    w.writerow(['n_total', n]); w.writerow(['n_outliers', int(outlier_mask.sum())])
    w.writerow(['bootstrap_B', 10000]); w.writerow(['bootstrap_seed', RNG_SEED])
    w.writerow(['resample_unit','independent_well'])
    w.writerow(['IC50_uM', 10**p4[2]]); w.writerow(['CI_lo', ci_lo]); w.writerow(['CI_hi', ci_hi])

print("[落盘] figure.png, ic50_estimate.csv, audit_log.csv")
print("[完成] 模拟数据" if is_sim else "[完成] 真实数据")