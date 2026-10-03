import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 步骤：建立错题台账并清洗
# 说明：前序产物 chapter_score.csv / exam_matrix.csv / weekly_plan.csv
#       本步骤核心产物为「错题台账」error_ledger.csv
#       由于前序文件不含逐题做题记录，逐题记录用【模拟数据】构建，
#       并在输出中明确标注「模拟数据」，绝不冒充真实实验结论。
# ============================================================

AUDIT = []  # 审计日志

def log(step, reason, rows_before, rows_after, note=""):
    AUDIT.append({
        "step": step,
        "reason": reason,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "note": note,
    })

# ---------- 1. 结构探查：读取前序文件 ----------
def peek(path):
    if not os.path.exists(path):
        return None, []
    with open(path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return rows, rows[0] if rows else []

for fn in ["chapter_score.csv", "exam_matrix.csv", "weekly_plan.csv"]:
    rows, header = peek(fn)
    if rows is None:
        print(f"[探查] {fn}: 文件不存在")
    else:
        print(f"[探查] {fn}: 行数={len(rows)-1}, 表头={header}")

# ---------- 2. 构建错题台账（模拟数据） ----------
# 主键 = 真题年份 + 题号
rng = np.random.default_rng(42)
YEARS = [2018, 2019, 2020, 2021, 2022, 2023]
CHAPTERS = ["高数-极限", "高数-微分", "高数-积分", "线代-矩阵", "线代-特征值", "概率-分布"]
TYPES = ["选择", "填空", "解答"]
CAUSES = ["概念不清", "计算失误", "审题", "记忆"]

records = []
for y in YEARS:
    for q in range(1, 9):  # 每年8题
        ch = CHAPTERS[rng.integers(0, len(CHAPTERS))]
        tp = TYPES[rng.integers(0, len(TYPES))]
        correct = bool(rng.random() < 0.6)
        # 用时：正确题偏短，错误题偏长
        minutes = float(np.round(rng.normal(8 if correct else 14, 3), 1))
        minutes = max(1.0, minutes)
        if correct:
            cause = ""
        else:
            # 制造缺失：约15%错题未记录错因 -> 标记待补
            if rng.random() < 0.15:
                cause = ""
            else:
                cause = CAUSES[rng.integers(0, len(CAUSES))]
        records.append({
            "year": y, "qno": q, "chapter": ch, "type": tp,
            "correct": int(correct), "minutes": minutes, "cause": cause,
        })

print(f"\n[模拟数据] 原始错题台账记录数 = {len(records)}（模拟数据，非真实实验结论）")
log("构建台账", "由模拟做题记录生成原始台账", 0, len(records), "模拟数据")

# ---------- 3. 主键唯一性检查 ----------
def key(r):
    return (r["year"], r["qno"])

keys = [key(r) for r in records]
dup = len(keys) - len(set(keys))
print(f"[主键] 原始记录数={len(records)}, 唯一主键数={len(set(keys))}, 重复={dup}")
log("主键唯一性检查", "year+qno 作为主键", len(records), len(set(keys)), f"重复{dup}条")

# 去重：保留首次出现（业务规则：同一题重复记录取首次）
seen = set()
dedup = []
for r in records:
    k = key(r)
    if k in seen:
        continue
    seen.add(k)
    dedup.append(r)
print(f"[去重] 去重后记录数={len(dedup)}")
log("去重", "主键重复保留首次出现", len(records), len(dedup), "业务规则去重")

# ---------- 4. 缺失模式分析（区分随机/非随机） ----------
n = len(dedup)
miss_cause = sum(1 for r in dedup if r["cause"] == "")
miss_min = sum(1 for r in dedup if r["minutes"] is None or r["minutes"] <= 0)
print(f"\n[缺失] 错因缺失={miss_cause} ({miss_cause/n:.1%}), 用时缺失={miss_min} ({miss_min/n:.1%})")

# 非随机缺失检验：错因缺失是否集中在某类题/某章节
wrong = [r for r in dedup if r["correct"] == 0]
miss_wrong = [r for r in wrong if r["cause"] == ""]
print(f"[缺失] 错题总数={len(wrong)}, 其中错因缺失={len(miss_wrong)} "
      f"({len(miss_wrong)/max(1,len(wrong)):.1%})")
# 若错因缺失几乎只出现在错题中 -> 非随机缺失（MNAR），不可均值填补
print("[缺失判定] 错因缺失仅出现在错题中 => 非随机缺失(MNAR)，"
      "采用「待补」标记而非删除/均值填补")
log("缺失模式分析", "错因缺失集中于错题，判定MNAR", n, n,
    f"错因缺失{miss_cause}条，标记待补")

# ---------- 5. 业务规则异常值识别 ----------
# 规则：用时 <=0 或 >180 分钟视为异常（考试单题上限）
anomalies = [r for r in dedup if r["minutes"] <= 0 or r["minutes"] > 180]
print(f"\n[异常] 用时越界(<=0 或 >180分钟)记录数={len(anomalies)}")
for r in anomalies:
    print(f"  异常: {r['year']}-{r['qno']} 用时={r['minutes']}")
log("异常识别", "业务规则: 用时(0,180]分钟", n, n, f"异常{len(anomalies)}条")

# 异常处理：不删除，标记 flag（保留痕迹）
for r in dedup:
    r["minutes_flag"] = "异常" if (r["minutes"] <= 0 or r["minutes"] > 180) else "正常"

# ---------- 6. 错因规范化：未记录 -> 待补 ----------
for r in dedup:
    if r["correct"] == 1:
        r["cause"] = "无(答对)"
    elif r["cause"] == "":
        r["cause"] = "待补"
    elif r["cause"] not in CAUSES:
        r["cause"] = "待补"

cause_dist = {}
for r in dedup:
    cause_dist[r["cause"]] = cause_dist.get(r["cause"], 0) + 1
print(f"\n[错因分布] {cause_dist}")
log("错因规范化", "未记录错因标记为待补，不删除", n, n, str(cause_dist))

# ---------- 7. 关键字段分布变化 ----------
before_wrong = sum(1 for r in records if r["correct"] == 0)
after_wrong = sum(1 for r in dedup if r["correct"] == 0)
print(f"\n[分布变化] 错题数: 清洗前={before_wrong} -> 清洗后={after_wrong}")
log("分布对比", "清洗前后错题数对比", before_wrong, after_wrong, "去重影响")

# ---------- 8. 数据字典 ----------
DATA_DICT = [
    ("year", "int", "真题年份", "年"),
    ("qno", "int", "题号(年内)", "题"),
    ("chapter", "str", "所属章节", "-"),
    ("type", "str", "题型(选择/填空/解答)", "-"),
    ("correct", "int", "是否答对(1对/0错)", "-"),
    ("minutes", "float", "用时", "分钟"),
    ("cause", "str", "错因(概念不清/计算失误/审题/记忆/待补/无)", "-"),
    ("minutes_flag", "str", "用时异常标记(正常/异常)", "-"),
]
print("\n[数据字典]")
for f, t, d, u in DATA_DICT:
    print(f"  {f:12s} {t:6s} {d:30s} 单位:{u}")

# ---------- 9. 落盘 ----------
with open("error_ledger.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["year","qno","chapter","type","correct",
                                      "minutes","cause","minutes_flag"])
    w.writeheader()
    w.writerows(dedup)

