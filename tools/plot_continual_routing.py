"""Render the measured continuation result; no synthetic scores or invented intervals."""
from pathlib import Path
import argparse,json


def main():
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=Path('docs/evidence/network-training-v2.json'))
    p.add_argument('--output',type=Path,default=Path('docs/evidence/continual-routing-results.png'));a=p.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np
    r=json.loads(a.report.read_text(encoding='utf-8'));chinese=any(f.name=='Microsoft YaHei' for f in font_manager.fontManager.ttflist)
    plt.rcParams['font.family']='Microsoft YaHei' if chinese else 'DejaVu Sans';plt.rcParams['axes.unicode_minus']=False
    bg,panel,fg,dim='#071c25','#102b35','#e7f2ed','#9bb8be';colors=['#789cab','#b0c5cb','#e5bd80','#a2e7d1']
    fig,axes=plt.subplots(1,2,figsize=(17,6.5),gridspec_kw={'width_ratios':[.9,1.35]});fig.patch.set_facecolor(bg)
    for ax in axes:
        ax.set_facecolor(panel);ax.set_ylim(0,100);ax.tick_params(colors=dim,labelsize=10);ax.grid(axis='y',alpha=.12,color=dim);ax.set_axisbelow(True)
        for s in ['top','right']:ax.spines[s].set_visible(False)
        for s in ['bottom','left']:ax.spines[s].set_color('#476770')
        ax.set_ylabel('Recall@5 (%)',color=dim)
    values=[r[k]['recall5']*100 for k in ['baseline_test','v1_test','selected_test','controlled_test']]
    axes[0].bar(range(4),values,color=colors,width=.65)
    axes[0].set_xticks(range(4),['冻结 E5','首轮候选','继续训练','校准保留'] if chinese else ['Frozen E5','V1','Continued','Retained'])
    for i,v in enumerate(values):axes[0].text(i,v+2,f'{v:.2f}%',ha='center',color=fg,fontsize=13)
    title=f"新测试 · {r['baseline_test']['tasks']} 题 / {r['baseline_test']['families']} 个参考组件" if chinese else f"New test: {r['baseline_test']['tasks']} questions / {r['baseline_test']['families']} reference groups"
    axes[0].set_title(title,color=fg,fontsize=13,pad=20)
    keys=list(r['baseline_test']['per_source_family_macro']);ix=np.arange(len(keys))
    labels=['程序组合','数学概念','逻辑推理','医学计算\n方法检索','数学定理','工具流程'] if chinese else keys
    names=['冻结 E5','首轮候选','继续训练'] if chinese else ['Frozen E5','V1','Continued']
    for offset,key,color,label in zip([-.24,0,.24],['baseline_test','v1_test','selected_test'],colors,names):
        v=[r[key]['per_source_family_macro'][s]*100 for s in keys];axes[1].bar(ix+offset,v,width=.23,color=color,label=label)
    axes[1].set_xticks(ix,labels);axes[1].legend(frameon=False,labelcolor=dim,loc='upper right',bbox_to_anchor=(1,1.17),ncol=3,fontsize=10)
    axes[1].set_title('各来源 · 参考族等权汇总' if chinese else 'Per source: equal reference-group weight',color=fg,fontsize=13,pad=20)
    fig.suptitle('继续训练必须接受跨来源检验' if chinese else 'Continual training needs cross-source evaluation',color=fg,fontsize=22,y=.97)
    caption=f"原始候选 {r['comparison_raw']['task_losses']} 题退步；预定校准选择保留实验基线。正式混合路由未更新，能力奖励 0。" if chinese else 'Raw candidate regressions are reported; calibration retains the baseline. No production update or capability reward.'
    fig.text(.5,.028,caption,ha='center',color=dim,fontsize=11)
    fig.subplots_adjust(left=.055,right=.985,top=.83,bottom=.17,wspace=.23)
    a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=150,facecolor=bg);plt.close(fig)


if __name__=='__main__':main()
