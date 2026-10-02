import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

rng = np.random.default_rng(42)

# ============================================================
# 0. 构造模拟数据（模拟数据，非真实实验结论）
# ============================================================
raw = []
groups = ['A', 'B', 'C']
doses_uM = [0.0, 0.1, 1.0, 10.0, 100.0]
for g in groups:
    for d in doses_uM:
        for rep in range(1, 4):
            ic50 = 5.0 if g == 'A' else (10.0 if g == 'B' else 2.0)
            inh = 1.0 / (1.0 + (ic50 / (d + 1e-9)) ** 1.2)
            inh = float(np.clip(inh + rng.normal(0, 0.05), 0, 1))
            unit_choice = rng.choice(['nM', 'uM', 'ug/mL'], p=[0.3, 0.5, 0.2])
            if unit_choice == 'nM':
                dose_raw = d * 1000.0
            elif unit_choice == 'uM':
                dose_raw = d
            else:
                dose_raw = d * 0.18
            if rng.random() < 0.5:
                resp_raw = inh * 100.0
                metric = 'inhibition_pct'
            else:
                resp_raw = (1.0 - inh) * 100.0
                metric = 'viability_pct'
            raw.append({
                'dose_raw': round(dose_raw, 6),
                'dose_unit': unit_choice,
                'response_raw': round(resp_raw, 4),
                'response_metric': metric,
                'replicate': rep,
                'group': g,
            })

raw[3]['response_raw'] = None
raw[10]['dose_raw'] = None
raw[20]['response_raw'] = None
raw.append(dict(raw[5]))
raw.append({'dose_raw': -1.0, 'dose_unit': 'uM', 'response_raw': 50.0,
            'response_metric': 'inhibition_pct', 'replicate': 1, 'group': 'A'})
raw.append({'dose_raw': 10.0, 'dose_unit': 'uM', 'response_raw': 150.0,
            'response_metric': 'inhibition_pct', 'replicate': 2, 'group': 'B'})

print("=" * 60)
print("【模拟数据声明】以下全部为模拟数据，非真实实验结论")
print("=" * 60)
print(f"原始记录数: {len(raw)}")

# ============================================================
# 1. 主键唯一性 + 去重
# ============================================================
audit = []
def log(step, reason, n_before, n_after, note=""):
    audit.append({'step': step, 'reason': reason,
                  'rows_before': n_before, 'rows_after': n_after, 'note': note})
    print(f"[审计] {step} | 原因: {reason} | {n_before} -> {n_after} | {note}")

n0 = len(raw)
keys = [(r['dose_raw'], r['dose_unit'], r['replicate'], r['group']) for r in raw]
seen, dup_idx = set(), []
for i, k in enumerate(keys):
    if k in seen:
        dup_idx.append(i)
    else:
        seen.add(k)
print(f"\n[主键] 重复孔数量: {len(dup_idx)} (索引 {dup_idx})")

dup_set = set(dup_idx)
raw_dedup = [r for i, r in enumerate(raw) if i not in dup_set]
log("去重", "主键(dose×unit×replicate×group)重复，保留首次", n0, len(raw_dedup),
    f"移除{len(dup_idx)}行")

# ============================================================
# 2. 缺失模式标记（不删除，仅标记）
# ============================================================
for r in raw_dedup:
    miss = []
    if r['dose_raw'] is None:
        miss.append('dose_raw')
    if r['response_raw'] is None:
        miss.append('response_raw')
    r['missing_fields'] = ';'.join(miss) if miss else ''
    r['is_missing'] = bool(miss)

n_miss = sum(1 for r in raw_dedup if r['is_missing'])
print(f"\n[缺失] 含缺失行数: {n_miss} / {len(raw_dedup)}")
from collections import Counter
pat = Counter(r['missing_fields'] for r in raw_dedup if r['is_missing'])
for k, v in pat.items():
    print(f"  缺失模式 '{k}': {v} 行")
print("  规避陷阱：不删除缺失行，仅标记 is_missing，避免选择偏差")

# ============================================================
# 3. 单位统一为 uM，口径统一为抑制率 0-1
# ============================================================
def to_uM(dose, unit):
    if dose is None:
        return None
    if unit == 'nM':
        return dose / 1000.0
    if unit == 'uM':
        return dose
    if unit == 'ug/mL':
        return dose / 0.18
    return None

def to_inhibition(resp, metric):
    if resp is None:
        return None
    if metric == 'inhibition_pct':
        return resp / 100.0
    if metric == 'viability_pct':
        return 1.0 - resp / 100.0
    return None

for r in raw_dedup:
    r['dose_uM'] = to_uM(r['dose_raw'], r['dose_unit'])
    r['inhibition'] = to_inhibition(r['response_raw'], r['response_metric'])
    if r['dose_uM'] is not None and r['dose_uM'] > 0:
        r['log10_dose_uM'] = float(np.log10(r['dose_uM']))
    else:
        r['log10_dose_uM'] = None

print(f"\n[单位统一] 剂量统一为 uM，口径统一为抑制率(0-1)")
print(f"  转换后 dose_uM 非空: {sum(1 for r in raw_dedup if r['dose_uM'] is not None)}")
print(f"  转换后 inhibition 非空: {sum(1 for r in raw_dedup if r['inhibition'] is not None)}")

