import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

LEDGER = "error_ledger.csv"
CLEAN = "error_ledger_clean.csv"
DICT_OUT = "data_dictionary.csv"
AUDIT = "cleaning_audit_log.csv"
FIG = "figure.png"

VALID_CAUSES = {"概念不清", "计算失误", "审题", "记忆"}
PENDING = "待补"

# ---------- 1. 读取原始台账 ----------
def read_csv(path):
    if not os.path.exists(path):
        return None, None
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        rows = list(r)
    if not rows:
        return [], []
    return rows[0], rows[1:]

header, rows = read_csv(LEDGER)
if header is None:
    print("[警告] 未找到 error_ledger.csv，使用【模拟数据】演示清洗流程。")
    header = ["题号", "章节", "知识点", "题型", "对错", "用时", "错因"]
    rows = [
        ["T001", "极限", "等价无穷小", "选择", "错", "3", "概念不清"],
        ["T002", "极限", "洛必达", "计算", "错", "5", "计算失误"],
        ["T003", "导数", "复合求导", "计算", "对", "2", ""],
        ["T004", "导数", "隐函数", "计算", "错", "6", "审题"],
        ["T005", "积分", "分部积分", "计算", "错", "4", "记忆"],
        ["T006", "积分", "换元", "选择", "错", "3", "概念不清"],
        ["T007", "级数", "收敛判别", "选择", "错", "7", "计算失误"],
        ["T008", "级数", "幂级数", "计算", "对", "5", ""],
        ["T009", "极限", "夹逼", "选择", "错", "4", "审题"],
        ["T010", "导数", "高阶导", "计算", "错", "8", "概念不清"],
        ["T011", "积分", "定积分应用", "计算", "错", "5", "计算失误"],
        ["T012", "级数", "傅里叶", "选择", "错", "6", "记忆"],
        ["T013", "极限", "无穷小比较", "选择", "错", "3", "概念不清"],
        ["T014", "导数", "参数方程", "计算", "错", "4", "审题"],
        ["T015", "积分", "反常积分", "计算", "错", "9", "计算失误"],
        ["T016", "级数", "交错级数", "选择", "错", "5", "记忆"],
        ["T017", "极限", "数列极限", "计算", "错", "6", "概念不清"],
        ["T018", "导数", "中值定理", "证明", "错", "10", "审题"],
        ["T019", "积分", "二重积分", "计算", "错", "7", "计算失误"],
        ["T020", "级数", "幂级数展开", "计算", "错", "8", "记忆"],
        ["T021", "极限", "等价无穷小", "选择", "错", "3", "概念不清"],
        ["T022", "导数", "复合求导", "计算", "错", "4", "计算失误"],
        ["T023", "积分", "分部积分", "计算", "错", "5", "审题"],
        ["T024", "级数", "收敛判别", "选择", "错", "6", "记忆"],
        ["T025", "极限", "洛必达", "计算", "错", "4", "概念不清"],
        ["T026", "导数", "隐函数", "计算", "错", "5", "计算失误"],
        ["T027", "积分", "换元", "选择", "错", "3", "审题"],
        ["T028", "级数", "幂级数", "计算", "错", "7", "记忆"],
        ["T029", "极限", "夹逼", "选择", "错", "4", "概念不清"],
        ["T030", "导数", "高阶导", "计算", "错", "6", "计算失误"],
    ]

# ---------- 2. 结构与类型探查 ----------
print("=" * 60)
print("步骤1：结构与类型探查")
print("字段列表:", header)
print("原始记录数:", len(rows))

idx = {name: i for i, name in enumerate(header)}
def col(row, name):
    return row[idx[name]].strip() if name in idx and idx[name] < len(row) else ""

# 主键唯一性检查
ids = [col(r, "题号") for r in rows]
dup_ids = set([x for x in ids if ids.count(x) > 1])
print("题号唯一性: 重复题号数 =", len(dup_ids), "->", sorted(dup_ids) if dup_ids else "无重复")

# 类型探查
def is_num(s):
    try:
        float(s); return True
    except Exception:
        return False
time_vals = [col(r, "用时") for r in rows]
non_num_time = [t for t in time_vals if t != "" and not is_num(t)]
print("用时字段非数值条数:", len(non_num_time), "->", non_num_time[:5])

# ---------- 3. 缺失模式标记 ----------
print("=" * 60)
print("步骤2：缺失模式标记")
missing_cause = [r for r in rows if col(r, "错因") == ""]
wrong_rows = [r for r in rows if col(r, "对错") == "错"]
print("错因缺失总条数:", len(missing_cause))
print("其中属于做错的题:", len([r for r in missing_cause if col(r, "对错") == "错"]))
print("做对的题(错因天然为空):", len([r for r in rows if col(r, "对错") == "对"]))
print("判定: 做对题错因缺失为结构性缺失(非随机); 做错题错因缺失为待补(非随机缺失, 不删除)")

