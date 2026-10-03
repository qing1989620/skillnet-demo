import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

rng = np.random.default_rng(42)

# ============ 1. 构造模拟数据（明确标注：模拟数据，非真实实验结论） ============
# 列: exp_id(实验), well(孔), dose_uM(剂量), viability_raw(存活率 0-100 或 0-1 混合)
N = 240
exp_ids = [f"E{i:02d}" for i in range(1, 9)]
doses = [0.0, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
rows = []
for e in exp_ids:
    for d in doses:
        for rep in range(3):
            # 真实剂量-响应：抑制率随剂量上升
            true_inh = 1.0 / (1.0 + np.exp(-(np.log10(d + 1e-9) - 0.5) * 1.8))
            noise = rng.normal(0, 0.06)
            inh = np.clip(true_inh + noise, 0, 1)
            # 混合单位：一半记录为百分数
            if rng.random() < 0.5:
                val = round(inh * 100, 2)
                unit = "percent"
            else:
                val = round(inh, 4)
                unit = "fraction"
            rows.append([e, f"{e}-{d}-{rep}", d, val, unit])

# 注入问题：缺失、重复孔、异常点
rows[5][3] = ""            # 缺失
rows[17][3] = ""           # 缺失
rows.append(list(rows[3])) # 重复孔（完全重复）
rows[40][3] = 999.0        # 超出载体对照的异常
rows[41][3] = -5.0         # 负值异常

raw = rows
print("=== 模拟数据（非真实实验结论） ===")
print(f"原始行数: {len(raw)}")

# ============ 2. 结构与类型探查 ============
header = ["exp_id", "well", "dose_uM", "viability_raw", "unit"]
data = [dict(zip(header, r)) for r in raw]

# 主键唯一性检查（exp_id + well）
keys = [(d["exp_id"], d["well"]) for d in data]
dup_keys = len(keys) - len(set(keys))
print(f"主键(exp_id+well)重复数: {dup_keys}")

# 重复孔检测：完全相同的记录
seen = set()
dup_rows = 0
for d in data:
    sig = tuple(str(d[k]) for k in header)
    if sig in seen:
        dup_rows += 1
    seen.add(sig)
print(f"完全重复记录数: {dup_rows}")

# ============ 3. 统一单位：剂量 μM，抑制率 0-1 小数 ============
def to_fraction(v, unit):
    if v == "" or v is None:
        return None
    v = float(v)
    if unit == "percent":
        return v / 100.0
    return v

for d in data:
    d["inh"] = to_fraction(d["viability_raw"], d["unit"])
    d["dose_uM"] = float(d["dose_uM"])
    d["log10_dose"] = np.log10(d["dose_uM"]) if d["dose_uM"] > 0 else np.nan

# ============ 4. 缺失模式 ============
miss = [d for d in data if d["inh"] is None]
print(f"缺失抑制率行数: {len(miss)}")
miss_by_dose = {}
for d in miss:
    miss_by_dose[d["dose_uM"]] = miss_by_dose.get(d["dose_uM"], 0) + 1
print(f"缺失按剂量分布: {miss_by_dose}")
# 判断随机/非随机：若缺失集中在特定剂量则提示非随机
if len(miss_by_dose) == 1 and len(miss) > 1:
    print("缺失模式: 疑似非随机缺失(MNAR)，不填补，仅标记")
else:
    print("缺失模式: 分散，倾向随机缺失(MAR)，仍不填补，仅标记")

# ============ 5. 业务规则异常标记（不删除） ============
# 规则A: 超出载体对照(dose=0)均值 ±3SD
ctrl = [d["inh"] for d in data if d["dose_uM"] == 0 and d["inh"] is not None]
ctrl_mean = float(np.mean(ctrl))
ctrl_sd = float(np.std(ctrl, ddof=1))
lo, hi = ctrl_mean - 3 * ctrl_sd, ctrl_mean + 3 * ctrl_sd
print(f"载体对照: mean={ctrl_mean:.4f}, sd={ctrl_sd:.4f}, 3SD区间=[{lo:.4f},{hi:.4f}]")

# 规则B: 违背剂量-响应单调性（同实验内，抑制率随剂量下降）
for d in data:
    d["flag"] = ""
    if d["inh"] is None:
        d["flag"] = "missing"
        continue
    if d["inh"] < lo or d["inh"] > hi:
        d["flag"] = "out_of_ctrl_3SD"
    if d["inh"] < 0 or d["inh"] > 1:
        d["flag"] = (d["flag"] + ";out_of_range").strip(";")

# 单调性检查：按实验分组，剂量升序，若抑制率显著下降则标记
for e in exp_ids:
    sub = sorted([d for d in data if d["exp_id"] == e and d["inh"] is not None],
                 key=lambda x: x["dose_uM"])
    for i in range(1, len(sub)):
        if sub[i]["inh"] < sub[i-1]["inh"] - 0.15:  # 明显下降
            sub[i]["flag"] = (sub[i]["flag"] + ";non_monotonic").strip(";")

n_flag = sum(1 for d in data if d["flag"])
print(f"被标记异常/缺失行数: {n_flag} (未删除，仅标记)")

# ============ 6. 审计日志 ============
audit = []
audit.append(["step", "action", "rows_affected", "reason"])
audit.append(["1", "读取原始表", len(raw), "原始数据"])
audit.append(["2", "主键重复检测", dup_keys, "exp_id+well 唯一性"])
audit.append(["3", "完全重复记录检测", dup_rows, "重复孔"])
audit.append(["4", "单位统一为0-1小数", len(data), "percent->fraction"])
audit.append(["5", "缺失标记(不填补)", len(miss), "避免选择偏差/均值填补"])
audit.append(["6", "3SD异常标记", sum(1 for d in data if "out_of_ctrl_3SD" in d["flag"]), "业务规则"])
audit.append(["7", "单调性异常标记", sum(1 for d in data if "non_monotonic" in d["flag"]), "业务规则"])

# 分布变化（清洗前后抑制率分布）
vals_before = [to_fraction(d["viability_raw"], d["unit"]) for d in data if d["viability_raw"] != ""]
vals_before = [v for v in vals_before if v is not None]
vals_after = [d["inh"] for d in data if d["inh"] is not None and d["flag"] == ""]
print(f"抑制率分布(清洗前): n={len(vals_before)}, mean={np.mean(vals_before):.4f}, sd={np.std(vals_before):.4f}")
print(f"抑制率分布(清洗后): n={len(vals_after)}, mean={np.mean(vals_after):.4f}, sd={np.std(vals_after):.4f}")

# ============ 7. 数据字典 ============
dictionary = [
    ["字段", "口径", "单位"],
    ["exp_id", "实验编号", "-"],
    ["well", "孔位标识", "-"],
    ["dose_uM", "化合物剂量", "μM"],
    ["log10_dose", "剂量对数", "log10(μM)"],
    ["inh", "抑制率(0-1小数)", "fraction"],
    ["flag", "异常/缺失标记", "-"],
]

# ============ 8. 出图 ============
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
# 左：剂量-响应散点（清洗后）
for e in exp_ids:
    sub = [d for d in data if d["exp_id"] == e and d["inh"] is not None and d["flag"] == ""]
    if sub:
        xs = [d["dose_uM"] for d in sub]
        ys = [d["inh"] for d in sub]
        axes[0].scatter(xs, ys, s=12, alpha=0.5)
axes[0].set_xscale("symlog", linthresh=0.1)
axes[0].set_xlabel("剂量 (μM)")
axes[0].set_ylabel("抑制率 (0-1)")
axes[0].set_title("剂量-响应（清洗后，模拟数据）")
axes[0].grid(alpha=0.3)

# 右：异常标记分布
flags = {}
for d in data:
    f = d["flag"] if d["flag"] else "clean"
    flags[f] = flags.get(f, 0) + 1
labels = list(flags.keys())
counts = [flags[k] for k in labels]
axes[1].bar(range(len(labels)), counts, color="steelblue")
axes[1].set_xticks(range(len(labels)))
axes[1].set_xticklabels(labels, rotation=30, ha="right")
axes[1].set_ylabel("行数")
axes[1].set_title("异常/缺失标记分布（模拟数据）")
plt.tight_layout()
plt.savefig("figure.png", dpi=120)
plt.close()

# ============ 9. 落盘 ============
with open("clean_data.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["exp_id", "well", "dose_uM", "log10_dose", "inh", "flag"])
    for d in data:
        w.writerow([d["exp_id"], d["well"], d["dose_uM"],
                    "" if np.isnan(d["log10_dose"]) else round(d["log10_dose"], 4),
                    "" if d["inh"] is None else round(d["inh"], 4), d["flag"]])

with open("audit_log.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerows(audit)

with open("data_dictionary.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerows(dictionary)

print("已输出: clean_data.csv, audit_log.csv, data_dictionary.csv, figure.png")
print("注：以上均为模拟数据，非真实实验结论。")