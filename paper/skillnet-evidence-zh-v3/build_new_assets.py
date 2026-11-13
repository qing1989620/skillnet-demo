"""Render new tables and scientific plots from frozen executed records only."""

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.font_manager import FontProperties, fontManager

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
N = ROOT / "research/skill_network/results"
D = ROOT / "research/skill_decision/results"
OUT = HERE / "results"
FIG = HERE / "figures"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(name, text):
    (OUT / name).write_text(text, encoding="utf-8")


def table(name, caption, label, cols, headings, rows, wide=False, note=""):
    env = "table*" if wide else "table"
    width = r"\textwidth" if wide else r"\columnwidth"
    text = f"\\begin{{{env}}}[t]\n\\caption{{{caption}}}\\label{{{label}}}\n\\centering\\small\n"
    text += f"\\begin{{tabularx}}{{{width}}}{{{cols}}}\n\\toprule\n"
    text += " & ".join(headings) + r" \\" + "\n\\midrule\n"
    text += "\n".join(" & ".join(str(v) for v in row) + r" \\" for row in rows)
    text += "\n\\bottomrule\n\\end{tabularx}\n"
    if note:
        text += "\\par\\vspace{3pt}\\raggedright\\footnotesize " + note + "\n"
    text += f"\\end{{{env}}}\n"
    write(name, text)


names = {
    "lexical_top5": "词法前五＋路径",
    "mmr_top5": "MMR 前五＋路径",
    "dpp_top5": "DPP 前五＋路径",
    "metadata_shortest_path": "原生元数据最短路径",
    "fixed_workflow": "人工固定流程",
    "global_filter_path": "全局证据过滤＋最短路径",
    "global_risk_path": "全局证据风险路径",
    "conditional_evidence_path": "ECP 完整方法",
    "conditional_top5": "条件证据前五＋路径",
    "evidence_without_version": "ECP 去版本绑定",
}
a = load(N / "analysis-v1/analysis.json")
j = load(N / "joint-posthoc-v1/summary.json")
s = load(D / "diagnostic-v3/summary.json")
groups = {(r["cohort"], r["policy"], r["multiplier"]): r for r in a["groups"]}
primary = {r["policy"]: r for r in a["primary_averages"]}
gate_keys = ["document_heuristic", "option_names_only", "native_argparse_only", "without_cli", "without_integrity", "full_gate"]
gate_names = ["文档均分阈值适配", "仅参数名", "标准库 argparse", "去接口检查", "去完整性检查", "完整判别器"]
table("gate_table.tex", "质量判别器的构造留出诊断。20个新父配置共200例；故障140、无害40、范围未知20。", "tab:gate", "Xrrr",
      ["方法", "检出/140", "误报/40", "弃权"],
      [(name, s["metrics"]["test"][key]["defects_detected"], s["metrics"]["test"][key]["false_alarms"], s["metrics"]["test"][key]["abstentions"]) for name, key in zip(gate_names, gate_keys)],
      note="阈值为本研究适配，不是发表版SkillNet的复现。完整判别器的60次弃权含40个缺行为证据的无害例；静态一致不自动获得可用认证。")
table("network_main_table.tex", "18节点可执行网络的全部主留出结果。每档均为128个输入，弃权按未完成计；三档均值以同一128任务为单位。", "tab:network-main", "Xrrrr", ["策略", "1.0倍", "1.5倍", "2.0倍", "三档均值(\\%)"],
      [(names[p], *[groups[("main", p, m)]["successes"] for m in [1.0,1.5,2.0]], f"{primary[p]['success_rate']*100:.2f}") for p in names], wide=True,
      note="预算锚为只用元数据求得的最低可行路径字节数，非根据测试成功选取。上下文字节不是LLM token或费用。人工流程与全局风险路径在两档宽预算上均与完整方法持平。")