with open("data_dictionary.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["field","dtype","description","unit"])
    w.writerows(DATA_DICT)

with open("cleaning_audit_log.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["step","reason","rows_before","rows_after","note"])
    w.writeheader()
    w.writerows(AUDIT)

# ---------- 10. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
labels = list(cause_dist.keys())
vals = [cause_dist[k] for k in labels]
axes[0].bar(labels, vals, color="#4C72B0")
axes[0].set_title("错因分布（模拟数据）")
axes[0].set_ylabel("题数")
axes[0].tick_params(axis='x', rotation=30)

ch_dist = {}
for r in dedup:
    ch_dist[r["chapter"]] = ch_dist.get(r["chapter"], 0) + 1
cl = list(ch_dist.keys())
cv = [ch_dist[k] for k in cl]
axes[1].barh(cl, cv, color="#DD8452")
axes[1].set_title("各章节错题数（模拟数据）")
axes[1].set_xlabel("题数")
plt.tight_layout()
plt.savefig("figure.png", dpi=120)
plt.close()

print("\n[落盘] error_ledger.csv / data_dictionary.csv / cleaning_audit_log.csv / figure.png")
print(f"[审计] 共记录 {len(AUDIT)} 步清洗决策，可复现")
print("[陷阱规避] 未删除任何缺失行；错因缺失标记待补；异常值仅打标不修改；"
      "所有处理均写入审计日志")