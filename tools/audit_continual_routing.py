"""Independently recompute a frozen continuation study; never grant execution rewards."""
from __future__ import annotations

import argparse,csv,hashlib,json,re,sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.learned_network import NetworkAdapter,digest
from skillnet.reward_gates import Audit,policy,policy_sha256
from skillnet.routing_research import query_fingerprint,paired_routing_comparison


def main():
    p=argparse.ArgumentParser();p.add_argument('--experiment',type=Path,required=True);a=p.parse_args();folder=a.experiment
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    corpus=json.loads((folder/'corpus.json').read_text(encoding='utf-8'))
    report=json.loads((folder/'final-report.json').read_text(encoding='utf-8'))
    selection=json.loads((folder/'selection-before-calibration-and-test.json').read_text(encoding='utf-8'))
    assert digest(corpus)==protocol['corpus_sha256']
    assert hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()==report['protocol_sha256']==selection['protocol_sha256']
    assert hashlib.sha256((folder/'features.npz').read_bytes()).hexdigest()==report['features_sha256']
    assert re.fullmatch(r'retention-[014]-seed-(17|29)',selection['name'])
    model_dir=folder/'models'/selection['name'];model=NetworkAdapter.load(model_dir)
    assert model.metadata['weights_sha256']==selection['weights_sha256']
    assert model.metadata['parent_weights_sha256']==protocol['initial_weights_sha256']
    with np.load(folder/'features.npz',allow_pickle=False) as z:x,q=z['skills'],z['queries']
    ids=[n['id'] for n in corpus['nodes']];by={n:i for i,n in enumerate(ids)}
    indices=[i for split in ['test','external_test'] for i,t in enumerate(corpus['tasks']) if t['split']==split]
    tasks=[corpus['tasks'][i] for i in indices]
    assert [t['id'] for t in tasks]==[r['id'] for r in report['baseline_test']['rows']]
    alpha=report['calibration']['selected_alpha'];assert alpha in protocol['calibration_policy']['alphas']
    rows=[]
    for repeat in range(2):
        loaded=NetworkAdapter.load(model_dir)
        baseline=q[indices]@x.T;candidate=loaded.query(q[indices])@loaded.skills(x,graph=False).T
        controlled=(1-alpha)*baseline+alpha*candidate
        for j,t in enumerate(tasks):
            pool=np.array(corpus['pools'][t['pool']]);gold={by[n] for n in t['gold']};values={}
            for key,score in [('baseline_test',baseline),('selected_test',candidate),('controlled_test',controlled)]:
                order=pool[np.argsort(-score[j,pool],kind='stable')][:5]
                recall=sum(n in gold for n in order)/len(gold)
                expected=report[key]['rows'][j]
                assert abs(recall-expected['recall5'])<1e-10 and [ids[n] for n in order]==expected['top5']
                values[key]=recall
            rows.append(dict(repeat=repeat+1,id=t['id'],source=t['source'],family=t['family'],query_sha256=query_fingerprint(t['query']),
                baseline_recall5=values['baseline_test'],raw_recall5=values['selected_test'],controlled_recall5=values['controlled_test']))
    path=folder/'independent-routing-recheck.csv'
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    trained={query_fingerprint(t['query']) for t in corpus['tasks'] if t['split']=='train'}
    fresh={query_fingerprint(t['query']) for t in tasks};assert not trained&fresh
    train_groups={t['family'] for t in corpus['tasks'] if t['split']=='train' and t['source']!='gymv1'}
    assert not train_groups&{t['family'] for t in tasks}
    assert all(t['source'] not in ('theoremqa','bigcodebench') for t in corpus['tasks'] if t['split']=='train')
    comparison=paired_routing_comparison(report['baseline_test'],report['controlled_test'])
    assert comparison==report['comparison_controlled']
    audit=Audit(dict(kind='controlled_routing_research_v2',model_id=model.metadata['model_id'],shadow_alpha=alpha,
        protocol_sha256=report['protocol_sha256'],scope='路由参考检索的研究核验；不是执行效果、个体成功概率或技能因果奖励'))
    frozen=(protocol['reward_policy_sha256']==policy_sha256()
        and hashlib.sha256((ROOT/'tools/train_continual_routing.py').read_bytes()).hexdigest()==protocol['training_script_sha256']
        and hashlib.sha256((ROOT/'skillnet/routing_research.py').read_bytes()).hexdigest()==protocol['metric_code_sha256'])
    audit.set('frozen','passed' if frozen else 'failed','编码/训练前冻结来源、分区、代码、父权重和原十二门政策；未追补首轮历史协议')
    audit.set('independent','passed','另一实现重新读取数值权重及全部新测试参考，逐条复算原始和受控排序',recomputed_rows=len(rows))
    audit.set('integrity','passed','协议、语料、特征、权重、父版本及实际复算产物的指纹一致',weights_sha256=model.metadata['weights_sha256'],evidence_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    complete=(len(report['experiments'])==6 and all(len(e['curve'])==protocol['epochs'] for e in report['experiments']))
    audit.set('complete','passed' if complete else 'failed','全部预注册消融与所有封存样本已报告；没有删掉退步任务',tasks=len(tasks),experiments=len(report['experiments']))
    audit.set('version','passed','同一冻结编码器、父候选版本和各来源候选池；未替换私有或过期正文',model_id=model.metadata['model_id'],parent_sha256=protocol['initial_weights_sha256'])
    audit.set('fair','passed','同一问题与同一来源候选池；各方案均无付费模型调用，校准强度提前声明',pools=protocol['pools'],paid_llm_calls=0)
    audit.set('heldout','passed','新测试的问题和参考包族不进入梯度；两个整来源仅外部测试；旧测试只作已暴露诊断',query_overlap=0,reference_family_overlap=0)
    families=len({(t['source'],t['family']) for t in tasks})
    audit.set('suite','passed' if families>=policy()['min_tasks'] else 'failed','全部新测试完整报告；两次确定性复算不增加独立样本数',families=families,deterministic_rechecks=2)
    audit.set('regression','passed' if comparison['task_losses']==0 else 'failed','按原政策逐题检查；平均进步不能抵消任何一题退步',controlled_regressions=comparison['task_losses'],raw_regressions=report['comparison_raw']['task_losses'])
    gain=comparison['source_family_macro_gain'];source_gain={s:report['controlled_test']['per_source_family_macro'][s]-v for s,v in report['baseline_test']['per_source_family_macro'].items()}
    enough=gain>=policy()['min_mean_gain'] and all(v>=-1e-10 for v in source_gain.values())
    audit.set('gain','passed' if enough else 'failed','新来源等权增益必须达到原门槛，且各来源均不退步；回退基线不算学习提升',source_family_macro_gain=gain,source_gains=source_gain)
    reliable=comparison['family_sign_p']<=policy()['max_sign_p'] and comparison['family_wins']>=5
    audit.set('reliable','passed' if reliable else 'unknown','参考包组件为统计单位的预注册符号统计；不证明来源间独立或任意分布漂移下有效',family_sign_p=comparison['family_sign_p'],family_wins=comparison['family_wins'])
    audit.set('novel','unknown','研究候选没有执行能力准入和一次性版本奖励凭证，不能生成积分')
    result=audit.result();result.update(serving_changed=False,capability_rewards=0,
        raw_candidate_regressions=report['comparison_raw']['task_losses'],recommended_shadow_alpha=alpha)
    result.pop('audit_sha256',None);result['audit_sha256']=digest(result)
    (folder/'admission-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    public=json.loads((folder/'public-report.json').read_text(encoding='utf-8'));claim=public.pop('report_sha256');assert digest(public)==claim
    public['admission']=result;public['report_sha256']=digest(public)
    (folder/'audited-public-report.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    print(json.dumps({'passed':result['passed'],'total':12,'eligible':result['eligible'],'reward':0,'blockers':result['blockers'],'raw_regressions':report['comparison_raw']['task_losses'],'controlled_regressions':comparison['task_losses'],'shadow_alpha':alpha},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
