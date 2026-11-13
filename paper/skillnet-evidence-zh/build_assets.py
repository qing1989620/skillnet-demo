"""Build manuscript tables, bibliography and releasable synthetic-data artifacts."""

import csv
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
analysis_path = ROOT / "out/research/skill-execution/20261111-analysis-v1/analysis.json"
if analysis_path.exists():
    shutil.copyfile(analysis_path, RESULTS / "analysis.json")
    shutil.copyfile(analysis_path.with_name("posthoc-diagnostics.json"), RESULTS / "posthoc-diagnostics.json")
    shutil.copyfile(analysis_path.with_name("trial-outcomes.jsonl"), RESULTS / "trial-outcomes.jsonl")
    shutil.copyfile(
        ROOT / "out/research/skill-execution/20261111-prepared-v2/cases.private.jsonl",
        RESULTS / "constructed-tasks.jsonl",
    )
    shutil.copyfile(
        ROOT / "out/research/skill-execution/20261111-five-arm-v1/run-plan.json", RESULTS / "run-plan.json"
    )
    for source in [
        "quality-summary.json",
        "routing-summary.json",
        "deepseek-readiness-analysis.json",
        "evidence-binding-summary.json",
        "literature_review.json",
    ]:
        path = (
            ROOT
            / "research/skill_study"
            / ("results/" + source if source != "literature_review.json" else source)
        )
        shutil.copyfile(path, RESULTS / source)
d = json.loads((RESULTS / "analysis.json").read_text(encoding="utf-8"))
post = json.loads((RESULTS / "posthoc-diagnostics.json").read_text(encoding="utf-8"))
assert d["responses"] == 300 and d["summary"]["complete"]
assert post["complete_successes"] == 23 and post["failed_required_checks"] == 259
names = {
    "no_skill": "A0 无 Skill",
    "original": "A1 原始包",
    "evidence_contract": "A2 原包＋契约",
    "unrelated": "A3 无关上下文",
    "contract_only": "A4 仅契约",
}
codes = {k: v[:2] for k, v in names.items()}


def table(name, caption, label, cols, header, rows, wide=False, note=""):
    env = "table*" if wide else "table"
    width = "\\textwidth" if wide else "\\columnwidth"
    text = "\\begin{" + env + "}[t]\n\\caption{" + caption + "}\\label{" + label + "}\n\\centering\\small\n"
    text += "\\begin{tabularx}{" + width + "}{" + cols + "}\n\\toprule\n" + header + " \\\\\n\\midrule\n"
    text += "\n".join(" & ".join(str(x) for x in row) + " \\\\" for row in rows)
    text += "\n\\bottomrule\n\\end{tabularx}\n"
    if note:
        text += "\\par\\vspace{2pt}{\\footnotesize " + note + "}\n"
    text += "\\end{" + env + "}\n"
    (RESULTS / name).write_text(text, encoding="utf-8", newline="\n")


table(
    "execution_table.tex",
    "五臂实际产物结果。范围内每组48次；边界处置每组12次。费用只汇总范围内请求的峰价上界，不是独立账单。",
    "tab:execution",
    "Xrrrrr",
    "方法 & 合格数 & 成功率(\\%) & 边界 & 平均输入token & 元上界",
    [
        [
            names[r["arm"]],
            f"{r['passed']}/48",
            f"{100 * r['success_rate']:.2f}",
            "12/12",
            f"{r['prompt_tokens'] / 48:.0f}",
            f"{float(r['peak_tariff_upper_cny']):.4f}",
        ]
        for r in d["aggregates"]
        if r["stratum"] == "artifact"
    ],
    True,
)
table(
    "effects_table.tex",
    "预先固定的配对比较。差为百分点；区间是12个构造条件簇的条件重采样百分位区间，未经多重比较校正，不是总体保证。",
    "tab:effects",
    "Xrrr",
    "比较 & 均值差 & 95\\%条件区间 & 胜/负/平",
    [
        [
            codes[r["selected"]] + "$-$" + codes[r["base"]],
            f"{100 * r['mean_paired_difference']:+.2f}",
            f"[{100 * r['conditional_percentile_interval_95'][0]:.2f}, {100 * r['conditional_percentile_interval_95'][1]:.2f}]",
            f"{r['paired_wins']}/{r['paired_losses']}/{r['paired_ties']}",
        ]
        for r in d["paired_effects"]
    ],
    True,
)
table(
    "sizes_table.tex",
    "范围内输入规模分层。每个单元格为合格产物数/24次，两个重复不是独立任务。",
    "tab:sizes",
    "Xrr",
    "方法 & 8行 & 48行",
    [
        [
            names[a],
            str(next(r["passed"] for r in d["by_row_count"] if r["arm"] == a and r["rows"] == 8)) + "/24",
            "0/24",
        ]
        for a in d["arms"]
    ],
)
table(
    "faults_table.tex",
    "受控接口干预结果。强标准库参照与扩展规则均达到当前受限机械契约的满检出；不能外推成整体质量准确率。",
    "tab:faults",
    "Xrrr",
    "已知缺陷 & 数量 & 参数名规则 & 扩展/标准库",
    [
        ["虚构选项", 80, 80, "80/80"],
        ["遗漏必填", 22, 0, "22/22"],
        ["非法枚举", 38, 0, "38/38"],
        ["数值类型", 14, 0, "14/14"],
        ["合计", 154, 80, "154/154"],
    ],
)
table(
    "judge_table.tex",
    "真实模型评价先导。引用分母只来自结构合格响应，定位有效不代表语义支持。",
    "tab:judge",
    "Xrrr",
    "提示 & 结构合格 & 引用定位 & 未知维度",
    [
        ["普通rubric", "17/18", "123/125", "9/136"],
        ["支持证据优先", "18/18", "132/135", "9/144"],
        ["反证优先", "18/18", "127/129", "15/144"],
    ],
)
table(
    "routing_table.tex",
    "全库Fabric组的历史检索回放。既见12例不是新留出；相关性与完整集合覆盖分别计量。",
    "tab:routing",
    "Xrrrr",
    "方法 & 20例R@5 & 20例F & 既见12 R@5 & 既见12 F",
    [
        ["原顺序", "80.00", "55.00", "78.47", "58.33"],
        ["MMR .7", "80.00", "55.00", "75.69", "50.00"],
        ["原核DPP", "80.00", "55.00", "78.47", "58.33"],
        ["残差DPP .5", "80.00", "55.00", "78.47", "58.33"],
        ["残差DPP 1", "80.00", "55.00", "78.47", "58.33"],
        ["查询覆盖 .5", "80.83", "55.00", "78.47", "50.00"],
        ["候选池上限", "100.00", "100.00", "94.44", "91.67"],
    ],
    True,
    note="R@5与F单位均为百分比；候选池上限使用参考标签作事后上界，不是实际选择器。",
)
macros = {
    "NormalPassRate": f"{100 * 23 / 240:.2f}",
    "CheckPassRate": f"{100 * post['mean_required_check_pass_fraction']:.2f}",
    "MeasurePassRate": f"{100 * post['five_data_measure_check_pass_fraction']:.2f}",
    "NewPromptTokens": f"{d['summary']['prompt_tokens']:,}",
    "NewOutputTokens": f"{d['summary']['completion_tokens']:,}",
    "NewPeakCny": f"{float(d['summary']['tariff_upper']['CNY']):.4f}",
    "NewPeakUsd": f"{float(d['summary']['tariff_upper']['USD']):.6f}",
}
(RESULTS / "macros.tex").write_text(
    "\n".join("\\newcommand{\\" + k + "}{" + v + "}" for k, v in macros.items()) + "\n", encoding="utf-8"
)
records = json.loads((RESULTS / "literature_review.json").read_text(encoding="utf-8"))["records"]
assert len(records) == 44 and len({r["id"] for r in records}) == 44


