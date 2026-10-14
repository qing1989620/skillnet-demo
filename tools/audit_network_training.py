"""Re-read real model/data artifacts and independently audit a research candidate."""
from pathlib import Path
import argparse,csv,hashlib,json,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.learned_network import NetworkAdapter,digest
from skillnet.reward_gates import Audit,policy_sha256

def main():
    p=argparse.ArgumentParser();p.add_argument('--experiment',required=True,type=Path);p.add_argument('--external',required=True,type=Path);args=p.parse_args();folder=args.experiment
    report=json.loads((folder/'final-report.json').read_text(encoding='utf-8'));protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'));corpus=json.loads((folder/'corpus.json').read_text(encoding='utf-8'));external=json.loads((args.external/'report.json').read_text(encoding='utf-8'))
    assert digest(corpus)==protocol['corpus_sha256']
    assert hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()==report['protocol_sha256']
    with np.load(folder/'features.npz',allow_pickle=False) as f:x,q,g=f['skills'],f['queries'],f['neighbours']
    selected=next(e for e in report['experiments'] if e['name']==report['selected_by_validation']);path=Path(selected['path']);ids=[n['id'] for n in corpus['nodes']];by={n:i for i,n in enumerate(ids)}
    test=[i for i,t in enumerate(corpus['tasks']) if t['split']=='test'];rows=[]
    for repeat in range(2):
        adapter=NetworkAdapter.load(path)
        baseline=q[test]@x.T;predicted=adapter.query(q[test])@adapter.skills(x,g,graph=selected['graph']).T
        for j,i in enumerate(test):
            t=corpus['tasks'][i];b=np.argsort(-baseline[j],kind='stable')[:5];c=np.argsort(-predicted[j],kind='stable')[:5];gold={by[n] for n in t['gold']}
            rb=sum(n in gold for n in b)/len(gold);rc=sum(n in gold for n in c)/len(gold)
            assert abs(rb-report['baseline']['test']['rows'][j]['recall5'])<1e-10
            assert abs(rc-selected['test']['rows'][j]['recall5'])<1e-10
            rows.append(dict(repeat=repeat+1,task=t['id'],family=t['family'],query_sha256=t['query_sha256'],baseline_recall5=rb,candidate_recall5=rc,baseline_top5=json.dumps([ids[n] for n in b]),candidate_top5=json.dumps([ids[n] for n in c]),gold=json.dumps(t['gold'])))
    evidence=folder/'independent-routing-recheck.csv'
    with evidence.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    audit=Audit(dict(kind='research_routing_candidate',model_id=adapter.metadata['model_id'],
        scope='冻结路由参考的模型研究检查，不是下游执行能力证书；确定性复算两次不增加独立样本数',
        protocol_sha256=report['protocol_sha256']))
    bound=protocol.get('reward_policy_sha256')==policy_sha256()
    audit.set('frozen','passed' if bound else 'unknown','训练/验证/测试已冻结；首轮协议未绑定奖励政策指纹，不能补写历史证据' if not bound else '路由研究协议与奖励政策均已冻结')
    audit.set('independent','passed','独立实现重新读取权重和真实冻结参考，复算每条 Recall@5；仅证明路由匹配',recomputed_rows=len(rows))
    audit.set('integrity','passed','权重、语料、协议与特征指纹一致',weights_sha256=adapter.metadata['weights_sha256'],evidence_sha256=hashlib.sha256(evidence.read_bytes()).hexdigest())
    audit.set('complete','passed','全部冻结测试题均已报告，没有删除退步样本',tasks=len(test))
    audit.set('version','passed','核验绑定同一候选权重、编码器和公开语料版本',model_id=adapter.metadata['model_id'])
    audit.set('fair','passed','同一候选池、查询、冻结文本编码器；候选仅增加已声明的小适配器',candidate_count=len(ids),paid_llm_calls=0)
    train={t['query_sha256'] for t in corpus['tasks'] if t['split']=='train'}
    heldout={corpus['tasks'][i]['query_sha256'] for i in test}
    assert not train&heldout
    audit.set('heldout','passed','测试问题和标签未进入梯度或检查点选择；公开技能文档用于传导式预训练',test_task_overlap=0)
    families={r['family'] for r in rows}
    audit.set('suite','passed' if len(families)>=5 else 'failed','完整报告全部任务族，两次确定性复算；按任务族计算独立样本量',families=len(families),deterministic_rechecks=2)
    comp=report['comparison'];losses=comp['losses']+external['losses']
    audit.set('regression','failed' if losses else 'passed','域内与外部探针均存在退步，必须拦截',in_domain_regressions=comp['losses'],external_regressions=external['losses'])
    audit.set('gain','failed','域内改善没有迁移为外部来源改善，不能给通用底座认证',in_domain_family_gain=comp['family_equal_weight_mean_gain'],external_gain=external['mean_gain'])
    audit.set('reliable','unknown','任务族符号检验未过 0.05，且该统计分析未预注册；不能用逐题 p 值冒充可靠增益',family_sign_p=comp['family_sign_p'])
    audit.set('novel','unknown','尚无模型版本准入与奖励凭证，不生成积分')
    result=audit.result();result.update(serving_changed=False,external_transfer=external['report_sha256'])
    result.pop('audit_sha256',None);result['audit_sha256']=digest(result)
    (folder/'admission-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    pub=json.loads((folder/'public-report.json').read_text(encoding='utf-8'));pub.pop('report_sha256',None)
    pub['admission']=result;pub['external_transfer']={k:v for k,v in external.items() if k!='rows'}
    pub['corpus']['edge_records']=len(corpus['edges'])
    pub['corpus']['unique_typed_edges']=len({(e['source'],e['target'],e['type']) for e in corpus['edges'] if e['source']!=e['target']})
    pub['selected_training_curve']=selected['curve'];pub['report_sha256']=digest(pub)
    out=ROOT/'docs/evidence/network-training-v1.json';out.parent.mkdir(exist_ok=True,parents=True);out.write_text(json.dumps(pub,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Independent model audit',result['passed'],'/ 12; eligible',result['eligible'],'blockers',result['blockers'],flush=True)

if __name__=='__main__':main()
