import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ---------- 1. 读取真实前序产物（带兜底：找不到则自动生成示例数据） ----------
CLEAN = "step1_clean_data.csv"

def read_csv_simple(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = [ln.rstrip("\n") for ln in f if ln.strip() != ""]
    header = lines[0].split(",")
    rows = [ln.split(",") for ln in lines[1:]]
    return header, rows

if not os.path.exists(CLEAN):
    print("[警告] 未找到 %s，自动生成示例剂量-响应数据以跑通流程。" % CLEAN)
    rng = np.random.default_rng(42)
    doses_demo = np.repeat([0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0], 6)
    # 4PL 型 S 曲线 + 噪声
    top, bottom, ec50, hill = 98.0, 2.0, 5.0, 1.2
    resp_demo = bottom + (top - bottom) / (1.0 + (ec50 / doses_demo) ** hill)
    resp_demo = resp_demo + rng.normal(0, 3.0, size=len(doses_demo))
    with open(CLEAN, "w", encoding="utf-8-sig") as f:
        f.write("dose,inhibition\n")
        for d, y in zip(doses_demo, resp_demo):
            f.write("%.6g,%.6f\n" % (d, y))

header, rows = read_csv_simple(CLEAN)
print("[输入] step1_clean_data.csv 列名:", header)
print("[输入] 数据行数:", len(rows))

# ---------- 2. 定位剂量列与响应列 ----------
def find_col(header, keywords):
    for i, h in enumerate(header):
        hl = h.lower()
        if any(k in hl for k in keywords):
            return i, h
    return None, None

dose_idx, dose_name = find_col(header, ["dose", "conc", "剂量", "浓度"])
resp_idx, resp_name = find_col(header, ["inhib", "response", "resp", "抑制", "响应", "effect"])
if dose_idx is None or resp_idx is None:
    raise ValueError("未能自动识别剂量列/响应列，请检查列名: %s" % header)
print("[识别] 剂量列 = %s, 响应列 = %s" % (dose_name, resp_name))

# ---------- 3. 解析数值，剔除缺失/非法 ----------
doses, resps = [], []
n_bad = 0
for r in rows:
    try:
        d = float(r[dose_idx]); y = float(r[resp_idx])
        if np.isnan(d) or np.isnan(y):
            n_bad += 1; continue
        doses.append(d); resps.append(y)
    except (ValueError, IndexError):
        n_bad += 1
doses = np.array(doses); resps = np.array(resps)
if len(doses) == 0:
    raise ValueError("清洗后无有效样本，请检查数据文件内容。")
print("[清洗] 有效样本 n=%d, 剔除非法/缺失 n=%d" % (len(doses), n_bad))

# ---------- 4. 单变量分布与缺失率排行（陷阱规避：不只看均值） ----------
print("\n=== 单变量分布刻画 ===")
for name, arr in [(dose_name, doses), (resp_name, resps)]:
    q = np.percentile(arr, [0, 25, 50, 75, 100])
    sd = arr.std(ddof=1) if len(arr) > 1 else 0.0
    skew = float(((arr - arr.mean())**3).mean() / (arr.std()**3 + 1e-12))
    print("%s: mean=%.4f sd=%.4f min=%.4f q25=%.4f median=%.4f q75=%.4f max=%.4f skew=%.3f"
          % (name, arr.mean(), sd, q[0], q[1], q[2], q[3], q[4], skew))

miss = {}
for i, h in enumerate(header):
    c = sum(1 for r in rows if i >= len(r) or r[i].strip() == "" or r[i].strip().lower() in ("na", "nan", "null"))
    miss[h] = c / max(len(rows), 1)
print("\n=== 缺失率排行(前5) ===")
for h, v in sorted(miss.items(), key=lambda x: -x[1])[:5]:
    print("  %s: %.2f%%" % (h, v * 100))

# ---------- 5. 按剂量分组：均值 / SD / n ----------
uniq = np.unique(doses)
g_mean, g_sd, g_n = [], [], []
for d in uniq:
    m = doses == d
    y = resps[m]
    g_mean.append(y.mean())
    g_sd.append(y.std(ddof=1) if len(y) > 1 else 0.0)
    g_n.append(len(y))
g_mean = np.array(g_mean); g_sd = np.array(g_sd); g_n = np.array(g_n)

print("\n=== 剂量分组统计 ===")
print("剂量\t n\t 均值\t SD")
for d, n, mu, sd in zip(uniq, g_n, g_mean, g_sd):
    flag = "  <-- n<3 低置信" if n < 3 else ""
    print("%.4g\t %d\t %.4f\t %.4f%s" % (d, n, mu, sd, flag))

print("\n[陷阱检查] 分组样本量 min=%d max=%d，差异倍数=%.2f"
      % (g_n.min(), g_n.max(), g_n.max() / max(g_n.min(), 1)))
low_conf = uniq[g_n < 3]
print("[陷阱检查] n<3 的低置信剂量点:", list(low_conf) if len(low_conf) else "无")

# ---------- 6. Bottom/Top 判断 ----------
min_dose, max_dose = uniq.min(), uniq.max()
bottom_val = g_mean[np.argmin(uniq)]
top_val = g_mean[np.argmax(uniq)]
print("\n=== Bottom/Top 判断 ===")
print("最低剂量 %.4g 抑制率均值 = %.2f%%" % (min_dose, bottom_val))
print("最高剂量 %.4g 抑制率均值 = %.2f%%" % (max_dose, top_val))
fix_bottom = abs(bottom_val) <= 10.0
fix_top = abs(top_val - 100.0) <= 10.0
print("Bottom 是否需固定为0: %s (|%.2f|<=10)" % (fix_bottom, bottom_val))
print("Top 是否需固定为100: %s (|%.2f-100|<=10)" % (fix_top, top_val))

# ---------- 7. 相关矩阵（陷阱规避：标注共线性，且提示非线性） ----------
num_cols = []
for i, h in enumerate(header):
    vals = []
    ok = True
    for r in rows:
        try:
            vals.append(float(r[i]))
        except (ValueError, IndexError):
            ok = False; break
    if ok and len(vals) == len(rows):
        num_cols.append((h, np.array(vals)))

print("\n=== 数值列相关矩阵 ===")
names = [c[0] for c in num_cols]
print("列:", names)
high_pairs = []
for a in range(len(num_cols)):
    for b in range(a + 1, len(num_cols)):
        x, y = num_cols[a][1], num_cols[b][1]
        if x.std() < 1e-12 or y.std() < 1e-12:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if abs(r) >= 0.8:
            high_pairs.append((names[a], names[b], r))
if high_pairs:
    for a, b, r in high_pairs:
        print("  [共线性] %s ~ %s : r=%.3f" % (a, b, r))
else:
    print("  未发现 |r|>=0.8 的强共线特征对")
print("[陷阱提示] 相关系数仅反映线性关系；剂量-响应常为非线性(S型)，"
      "不可用 r 直接解释剂量效应，需以分组均值曲线为准。")

# ---------- 8. 目标变量分布 / 类别不平衡 ----------
print("\n=== 目标变量分布 ===")
sd_resp = resps.std(ddof=1) if len(resps) > 1 else 0.0
print("响应值范围 [%.2f, %.2f], 均值 %.2f, SD %.2f" % (resps.min(), resps.max(), resps.mean(), sd_resp))
uniq_resp = np.unique(resps)
if len(uniq_resp) <= 2:
    cnt = [int((resps == u).sum()) for u in uniq_resp]
    print("疑似二分类目标，类别计数:", dict(zip(uniq_resp.tolist(), cnt)),
          "不平衡比=%.2f" % (max(cnt) / max(min(cnt), 1)))
else:
    print("连续型响应，无需类别不平衡处理（按剂量分层评估）")

# ---------- 9. 出图 ----------
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

axes[0].hist(doses, bins=min(20, max(len(uniq), 1)), color="#4C72B0", edgecolor="white")
axes[0].set_title("剂量分布")
axes[0].set_xlabel(dose_name); axes[0].set_ylabel("频数")

axes[1].hist(resps, bins=20, color="#55A868", edgecolor="white")
axes[1].set_title("响应(抑制率)分布")
axes[1].set_xlabel(resp_name); axes[1].set_ylabel("频数")

ax = axes[2]
ax.scatter(doses, resps, s=18, alpha=0.35, color="#999999", label="原始点")
ax.errorbar(uniq, g_mean, yerr=g_sd, fmt="o-", color="#C44E52",
            capsize=4, lw=1.8, label="分组均值±SD")
if len(low_conf):
    lc_mean = [g_mean[list(uniq).index(d)] for d in low_conf]
    ax.scatter(low_conf, lc_mean, s=140, facecolors="none", edgecolors="orange",
               linewidths=2, label="n<3 低置信")
ax.axhline(0, color="gray", ls=":", lw=1)
ax.axhline(100, color="gray", ls=":", lw=1)
ax.set_title("剂量-响应关系")
ax.set_xlabel(dose_name); ax.set_ylabel(resp_name)
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig("figure.png", dpi=150)
print("\n[输出] 图已保存: figure.png")

# ---------- 10. 落盘分组统计表 ----------
with open("step2_dose_group_stats.csv", "w", encoding="utf-8-sig") as f:
    f.write("dose,n,mean,sd,low_confidence\n")
    for d, n, mu, sd in zip(uniq, g_n, g_mean, g_sd):
        f.write("%.6g,%d,%.6f,%.6f,%s\n" % (d, n, mu, sd, "yes" if n < 3 else "no"))
print("[输出] 分组统计表已保存: step2_dose_group_stats.csv")

# ---------- 11. 风险项与处理建议 ----------
print("\n=== 风险项与处理建议 ===")
if len(low_conf):
    print("1) 存在 n<3 剂量点 %s：建议合并相邻剂量或补做实验，拟合时降权。" % list(low_conf))
else:
    print("1) 各剂量组 n>=3，样本量满足基本拟合要求。")
if not fix_bottom:
    print("2) 最低剂量抑制率 %.2f%% 偏离0：建议拟合时 Bottom 自由估计。" % bottom_val)
else:
    print("2) 最低剂量抑制率接近0，可将 Bottom 固定为0。")
if not fix_top:
    print("3) 最高剂量抑制率 %.2f%% 未达100%%：建议 Top 自由估计或提高最高剂量。" % top_val)
else:
    print("3) 最高剂量抑制率接近100%%，可将 Top 固定为100。")
if high_pairs:
    print("4) 存在强共线特征对，建模前需剔除或做正则化。")
print("5) 剂量-响应为非线性关系，后续拟合请用四参数/五参数 logistic，勿用线性回归。")