table("network_effect_table.tex", "ECP相对各对照的三档平均成功差（百分点）。32个构造条件块的10,000次条件重采样；不作总体或多重检验显著性主张。", "tab:network-effects", "Xrr", ["对照", "平均差", "95\\%条件区间"],
      [(names[r["base"]], f"{100*r['mean_difference']:.2f}", f"[{100*r['conditional_interval_95'][0]:.2f}, {100*r['conditional_interval_95'][1]:.2f}]") for r in a["paired_effects"]], wide=False)
table("network_stress_table.tex", "固定压力实验及事后组合反例。各列均为中预算成功数。", "tab:network-stress", "Xrrrr", ["策略", "精度/24", "换版本/128", "缺能力/16", "组合/24"],
      [(names[p], groups[("precision",p,1.5)]["successes"], groups[("version_drift",p,1.5)]["successes"], groups[("missing_capability",p,1.5)]["successes"], j["methods"][p]) for p in names], wide=True,
      note="精度、换版本、缺能力在执行前固定；最右列为观察主结果后的证伪检查，复用同24个精度输入，不增加独立样本。组合条件中ECP只通过12/24，未据此调参。缺能力时全部方法弃权。")
table("network_cost_table.tex", "中预算资源与求解开销。包含失败尝试；前期取证为证据方法各自计入928次，非跨方法重复收费。", "tab:network-cost", "Xrrrr", ["策略", "成功/128", "调用总数", "上下文字节均值", "含取证调用/成功"],
      [(names[p], groups[("main",p,1.5)]["successes"], groups[("main",p,1.5)]["operator_calls"], f"{groups[('main',p,1.5)]['mean_context_bytes_per_started_plan']:.1f}", f"{groups[('main',p,1.5)]['including_initial_probe_calls_per_correct_artifact']:.2f}") for p in ["metadata_shortest_path","fixed_workflow","global_filter_path","global_risk_path","conditional_evidence_path"]], wide=True,
      note="字节均值以启动路径为分母；本表五策略均启动128条。ECP含取证后为(416+928)/128=10.50，人工流程为448/128=3.50。调用不是货币成本。")
table("network_dataset_table.tex", "主结果分数据集核对。每格为同64个输入在三档预算下的成功总数/192。两个数据集的模式完全相同，反映构造语义主导的限制。", "tab:network-datasets", "Xrr", ["策略", "WDBC", "Banknote"],
      [(names[p], *[f"{next(r for r in a['by_held_out_dataset'] if r['dataset']==d and r['policy']==p)['successes']}/192" for d in ["wdbc","banknote"]]) for p in names], wide=False)
for name, src in [("network-analysis.json", N/"analysis-v1/analysis.json"), ("network-posthoc.json", N/"joint-posthoc-v1/summary.json"), ("decision-summary.json", D/"diagnostic-v3/summary.json")]:
    shutil.copyfile(src, OUT/name)

font = Path("C:/Windows/Fonts/msyh.ttc")
if font.exists():
    fontManager.addfont(str(font))
    plt.rcParams["font.family"] = FontProperties(fname=str(font)).get_name()
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.unicode_minus": False,
                     "pdf.fonttype": 42, "savefig.dpi": 300})
blue, light, gray, teal, orange = "#27408b", "#87ceeb", "#78818c", "#287e80", "#b86624"
fig, axes = plt.subplots(1,2,figsize=(10.7,3.9),gridspec_kw={"width_ratios":[1,1.18]},layout="constrained")
ax=axes[0]
for p, label, color, marker, style in [
    ("conditional_evidence_path","ECP",blue,"o","-"),
    ("fixed_workflow","人工固定 / 全局风险（重合）",teal,"s","--"),
    ("conditional_top5","条件证据前五",orange,"^","-."),
    ("metadata_shortest_path","元数据最短路径",gray,"D",":"),
]:
    ax.plot([1,1.5,2], [100*groups[("main",p,m)]["success_rate"] for m in [1.,1.5,2.]], marker=marker,color=color,ls=style,label=label,lw=1.5)
