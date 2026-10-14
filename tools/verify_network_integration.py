"""Real encoder + actual FastAPI routes in an isolated ASGI workspace; no paid LLM calls."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
    if (out/'report.json').exists():raise SystemExit('Use a new integration output folder')
    out.mkdir(parents=True,exist_ok=True)
    from fastapi.testclient import TestClient
    import server
    from skillnet.catalog import SkillLibrary
    from skillnet.retriever import Retriever
    from skillnet.learned_network import digest
    data=out/'data';data.mkdir(exist_ok=True)
    for name in ['network-model','network-model-v2']:shutil.copytree(ROOT/'data'/name,data/name)
    shared_before={name:hashlib.sha256((ROOT/'data'/name/'model.npz').read_bytes()).hexdigest() for name in ['network-model','network-model-v2']}
    library_path=ROOT/'data/library.json';library_before=hashlib.sha256(library_path.read_bytes()).hexdigest()
    server.config.OUT_DIR=out/'runtime';server.config.DATA_DIR=data
    server.config.OUT_DIR.mkdir(exist_ok=True)
    library=SkillLibrary.load(ROOT/'data/library.baseline.json');retriever=Retriever(library).build()
    assert retriever.vec.status['kind']=='dense-onnx'
    server.STATE['lib']=library;server.STATE['retriever']=retriever
    server.ACCESS_TOKEN='';server.S1_SIGNING_KEY=''
    client=TestClient(server.app,client=('127.0.0.1',50000))
    def call(method,path,body=None):
        response=client.request(method,path,**({'json':body} if body is not None else {}));response.raise_for_status();return response.json()
    state=call('GET','/api/personal')
    assert all(v['verified'] for v in state['evidence_bindings'].values())
    topics=['重复样本','缺失值','数据类型','编码问题','异常值','字段一致性','跨组泄漏','格式转换','列名规范','数据合并','审计日志','清洗报告','数值范围','表格对齐','分组检查','原值保留']
    questions=[f'请在表格清理任务中处理{topic}，保留原始数据并生成可复核的交付文件。' for topic in topics]
    for q in questions:call('POST','/api/personal/feedback',dict(query=q,preferred='xlsx',rejected='data-cleaning'))
    trained=call('POST','/api/personal/train',{});assert trained['trained'] and trained['parameter_delta_l2']>0
    call('PUT','/api/personal/profile',dict(expected_version=0,patch=dict(active_personal_model=trained['model_id'])))
    familiar=call('POST','/api/personal/search',dict(query=questions[0],candidate_version='v2'))
    assert familiar['manual_personal_model_applied'] and familiar['candidate']['model']['model_id']==state['model_candidates']['v2']['model_id']
    assert not familiar['candidate']['stale_versions']
    q='如何核验 OAuth2 回调地址与 PKCE 授权码交换的安全边界？'
    unfamiliar=call('POST','/api/personal/search',dict(query=q,candidate_version='v2'))
    assert not unfamiliar['manual_personal_model_applied'] and not unfamiliar['personal_candidate']['within_support']
    call('PUT','/api/personal/profile',dict(expected_version=1,patch=dict(active_personal_model=None)))
    baseline=call('POST','/api/personal/search',dict(query=q,compare_candidate=False))
    assert [r['name'] for r in unfamiliar['selected']]==[r['name'] for r in baseline['selected']]
    current=call('GET','/api/personal');call('POST','/api/personal/rollback',dict(expected_version=current['profile']['version'],target_version=0))
    assert not call('GET','/api/personal')['profile']['active_personal_model']
    assert shared_before=={name:hashlib.sha256((ROOT/'data'/name/'model.npz').read_bytes()).hexdigest() for name in shared_before}
    assert library_before==hashlib.sha256(library_path.read_bytes()).hexdigest()
    report=dict(version='real-encoder-asgi-integration-v2',scope='Isolated ASGI routes using the actual frozen dense encoder and product catalog; not browser pixels or paid end-task execution',
        skills=len(library),encoder_revision=retriever.vec.status['revision'],candidate_evidence_bindings_valid=True,
        continuation_model_id=state['model_candidates']['v2']['model_id'],private_gradient_fit=True,
        familiar_question_applies_private_model=familiar['manual_personal_model_applied'],
        unrelated_question_applies_private_model=unfamiliar['manual_personal_model_applied'],
        unrelated_max_support_similarity=unfamiliar['personal_candidate']['max_support_similarity'],unrelated_ranking_preserved=True,
        history_rollback_verified=True,shared_model_and_catalog_bytes_unchanged=True,quality_rewards=0)
    report['report_sha256']=digest(report);(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
    client.close();print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