# ---------- 4. 业务规则异常识别 ----------
print("=" * 60)
print("步骤3：业务规则异常识别")
anomalies = []
for r in rows:
    t = col(r, "用时")
    if t != "" and is_num(t):
        v = float(t)
        if v <= 0:
            anomalies.append((col(r, "题号"), "用时<=0", t))
        elif v > 60:
            anomalies.append((col(r, "题号"), "用时>60分钟(疑似异常)", t))
    if col(r, "对错") not in ("对", "错"):
        anomalies.append((col(r, "题号"), "对错取值非法", col(r, "对错")))
    c = col(r, "错因")
    if c != "" and c not in VALID_CAUSES:
        anomalies.append((col(r, "题号"), "错因不在4类内", c))
print("业务规则异常条数:", len(anomalies))
for a in anomalies[:10]:
    print("  ", a)

# ---------- 5. 清洗（保留缺失，不删除；不均值填补） ----------
print("=" * 60)
print("步骤4：清洗执行与审计")
audit = []
clean = []
seen = set()
for r in rows:
    rid = col(r, "题号")
    if rid in seen:
        audit.append([rid, "去重", "重复主键，保留首条", 1])
        continue
    seen.add(rid)
    cause = col(r, "错因")
    if col(r, "对错") == "错" and cause == "":
        cause = PENDING
        audit.append([rid, "错因缺失标记", "做错但未记错因->待补(不删除)", 1])
    elif cause != "" and cause not in VALID_CAUSES:
        audit.append([rid, "错因非法值", "保留原值并标记待补", 1])
        cause = PENDING
    clean.append([rid, col(r, "章节"), col(r, "知识点"), col(r, "题型"),
                  col(r, "对错"), col(r, "用时"), cause])

print("清洗后记录数:", len(clean), "(原始", len(rows), ")")
print("删除行数:", len(rows) - len(clean), "-> 仅去重，未因缺失删除任何行")

# 关键字段分布变化
def dist(data, name):
    d = {}
    for r in data:
        k = col(r, name)
        d[k] = d.get(k, 0) + 1
    return d
print("错因分布(清洗前):", dist(rows, "错因"))
print("错因分布(清洗后):", dist(clean, "错因"))
print("待补条数:", sum(1 for r in clean if r[6] == PENDING))

# 主键唯一性复核
clean_ids = [r[0] for r in clean]
print("清洗后主键唯一:", len(clean_ids) == len(set(clean_ids)))

# ---------- 6. 数据字典 ----------
data_dict = [
    ["题号", "字符串", "题目唯一标识", "无", "主键，唯一"],
    ["章节", "字符串", "所属章节(极限/导数/积分/级数)", "无", "分类字段"],
    ["知识点", "字符串", "具体考点", "无", "分类字段"],
    ["题型", "字符串", "选择/计算/证明", "无", "分类字段"],
    ["对错", "字符串", "对/错", "无", "结果字段"],
    ["用时", "数值", "本题作答用时", "分钟", ">0且<=60为合理"],
    ["错因", "字符串", "概念不清/计算失误/审题/记忆/待补", "无", "做对题为空; 做错未记为待补"],
]

# ---------- 7. 出图 ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
causes = ["概念不清", "计算失误", "审题", "记忆", PENDING]
counts = [sum(1 for r in clean if r[6] == c) for c in causes]
axes[0].bar(causes, counts, color=["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"])
axes[0].set_title("清洗后错因分布")
axes[0].set_ylabel("题数")
for i, v in enumerate(counts):
    axes[0].text(i, v + 0.1, str(v), ha="center")

chapters = sorted(set(r[1] for r in clean))
ch_counts = [sum(1 for r in clean if r[1] == ch) for ch in chapters]
axes[1].bar(chapters, ch_counts, color="#4C72B0")
axes[1].set_title("各章节错题数")
axes[1].set_ylabel("题数")
for i, v in enumerate(ch_counts):
    axes[1].text(i, v + 0.1, str(v), ha="center")
plt.tight_layout()
plt.savefig(FIG, dpi=120)
plt.close()

# ---------- 8. 落盘 ----------
with open(CLEAN, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(clean)

with open(DICT_OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["字段", "类型", "口径说明", "单位", "备注"])
    w.writerows(data_dict)

with open(AUDIT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["题号", "操作", "原因", "影响行数"])
    w.writerows(audit)

print("=" * 60)
print("落盘文件:", CLEAN, DICT_OUT, AUDIT, FIG)
print("审计日志条数:", len(audit))
print("数据字典字段数:", len(data_dict))