# ============================================================
# 4. 业务规则异常标记（不删除）
# ============================================================
for r in raw_dedup:
    flags = []
    if r['dose_uM'] is not None and r['dose_uM'] < 0:
        flags.append('negative_dose')
    if r['inhibition'] is not None and (r['inhibition'] < -0.05 or r['inhibition'] > 1.05):
        flags.append('out_of_range_inhibition')
    r['outlier_flag'] = ';'.join(flags) if flags else ''
    r['is_outlier'] = bool(flags)

n_out = sum(1 for r in raw_dedup if r['is_outlier'])
print(f"\n[异常] 业务规则标记异常行数: {n_out}")
for r in raw_dedup:
    if r['is_outlier']:
        print(f"  group={r['group']} rep={r['replicate']} dose_uM={r['dose_uM']} "
              f"inh={r['inhibition']} flags={r['outlier_flag']}")
print("  规避陷阱：异常点仅标记不删除，保留审计痕迹")

# ============================================================
# 5. 清洗后主键唯一性复核
# ============================================================
keys2 = [(r['dose_uM'], r['replicate'], r['group']) for r in raw_dedup]
print(f"\n[复核] 清洗后主键唯一性: {len(keys2) == len(set(keys2))} "
      f"(唯一键 {len(set(keys2))} / 总行 {len(keys2)})")

# ============================================================
# 6. 关键字段分布变化
# ============================================================
def dist(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return "无有效值"
    return f"n={len(v)} min={min(v):.4f} max={max(v):.4f} mean={np.mean(v):.4f}"

print(f"\n[分布] 清洗前 dose_raw: {dist([r['dose_raw'] for r in raw])}")
print(f"[分布] 清洗后 dose_uM: {dist([r['dose_uM'] for r in raw_dedup])}")
print(f"[分布] 清洗前 response_raw: {dist([r['response_raw'] for r in raw])}")
print(f"[分布] 清洗后 inhibition: {dist([r['inhibition'] for r in raw_dedup])}")

# ============================================================
# 7. 可视化（修复：x/y 成对收集，保证长度一致）
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

for g in groups:
    pts = [(r['log10_dose_uM'], r['inhibition']) for r in raw_dedup
           if r['group'] == g and r['log10_dose_uM'] is not None
           and r['inhibition'] is not None and not r['is_outlier']]
    if pts:
        xs, ys = zip(*pts)
        axes[0].scatter(xs, ys, label=f'组 {g}', alpha=0.7)

out_pts = [(r['log10_dose_uM'], r['inhibition']) for r in raw_dedup
           if r['is_outlier'] and r['log10_dose_uM'] is not None
           and r['inhibition'] is not None]
if out_pts:
    ox, oy = zip(*out_pts)
    axes[0].scatter(ox, oy, c='red', marker='x', s=100, label='异常(标记未删)')

axes[0].set_xlabel('log10(剂量 / μM)')
axes[0].set_ylabel('抑制率 (0-1)')
axes[0].set_title('剂量-抑制率（模拟数据）')
axes[0].legend()
axes[0].grid(alpha=0.3)

cats = ['总行', '缺失行', '异常行', '重复孔']
vals = [len(raw), n_miss, n_out, len(dup_idx)]
axes[1].bar(cats, vals, color=['steelblue', 'orange', 'red', 'gray'])
for i, v in enumerate(vals):
    axes[1].text(i, v + 0.2, str(v), ha='center')
axes[1].set_title('数据质量概览（模拟数据）')
axes[1].set_ylabel('行数')
axes[1].grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n[输出] 图已保存: figure.png")

# ============================================================
# 8. 落盘
# ============================================================
clean_fields = ['group', 'replicate', 'dose_raw', 'dose_unit', 'dose_uM',
                'log10_dose_uM', 'response_raw', 'response_metric',
                'inhibition', 'is_missing', 'missing_fields',
                'is_outlier', 'outlier_flag']
with open('clean_data.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=clean_fields)
    w.writeheader()
    for r in raw_dedup:
        w.writerow({k: ('' if r.get(k) is None else r.get(k, '')) for k in clean_fields})

with open('audit_log.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['step', 'reason', 'rows_before', 'rows_after', 'note'])
    w.writeheader()
    for a in audit:
        w.writerow(a)

with open('data_dictionary.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['字段', '口径/单位', '说明'])
    w.writerow(['group', '分类', '实验分组'])
    w.writerow(['replicate', '整数', '生物学重复编号'])
    w.writerow(['dose_raw', '原始单位', '原始剂量值'])
    w.writerow(['dose_unit', 'nM/uM/ug/mL', '原始剂量单位'])
    w.writerow(['dose_uM', 'μM', '统一后剂量'])
    w.writerow(['log10_dose_uM', 'log10(μM)', '对数剂量，dose=0时为缺失'])
    w.writerow(['response_raw', '百分比', '原始响应值'])
    w.writerow(['response_metric', 'inhibition_pct/viability_pct', '原始响应口径'])
    w.writerow(['inhibition', '0-1小数', '统一后抑制率'])
    w.writerow(['is_missing', 'bool', '是否含缺失字段'])
    w.writerow(['missing_fields', '文本', '缺失字段列表'])
    w.writerow(['is_outlier', 'bool', '业务规则异常标记'])
    w.writerow(['outlier_flag', '文本', '异常类型'])

print("[输出] clean_data.csv / audit_log.csv / data_dictionary.csv 已保存")
print(f"\n最终干净数据行数: {len(raw_dedup)}")
print("=" * 60)