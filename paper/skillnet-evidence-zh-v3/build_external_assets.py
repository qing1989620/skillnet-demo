"""Rebuild four manuscript tables from frozen external and CLI observations."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'research/skill_external/results'
OUT=HERE/'results'

def load(name):
    return json.loads((BASE/name).read_text(encoding='utf-8'))

def table(name,caption,label,head,rows,cols):
    text='\\begin{table*}[t]\n\\caption{'+caption+'}\\label{'+label+'}\n\\centering\\small\n\\begin{tabularx}{\\textwidth}{'+cols+'}\n\\toprule\n'
    text+=' & '.join(head)+r' \\'+'\n\\midrule\n'
    text+='\n'.join(' & '.join(map(str,r))+r' \\' for r in rows)
    text+='\n\\bottomrule\n\\end{tabularx}\n\\end{table*}\n'
    (OUT/name).write_text(text,encoding='utf-8')

a=load('analysis-v3/analysis.json');c=load('community-v1/summary.json');j=load('joint-posthoc-v1/summary.json')
lookup={(r['script'],r['threshold']):r for r in c['groups']}
rr=[]
for script,threshold,name in [('data_profiler.py',0,'原画像：行数与原生缺失规则'),('data_profiler_repaired.py',0,'画像修复副本：相同目标'),('missing_value_analyzer.py',0,'原缺失分析：原生缺失规则'),('outlier_detector.py',1.5,'原IQR：阈值1.5'),('outlier_detector.py',3.0,'原IQR：阈值3.0'),('outlier_detector_repaired.py',1.5,'IQR修复：阈值1.5'),('outlier_detector_repaired.py',3.0,'IQR修复：阈值3.0')]:
    r=lookup[(script,threshold)];rr.append([name,r['n'],r['passed'],r['nonzero_exit']])
rr.append(['六个原模板入口：输出路径子契约',12,0,0])
table('community_table.tex','355次社区原始/修复CLI的实际执行。表中通过仅限列出的目标子契约，非整个Skill质量；49个输入含48个UCI派生输入与1个显式回归例。','tab:community',['工具及目标','执行数','目标通过','异常退出'],rr,'Xrrr')
names={'standard':'普通直接评审','evidence_rules':'同材料证据规则','artifact_packet':'范围提示臂（原计划附产物）'}
rows=[]
for arm,name in names.items():
    r=a['by_arm'][arm]
    rows.append([name,f"{r['valid']}/86",f"{r['correct']}/86",f"{100*r['balanced_accuracy']:.2f}",f"{r['brier_invalid_fixed_half']:.3f}",f"{r['false_acceptances']}/62",f"{100*r['confidence_coverage']:.2f}"])
table('external_judge_table.tex','因402中断后的86个完整配对案例；24个官方通过、62个失败。Brier中无效响应固定概率0.5。没有产物快照的实际子集不能检验有产物时的增强收益。','tab:external-judge',['方案','结构有效','判断正确','平衡准确率(\\%)','Brier','错误放行','置信覆盖(\\%)'],rows,'Xrrrrrr')
short={'crystallographic-wyckoff-position-analysis':'晶体Wyckoff位置','dialogue-parser':'对话解析','earthquake-phase-association':'地震相位关联','energy-market-pricing':'能源市场定价','invoice-fraud-detection':'发票欺诈检测','jax-computing-basics':'JAX计算基础'}
rows=[]
for task in sorted(a['attempted_task_counts']):
    rs=[r for r in a['by_task'] if r['task']==task]
    first=rs[0]
    rows.append([short[task],first['n'],f"{first['gold_pass']}/{first['gold_fail']}",*[f"{100*next(r for r in rs if r['arm']==arm)['balanced_accuracy']:.2f}" for arm in names]])
table('external_task_table.tex','中断后六个实际任务的平衡准确率，单位为百分比。任务不是按结果抽样；排序中断导致其余八个预定任务未进入配对分析。','tab:external-tasks',['源任务','轨迹数','通过/失败','普通','证据规则','范围提示'],rows,'Xrrrrr')
mapnames={'fixed_original':'固定原始流程','original_metadata':'原候选＋最短路径','original_evidence':'原候选＋开发失败过滤','expanded_metadata':'加修复候选＋最短路径','expanded_evidence':'加修复候选＋证据路径'}
rows=[]
for m,n in mapnames.items():
    r=next(r for r in j['groups'] if r['cohort']=='held_source' and r['method']==m)
    e=next(r for r in j['groups'] if r['cohort']=='explicit_regression' and r['method']==m)
    rows.append([n,f"{r['successes']}/48",r['abstentions'],f"{e['successes']}/2"])
table('natural_joint_table.tex','事后自然工具联合验收回放：24个来源留出输入、两个阈值。复用355次CLI输出，不增加新执行；显式回归例与来源留出分开。','tab:natural-joint',['候选与选择策略','联合通过','弃权','显式回归'],rows,'Xrrr')
for name,obj in [('external-analysis.json',a),('community-runtime-summary.json',c),('natural-joint-summary.json',j)]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Built four tables from frozen observations.')
