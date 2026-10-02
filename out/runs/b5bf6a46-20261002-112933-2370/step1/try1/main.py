import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import csv

# ============================================================
# 注意：以下为【模拟数据】，仅用于演示清洗流程，非真实实验结论
# ============================================================
rng = np.random.default_rng(42)

def make_raw():
    rows = []
    groups = ['A', 'B']
    doses_uM = [0.0, 0.1, 1.0, 10.0, 100.0]
    rid = 0
    for g in groups:
        for d in doses_uM:
            for rep in range(1, 4):
                rid += 1
                # 真实抑制率（模拟）
                true_r = 1.0 / (1.0 + np.exp(-(np.log10(d + 1e-9) + 1.0)))
                resp = float(np.clip(true_r + rng.normal(0, 0.03), 0, 1))
                rows.append({'id': rid, 'dose': d, 'dose_unit': 'uM',
                             'response': resp, 'replicate': rep, 'group': g})
    # 注入问题数据
    rows[3]['response'] = None                      # 缺失
    rows[7]['response'] = 1.35                      # 越界异常
    rows[10]['dose_unit'] = 'nM'                    # 单位不一致
    rows[10]['dose'] = 1000.0                       # 1000 nM = 1 uM
    rows[12]['response'] = -0.2                     # 负值异常
    rows.append(dict(rows[5]))                      # 重复主键
    rows[-1]['id'] = rows[5]['id']
    return rows

raw = make_raw()
print("=== 步骤1: 结构与类型探查 ===")
print(f"原始行数: {len(raw)}")
ids = [r['id'] for r in raw]
dup_ids = sorted({i for i in ids if ids.count(i) > 1})
print(f"主键重复 id: {dup_ids}  (重复行数={len(ids)-len(set(ids))})")

# 去重：保留首次出现，记录审计
audit = []
seen = set()
clean = []
for r in raw:
    if r['id'] in seen:
        audit.append(('drop_duplicate_pk', r['id'], '主键重复，保留首条'))
        continue
    seen.add(r['id'])
    clean.append(dict(r))
print(f"去重后行数: {len(clean)}")

# ============================================================
# 步骤2: 单位统一 -> μM
# ============================================================
print("\n=== 步骤2: 剂量单位统一为 μM ===")
unit_fix = 0
for r in clean:
    if r['dose_unit'] == 'nM':
        r['dose'] = r['dose'] / 1000.0
        r['dose_unit'] = 'uM'
        unit_fix += 1
        audit.append(('unit_convert_nM_to_uM', r['id'], 'nM->uM 除以1000'))
print(f"单位转换行数: {unit_fix}")
print(f"剂量范围(μM): {min(r['dose'] for r in clean):.4f} ~ {max(r['dose'] for r in clean):.4f}")

# ============================================================
# 步骤3: 缺失模式标记（不删除、不均值填补）
# ============================================================
print("\n=== 步骤3: 缺失模式标记 ===")
miss = [r for r in clean if r['response'] is None]
print(f"缺失 response 行数: {len(miss)}")
for r in miss:
    r['flag'] = 'missing_response'
    audit.append(('flag_missing', r['id'], 'response缺失，标记不删除'))
# 判断是否随机缺失：按 group/dose 分布
if miss:
    print("缺失行分布(按group):", {g: sum(1 for r in miss if r['group']==g) for g in set(r['group'] for r in clean)})
    print("缺失行分布(按dose):", {d: sum(1 for r in miss if r['dose']==d) for d in sorted(set(r['dose'] for r in clean))})
    print("结论: 缺失集中在单一剂量/组 -> 疑似非随机缺失(MNAR)，保留并标记，禁止均值填补")

# ============================================================
# 步骤4: 业务规则异常识别（标记不删除）
# ============================================================
print("\n=== 步骤4: 业务规则异常标记 ===")
outlier_n = 0
for r in clean:
    if r['response'] is None:
        continue
    if r['response'] < 0 or r['response'] > 1:
        r['flag'] = 'out_of_range_response'
        outlier_n += 1
        audit.append(('flag_outlier', r['id'], f"response={r['response']} 超出[0,1]"))
print(f"越界异常行数: {outlier_n} (业务规则: 抑制率必须∈[0,1])")

# ============================================================
# 步骤5: 输出干净表 + 审计日志
# ============================================================
print("\n=== 步骤5: 产出 ===")
valid = [r for r in clean if r['response'] is not None and 0 <= r['response'] <= 1]
print(f"最终有效行数: {len(valid)} / 原始 {len(raw)}")
print(f"审计日志条数: {len(audit)}")
resp_vals = [r['response'] for r in valid]
print(f"response 分布: mean={np.mean(resp_vals):.4f}, std={np.std(resp_vals):.4f}, "
      f"min={np.min(resp_vals):.4f}, max={np.max(resp_vals):.4f}")

# 数据字典
print("\n=== 数据字典 ===")
print("dose      : 剂量, 单位 μM (float)")
print("response  : 抑制率, 0-1 小数 (float, 缺失为None)")
print("replicate : 复孔编号 (int)")
print("group     : 实验组 (str)")
print("flag      : 清洗标记 (missing_response/out_of_range_response/空)")

# ============================================================
# 出图
# ============================================================
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for g in sorted(set(r['group'] for r in valid)):
    sub = [r for r in valid if r['group'] == g]
    xs = [r['dose'] for r in sub]
    ys = [r['response'] for r in sub]
    axes[0].scatter(xs, ys, label=f'组{g}', alpha=0.7)
axes[0].set_xscale('symlog', linthresh=0.1)
axes[0].set_xlabel('剂量 (μM)')
axes[0].set_ylabel('抑制率')
axes[0].set_title('剂量-响应散点 (模拟数据)')
axes[0].legend()
axes[0].grid(alpha=0.3)

axes[1].hist(resp_vals, bins=15, color='steelblue', edgecolor='k', alpha=0.8)
axes[1].set_xlabel('抑制率')
axes[1].set_ylabel('频数')
axes[1].set_title('抑制率分布 (清洗后, 模拟数据)')
axes[1].grid(alpha=0.3)
plt.tight_layout()
plt.savefig('figure.png', dpi=120)
print("\n图已保存: figure.png")

# ============================================================
# 落盘
# ============================================================
with open('clean_data.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['dose', 'response', 'replicate', 'group', 'flag'])
    for r in clean:
        w.writerow([r['dose'], r['response'] if r['response'] is not None else '',
                    r['replicate'], r['group'], r.get('flag', '')])

with open('audit_log.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['action', 'id', 'reason'])
    for a in audit:
        w.writerow(a)

print("已保存: clean_data.csv, audit_log.csv")