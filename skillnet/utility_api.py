"""Read verified research evidence and rerun named public tasks only."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time

from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel,ConfigDict,Field

from . import conditional_utility as cu, conditional_boundary as cb, utility_ops, utility_oracle

BUNDLE = 'assets/conditional-utility/v1'
REQUIRED = {'protocol.json','model.json','selection.json','cases.json','report.json',
            'artifact-audit.json','strong-baselines.json','llm-report.json','admission.json','execution-evidence.zip'}


def _read(path: Path, maximum: int) -> bytes:
    from .frontier_ops import _linked
    if _linked(path.absolute()):raise ValueError('linked research files are not admissible')
    with path.open('rb') as f:raw=f.read(maximum+1)
    if len(raw)>maximum:raise ValueError('research file exceeds bound')
    return raw


def public_evidence(value,field=''):
    """Scrub transient host paths even when a Windows traceback is misdecoded."""
    if isinstance(value,dict):return {k:public_evidence(v,k) for k,v in value.items()}
    if isinstance(value,list):return [public_evidence(v,field) for v in value]
    if isinstance(value,str) and field in ('stderr','reason','detail','error'):
        value=re.sub(r'(?m)(File )"[^"\r\n]+"',r'\1"<registered-program>"',value)
        value=re.sub(r"[A-Za-z]:[\\/][^\r\n\"']*",'<workspace>',value)
    return value


def bundle(root: Path) -> dict:
    base=Path(root)/BUNDLE
    publication=json.loads(_read(base/'publication.json',1048576))
    if publication.get('digest')!=cu.digest({k:v for k,v in publication.items() if k!='digest'}):
        raise ValueError('publication digest mismatch')
    if not REQUIRED<=publication.get('files',{}).keys():raise ValueError('incomplete research delivery')
    result={'base':base,'publication':publication}
    for name in REQUIRED:
        meta=publication['files'][name];limit=32*1048576 if name.endswith('.zip') else 4*1048576
        raw=_read(base/name,limit)
        if meta.get('sha256')!=hashlib.sha256(raw).hexdigest() or meta.get('bytes')!=len(raw):
            raise ValueError('research file binding mismatch')
        if name.endswith('.json'):result[name[:-5]]=json.loads(raw)
    model,protocol=result['model'],result['protocol']
    cu.validate_model(model)
    protocol_sha=protocol.get('protocol_sha256')
    if protocol_sha!=cu.digest({k:v for k,v in protocol.items() if k!='protocol_sha256'}):raise ValueError('protocol mismatch')
    if model.get('operator_code_sha256')!=utility_ops.CODE_SHA or model.get('protocol_sha256')!=protocol_sha:
        raise ValueError('operator/model binding mismatch')
    for name,sha in protocol['code_sha256'].items():
        if name not in {'skillnet/conditional_utility.py','skillnet/utility_ops.py','skillnet/utility_oracle.py',
                        'tools/conditional_utility_lab.py','tools/conditional_llm_contrast.py'}:
            raise ValueError('unrecognized frozen code')
        if hashlib.sha256(_read(Path(root)/name,1048576)).hexdigest()!=sha:raise ValueError('frozen code changed')
    model_sha=cu.digest(model)
    for key in ('report','llm-report'):
        value=result[key]
        if value.get('report_sha256')!=cu.digest({k:v for k,v in value.items() if k!='report_sha256'}):
            raise ValueError('evidence digest mismatch')
        if value.get('model_sha256')!=model_sha or value.get('protocol_sha256')!=protocol_sha:
            raise ValueError('evidence references another model')
    if result['selection'].get('model_sha256')!=model_sha:raise ValueError('calibration references another model')
    if result['artifact-audit'].get('ok') is not True:raise ValueError('artifact audit failed')
    result.update(model_sha256=model_sha,protocol_sha256=protocol_sha)
    return result


def case_input(data,case_id):
    cases=[c for c in data['cases'] if c['split']=='sealed_test' and c['id']==case_id]
    if len(cases)!=1:raise HTTPException(422,'请选择已登记的公开任务')
    case=cases[0];path=case['path']
    if not re.fullmatch(r'inputs/[a-z0-9-]+\.csv',path):raise ValueError('invalid case path')
    raw=_read(data['base']/path,65536)
    if hashlib.sha256(raw).hexdigest()!=case['input_sha256']:raise ValueError('frozen input changed')
    threshold=data['selection']['minimum_quality']
    pred=cu.predict(data['model'],cu.features(raw,case['intent']),minimum_quality=threshold if threshold is not None else .75)
    if data['selection']['fallback_to_baseline']:
        pred.update(mask=7,abstain=False,reason='calibration_kept_baseline')
    return case,raw,pred


def boundary_bundle(root):
    base=Path(root)/'assets/conditional-utility/v2'
    pub=json.loads(_read(base/'publication.json',1048576))
    if pub.get('digest')!=cu.digest({k:v for k,v in pub.items() if k!='digest'}):raise ValueError('boundary publication mismatch')
    result={'base':base}
    for name in ('model.json','protocol.json','selection.json','cases.json','report.json','execution-evidence.zip','feature-rule-diagnostic.json'):
        raw=_read(base/name,32*1048576 if name.endswith('.zip') else 1048576);meta=pub['files'][name]
        if hashlib.sha256(raw).hexdigest()!=meta['sha256'] or len(raw)!=meta['bytes']:raise ValueError('boundary file changed')
        if name.endswith('.json'):result[name[:-5]]=json.loads(raw)
    p,m,r=result['protocol'],result['model'],result['report'];cb.validate(m)
    sha=p.get('protocol_sha256')
    if sha!=cu.digest({k:v for k,v in p.items() if k!='protocol_sha256'}):raise ValueError('boundary protocol mismatch')
    for name,expected in p['code_sha256'].items():
        if name not in ('skillnet/conditional_boundary.py','tools/conditional_boundary_lab.py'):raise ValueError('unknown boundary code')
        if hashlib.sha256(_read(Path(root)/name,1048576)).hexdigest()!=expected:raise ValueError('boundary code changed')
    if (r['report_sha256']!=cu.digest({k:v for k,v in r.items() if k!='report_sha256'})
            or r['model_sha256']!=cu.digest(m) or m['protocol_sha256']!=sha
            or r['protocol_sha256']!=sha or m['operator_code_sha256']!=utility_ops.CODE_SHA
            or result['selection']['model_sha256']!=cu.digest(m) or not r['artifact_audit']['ok']):
        raise ValueError('boundary evidence binding mismatch')
    d=result['feature-rule-diagnostic']
    if (d.get('defined_after_test') is not True or d.get('source_report_sha256')!=r['report_sha256']
            or d.get('report_sha256')!=cu.digest({k:v for k,v in d.items() if k!='report_sha256'})):
        raise ValueError('post-hoc diagnostic binding mismatch')
    return result


def boundary_case(data,case_id):
    cases=[c for c in data['cases'] if c['id']==case_id]
    if len(cases)!=1:raise HTTPException(422,'请选择已登记的第二轮公开任务')
    c=cases[0]
    if not re.fullmatch(r'inputs/iris-sealed-[0-9]{2}\.csv',c['path']):raise ValueError('invalid boundary path')
    raw=_read(data['base']/c['path'],65536)
    if hashlib.sha256(raw).hexdigest()!=c['input_sha256']:raise ValueError('boundary input changed')
    mask=sum(1<<j for j,k in enumerate(cu.KEYS) if c['intent'][k])
    p=cb.predict(data['model'],cb.observe(raw,c['intent'],mask),data['selection']['threshold'])
    base=cu.features(raw,c['intent']);f=base['features']
    before=not(base['supported_contract'] and not f['has_bad_test_number'] and f['has_test'] and not f['all_test_blank'])
    return c,raw,p,mask,before


class CaseRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case_id: str=Field(strict=True,min_length=1,max_length=80,pattern=r'^[a-z][a-z0-9-]*$')


class SemanticReplayRequest(CaseRequest):
    repeat:int=Field(default=0,strict=True,ge=0,le=1)


def make_router(root_provider,out_provider,require_token,slots_provider):
    router=APIRouter(prefix='/api/frontier/utility')
    from . import semantic_study
    def checked_semantic(version='v1'):
        try:return semantic_study.bundle(root_provider(),version)
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):
            raise HTTPException(503,'语义路由研究文件缺失或版本不一致，已停止实验') from None
    @router.get('/semantic')
    def semantic_report():
        b=checked_semantic();guard=checked_semantic('guard-v1')
        return JSONResponse({'report':b['report'],'guard_validation':guard['report'],
            'selection':b['selection'],'cases':[{'id':c['id'],'request':c['request'],'kind':c['kind']}
                for c in b['cases'] if c['split']=='sealed_test']},headers={'Cache-Control':'no-store'})
    @router.get('/semantic/evidence')
    def semantic_evidence():
        b=checked_semantic()
        return FileResponse(b['base']/'execution-evidence.zip',media_type='application/zip',
            filename='skillnet-semantic-routing-physical-evidence-v1.zip',headers={'Cache-Control':'no-store'})
    @router.post('/semantic/replay',dependencies=[Depends(require_token)])
    def semantic_replay(req:SemanticReplayRequest):
        b=checked_semantic();checked_semantic('guard-v1');slots=slots_provider()
        if not slots.acquire(blocking=False):raise HTTPException(429,'已有能力实验运行，请稍后重试',headers={'Retry-After':'2'})
        try:return JSONResponse(semantic_study.replay(b,req.case_id,out_provider(),req.repeat),headers={'Cache-Control':'no-store'})
        except semantic_study.UnknownCase:raise HTTPException(422,'请选择已登记的公开语义任务') from None
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):
            raise HTTPException(503,'语义实验未完成；未更新正式技能库与奖励') from None
        finally:slots.release()
    def checked():
        try:return bundle(root_provider())
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):
            raise HTTPException(503,'条件收益实验文件缺失或版本不一致，请核验完整交付') from None
    def checked_boundary():
        try:
            checked()  # The second study depends on the first frozen programs.
            return boundary_bundle(root_provider())
        except HTTPException:raise
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):
            raise HTTPException(503,'失败边界修正文件缺失或版本不一致，请核验完整交付') from None
    @router.get('/boundary')
    def boundary_report():
        b=checked_boundary();r=b['report']
        value={**r,'source_report_sha256':r['report_sha256'],'feature_rule_diagnostic':b['feature-rule-diagnostic']}
        value['report_sha256']=cu.digest({k:v for k,v in value.items() if k!='report_sha256'})
        return JSONResponse(value,headers={'Cache-Control':'no-store'})
    @router.get('/boundary/cases')
    def boundary_choices():
        b=checked_boundary()
        descriptions={'valid_measurements':'原始测量与受控清洗','blank_groups_removed_by_contract':'允许清除空值分组',
            'blank_groups_must_be_preserved':'保留空值分组，验证失败边界','bad_numeric':'非法数值边界',
            'unsupported_partition':'缺少 test 集合','unknown_goal':'未支持的目标','unknown_schema':'未支持的列结构'}
        return JSONResponse({'cases':[{'id':c['id'],'label':c['id']+' · '+descriptions[c['kind']]} for c in b['cases']]},headers={'Cache-Control':'no-store'})
    @router.get('/boundary/evidence')
    def boundary_evidence():
        b=checked_boundary()
        return FileResponse(b['base']/'execution-evidence.zip',media_type='application/zip',
            filename='skillnet-conditional-boundary-evidence-v2.zip',headers={'Cache-Control':'no-store'})
    @router.post('/boundary/predict',dependencies=[Depends(require_token)])
    def boundary_prediction(req:CaseRequest):
        b=checked_boundary()
        try:c,raw,p,mask,before=boundary_case(b,req.case_id)
        except (OSError,ValueError,TypeError,KeyError):raise HTTPException(503,'第二轮输入指纹不一致，已停止预测') from None
        return JSONResponse({'case':c,'input_csv':raw.decode('utf-8-sig'),'prediction':p,'created_at_ns':time.time_ns()},headers={'Cache-Control':'no-store'})
    @router.post('/boundary/execute',dependencies=[Depends(require_token)])
    def boundary_execute(req:CaseRequest):
        b=checked_boundary();slots=slots_provider()
        if not slots.acquire(blocking=False):raise HTTPException(429,'已有能力实验运行，请稍后重试',headers={'Retry-After':'2'})
        try:
            c,raw,p,mask,before=boundary_case(b,req.case_id);at=time.time_ns();results={}
            out=Path(out_provider());out.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='utility-api-',dir=out) as tmp:
                root=Path(tmp);source=root/'source.csv';source.write_bytes(raw)
                for arm,stop in [('baseline',before),('candidate',p['abstain']),('diagnostic',False)]:
                    if stop:
                        results[arm]={'state':'abstained','oracle':utility_oracle.evaluate(raw,c['intent'],None),'artifacts':{}}
                    else:
                        folder=root/arm;e=utility_ops.execute(mask,source,folder);o=utility_oracle.evaluate(raw,c['intent'],folder)
                        files={name:{**meta,'text':_read(folder/name,65536).decode('utf-8-sig')} for name,meta in e['artifacts'].items()}
                        results[arm]={'state':'verified' if o['deliverable'] else 'rejected','execution':e,'oracle':o,'artifacts':files}
            value={'case_id':c['id'],'prediction':p,'predicted_at_ns':at,'results':public_evidence(results),
                   'reward_applied':False,'formal_library_changed':False,'points':0}
            value['report_sha256']=cu.digest(value)
            return JSONResponse(value,headers={'Cache-Control':'no-store'})
        except HTTPException:raise
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):raise HTTPException(503,'第二轮实验未完成；未更新正式网络与奖励') from None
        finally:slots.release()
    @router.get('')
    def report():
        b=checked();summary={k:v for k,v in b['report']['summary'].items() if k!='pairs'}
        return JSONResponse({'version':cu.VERSION,'model_sha256':b['model_sha256'],'protocol_sha256':b['protocol_sha256'],
            'summary':summary,'strong_baselines':b['strong-baselines']['metrics'],
            'effect_distribution':b['strong-baselines']['effect_distribution'],'llm':b['llm-report']['summary'],
            'usage':b['llm-report']['usage'],'admission':b['admission'],'artifact_audit':b['artifact-audit'],
            'training_tasks':b['report']['training_tasks'],'calibration':b['selection'],
            'scope':b['report']['scope'],'limitations':b['report']['limitations'],
            'source_url':'https://github.com/allisonhorst/palmerpenguins','source_license':'CC0',
            'evidence_url':'/api/frontier/utility/evidence','formal_routing_deployed':False,'reward_applied':False},
            headers={'Cache-Control':'no-store'})
    @router.get('/cases')
    def choices():
        b=checked()
        return JSONResponse({'cases':[{k:c.get(k) for k in ('id','kind','boundary','intent')} for c in b['cases'] if c['split']=='sealed_test']},headers={'Cache-Control':'no-store'})
    @router.get('/evidence')
    def evidence():
        b=checked()
        return FileResponse(b['base']/'execution-evidence.zip',media_type='application/zip',
                            filename='skillnet-conditional-utility-evidence-v1.zip',headers={'Cache-Control':'no-store'})
    @router.post('/predict',dependencies=[Depends(require_token)])
    def prediction(req:CaseRequest):
        b=checked()
        try:case,raw,pred=case_input(b,req.case_id)
        except (OSError,ValueError,TypeError,KeyError):raise HTTPException(503,'公开输入指纹不一致，已停止预测') from None
        return JSONResponse({'case':case,'input_csv':raw.decode('utf-8-sig'),'prediction':pred,
                             'created_at_ns':time.time_ns()},headers={'Cache-Control':'no-store'})
    @router.post('/execute',dependencies=[Depends(require_token)])
    def execute(req:CaseRequest):
        b=checked();slots=slots_provider()
        if not slots.acquire(blocking=False):raise HTTPException(429,'已有能力实验运行，请稍后重试',headers={'Retry-After':'2'})
        try:
            case,raw,pred=case_input(b,req.case_id)
            pre_execution=time.time_ns();results={}
            out=Path(out_provider());out.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='utility-api-',dir=out) as tmp:
                root=Path(tmp);source=root/'source.csv';source.write_bytes(raw)
                for arm,mask in [('all',7),('conditional',pred['mask'])]:
                    if mask is None:
                        results[arm]={'state':'abstained','mask':None,'oracle':utility_oracle.evaluate(raw,case['intent'],None),'artifacts':{}}
                        continue
                    work=root/arm;execution=utility_ops.execute(mask,source,work)
                    oracle=utility_oracle.evaluate(raw,case['intent'],work)
                    artifacts={}
                    for name,meta in execution['artifacts'].items():
                        artifacts[name]={**meta,'text':_read(work/name,65536).decode('utf-8-sig')}
                    results[arm]={'state':'verified' if oracle['deliverable'] else 'rejected','mask':mask,
                                  'execution':execution,'oracle':oracle,'artifacts':artifacts}
            payload={'case_id':case['id'],'prediction':pred,'predicted_at_ns':pre_execution,'results':public_evidence(results),
                     'reward_applied':False,'formal_library_changed':False,'points':0,
                     'boundary':'有限公开任务实测；不能解释为全技能网络或生产 S1 的收益证明。'}
            payload['report_sha256']=cu.digest(payload)
            return JSONResponse(payload,headers={'Cache-Control':'no-store'})
        except HTTPException:raise
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):
            raise HTTPException(503,'公开实验未完成或证据不一致；未更新技能库和奖励') from None
        finally:slots.release()
    return router
