"""Controlled synthetic owner preferences; actual encoder and gradients, no user-study claim."""
from pathlib import Path
import argparse,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet.catalog import SkillLibrary
from skillnet.semantic import DenseIndex
from skillnet.personal_network import PersonalNetworkStore
from skillnet.network_service import train_private_preference_candidate,preview_private_candidate
from skillnet.learned_network import digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args();out=args.output;out.mkdir(exist_ok=True,parents=True)
    assert not (out/'report.json').exists(),'Preserve the previous experiment; choose a new output folder'
    store=PersonalNetworkStore(out/'private.sqlite3');encoder=DenseIndex(ROOT/'.models/multilingual-e5-small');lib=SkillLibrary.load();names=[s.name for s in lib.all()]
    before=digest([s.to_dict() for s in lib.all()]);shared_weights=ROOT/'data/network-model/model.npz';weight_sha=hashlib.sha256(shared_weights.read_bytes()).hexdigest()
    subjects=['重复样本','缺失值','数据类型','编码问题','异常值','字段一致性','跨组泄漏','格式转换','列名规范','数据合并','审计日志','清洗报告','数值范围','表格对齐','分组检查','原值保留']
    queries=[f'请在表格清理任务中处理{topic}，保留原始数据并生成可复核的交付文件。' for topic in subjects]
    probes=['设计 CUDA 算子融合与显存优化方案，比较 GPU 访存和并行调度。',
        '证明有限域上的不可约多项式对应扩域，并讨论群作用。',
        '如何核验 OAuth2 回调地址与 PKCE 授权码交换的安全边界？',
        '建立月球轨道摄动模型，计算航天器的轨道转移窗口。']
    frozen=dict(version='personal-scope-controlled-protocol-v3',subjects='two synthetic owners; not independent real users',
        query_sha256=[hashlib.sha256(q.encode()).hexdigest() for q in queries],
        out_of_scope_probe_sha256=[hashlib.sha256(q.encode()).hexdigest() for q in probes],
        scope_min_cosine=.88,holdout='query SHA modulo 5; heldout questions never added to support vectors',
        shared_weights_frozen=True,capability_reward=False)
    assert not (out/'protocol-before-training.json').exists(),'Preserve the frozen protocol; choose a new directory'
    (out/'protocol-before-training.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    rows=[];contexts=[]
    for user,preferred,rejected in [('virtual-python-owner','data-cleaning','xlsx'),('virtual-excel-owner','xlsx','data-cleaning')]:
        context=dict(tenant='synthetic-research',user=user,project='preference-isolation');contexts.append(context)
        for query in queries:store.feedback(context,query,preferred,rejected,names)
        report=train_private_preference_candidate(store,context,encoder,lib,out/'models')
        preview=preview_private_candidate(store,context,encoder,lib,[{'name':n,'score':1} for n in ['data-cleaning','xlsx']],queries[0],out/'models')
        profile=store.update(context,0,{'active_personal_model':report['model_id']},names)
        assert profile['active_personal_model']==report['model_id']
        selected_preview=preview_private_candidate(store,context,encoder,lib,[{'name':n,'score':1} for n in ['data-cleaning','xlsx']],queries[0],out/'models',profile['active_personal_model'])
        assert selected_preview['available'] and selected_preview['model_id']==report['model_id']
        scope_rows=[]
        for i,probe in enumerate(probes):
            checked=preview_private_candidate(store,context,encoder,lib,[{'name':n,'score':1} for n in ['data-cleaning','xlsx']],probe,out/'models',profile['active_personal_model'])
            scope_rows.append(dict(probe=i+1,within_support=checked['within_support'],max_support_similarity=checked['max_support_similarity'],
                ranking_preserved=[r['name'] for r in checked['ranking']]==['data-cleaning','xlsx']))
        assert store.update(context,1,{'active_personal_model':None},names)['active_personal_model'] is None
        rows.append(dict(user=user,preferred=preferred,train_queries=report['train_queries'],holdout_queries=report['holdout_queries'],loss_before=report['loss_before'],loss_after=report['loss_after'],holdout_accuracy_before=report['holdout_preference_accuracy_before'],holdout_accuracy_after=report['holdout_preference_accuracy_after'],holdout_scope_coverage=report['holdout_scope_coverage'],parameter_delta_l2=report['parameter_delta_l2'],preview_order=[r['name'] for r in preview['ranking']],manual_selection_and_withdrawal_verified=True,scope_probes=scope_rows,deployed=report['deployed'],reward=report['reward']))
    assert before==digest([s.to_dict() for s in lib.all()]);assert weight_sha==hashlib.sha256(shared_weights.read_bytes()).hexdigest()
    assert all(r['reward']==0 and not r['deployed'] for r in rows)
    assert all(len(store.observations(c))==16 for c in contexts)
    report=dict(version='personal-network-controlled-experiment-v3',scope='Controlled synthetic owner pair preferences and dissimilar-question probes; not real user behaviour or execution success. Reuses the same synthetic preferences; not additional independent subjects.',protocol_sha256=hashlib.sha256((out/'protocol-before-training.json').read_bytes()).hexdigest(),encoder_revision=encoder.status['revision'],contexts_isolated=True,shared_catalog_unchanged=True,shared_model_unchanged=True,rows=rows,quality_rewards=0)
    report['report_sha256']=digest(report);(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'docs/evidence/personal-network-experiment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