def esc(text):
    return "".join(
        {
            "&": r"\&",
            "%": r"\%",
            "_": r"\_",
            "#": r"\#",
            "$": r"\$",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
            "\\": r"\textbackslash{}",
            "τ": r"\ensuremath{\tau}",
        }.get(c, c)
        for c in str(text)
    )


bib = []
for record in records:
    authors = record["authors"]
    if record["id"] == "P28":
        authors = [
            "Shi, Lin",
            "Ma, Chiyu",
            "Liang, Wenhua",
            "Diao, Xingjian",
            "Ma, Weicheng",
            "Vosoughi, Soroush",
        ]
    assert authors, record["id"]
    author = " and ".join(esc(a) for a in authors[:3]) + (" and others" if len(authors) > 3 else "")
    venue = record["venue"]
    formal = venue != "arXiv preprint"
    pinned = record.get("pinned_arxiv")
    years = re.findall(r"(?:19|20)\d{2}", venue)
    year = years[-1] if years else ("20" + pinned[:2] if pinned else "2025")
    # The read versions of these titles differ from their later published titles.
    if record["id"] in ["P19", "P20"]:
        kind = "misc"
        year = "20" + pinned[:2]
        venue = "arXiv preprint"
    elif not formal:
        kind = "misc"
    elif any(x in venue for x in ["Nature", "Journal", "TMLR", "Foundations"]):
        kind = "article"
    else:
        kind = "inproceedings"
    title = record["title"].replace("$k$", "k").replace("$τ$", "τ")
    fields = {
        "author": author,
        "title": "{" + esc(title) + "}",
        "year": year,
        "url": record["primary_url"],
    }
    if kind == "article":
        fields["journal"] = esc(venue)
    elif kind == "inproceedings":
        fields["booktitle"] = esc(venue)
    else:
        fields["howpublished"] = esc(venue)
    if pinned and pinned not in record["primary_url"]:
        fields["note"] = "Read version: arXiv:" + pinned
    bib.append(
        "@"
        + kind
        + "{"
        + record["id"]
        + ",\n"
        + ",\n".join("  " + k + " = {" + v + "}" for k, v in fields.items())
        + "\n}"
    )
(HERE / "references.bib").write_text("\n\n".join(bib) + "\n", encoding="utf-8", newline="\n")
with (RESULTS / "trial-outcomes.csv").open("w", encoding="utf-8-sig", newline="") as stream:
    keys = [
        "trial_id",
        "task_id",
        "condition",
        "rows",
        "arm",
        "repeat",
        "stratum",
        "task_success",
        "failed_checks",
    ]
    writer = csv.DictWriter(stream, fieldnames=keys)
    writer.writeheader()
    for line in (RESULTS / "trial-outcomes.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        writer.writerow({k: (",".join(row[k]) if k == "failed_checks" else row[k]) for k in keys})
(RESULTS / "table-provenance.json").write_text(
    json.dumps(
        {
            "source_summary_sha256": d["source_summary_sha256"],
            "figures_and_tables": "actual recorded API outputs on constructed tasks",
            "bib_record_count": 44,
            "posthoc_metrics_explicit": True,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(
    json.dumps(
        {"generated_tables": 6, "bib_entries": 44, "model_responses": d["responses"], "macros": macros},
        ensure_ascii=False,
    )
)