ax.set(xlabel="预算 / 元数据最低路径字节",ylabel="完整产物成功率（%）",xticks=[1,1.5,2],yticks=[0,25,50,75,100],ylim=(-4,105),title="A  三个预定预算档位（每档 n=128）")
ax.legend(loc="center right",bbox_to_anchor=(1,.34),fontsize=7.5,frameon=False)
ax=axes[1]
selected=[next(r for r in a["paired_effects"] if r["base"]==p) for p in ["metadata_shortest_path","fixed_workflow","global_risk_path","global_filter_path","conditional_top5"]]
for y,r in enumerate(selected):
    mean=r["mean_difference"]*100
    lo,hi=np.array(r["conditional_interval_95"])*100
    ax.errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt="o",color=blue,capsize=3,lw=1.2)
ax.axvline(0,color="#b6b6b6",lw=.8)
ax.set(yticks=range(len(selected)),yticklabels=[names[r["base"]] for r in selected],xlabel="ECP 的三档平均成功差（百分点）",xlim=(-4,74),title="B  配对差与95%条件重采样区间")
ax.invert_yaxis()
fig.savefig(FIG/"network_budget_effects.pdf",bbox_inches="tight")
fig.savefig(FIG/"network_budget_effects.png",bbox_inches="tight")
plt.close(fig)

fig,ax=plt.subplots(figsize=(9.8,3.25),layout="constrained")
policies=["conditional_evidence_path","global_risk_path","fixed_workflow","evidence_without_version","metadata_shortest_path"]
for i,(cohort,label,color,marker) in enumerate([("precision","精度 n=24",teal,"s"),("version_drift","版本变化 n=128",blue,"o"),("joint","组合（事后）n=24",orange,"^")]):
    vals=[100*j["methods"][p]/24 if cohort=="joint" else 100*groups[(cohort,p,1.5)]["success_rate"] for p in policies]
    ax.scatter(np.arange(len(policies))+(i-1)*.17,vals,label=label,color=color,marker=marker,s=42)
ax.set(xticks=range(len(policies)),xticklabels=[names[p] for p in policies],ylabel="完整产物成功率（%）",ylim=(-5,110),yticks=[0,25,50,75,100])
ax.legend(ncols=3,loc="upper center",bbox_to_anchor=(.5,1.2),frameon=False)
fig.savefig(FIG/"network_stress.pdf",bbox_inches="tight")
fig.savefig(FIG/"network_stress.png",bbox_inches="tight")
plt.close(fig)

rows=[json.loads(v) for v in (N/"execution-v2/decisions.jsonl").read_text(encoding="utf-8").splitlines()]
ids=sorted({r["task_id"] for r in rows if r["cohort"]=="main"})
mapr={(r["task_id"],r["policy"]):r["task_success"] for r in rows if r["cohort"]=="main" and r["multiplier"]==1.5}
matrix=np.array([[mapr[(t,p)] for p in policies[:3]+["metadata_shortest_path"]] for t in ids],dtype=int)
fig,ax=plt.subplots(figsize=(4.9,6.1),layout="constrained")
ax.imshow(matrix,aspect="auto",interpolation="nearest",cmap=ListedColormap(["#e5e7eb",blue]),vmin=0,vmax=1)
ax.set(xticks=range(4),xticklabels=["ECP","全局风险","人工固定","元数据"],yticks=[0,31,63,95,127],yticklabels=[1,32,64,96,128],ylabel="冻结任务ID排序（128个输入）",title="中预算完整产物二元结果")
fig.savefig(FIG/"network_binary_matrix.pdf",bbox_inches="tight")
fig.savefig(FIG/"network_binary_matrix.png",bbox_inches="tight")
plt.close(fig)
print("Generated 6 tables and 3 plot directions from frozen actual executions.")
