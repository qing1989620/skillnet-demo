"""Owned personal-network API; no client supplied identity, certificate or path."""
from __future__ import annotations
import json,threading
from pathlib import Path
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field
from . import config
from .learned_network import digest
from .personal_network import PersonalNetworkStore,Conflict
from .network_service import NetworkModelService,train_private_preference_candidate,preview_private_candidate

TRAIN_SLOT=threading.BoundedSemaphore(1)

class StrictBody(BaseModel):
    model_config=ConfigDict(extra='forbid')

class ProfileEdit(StrictBody):
    expected_version:int=Field(ge=0,strict=True)
    patch:dict

class PersonalSearch(StrictBody):
    query:str=Field(min_length=1,max_length=4000,pattern=r'\S')
    k:int=Field(default=5,ge=1,le=20)
    compare_candidate:bool=True
    candidate_version:Literal['v1','v2']='v1'

class Preference(StrictBody):
    query:str=Field(min_length=1,max_length=4000,pattern=r'\S')
    preferred:str=Field(min_length=1,max_length=128)
    rejected:str=Field(min_length=1,max_length=128)

class Rollback(StrictBody):
    expected_version:int=Field(ge=0,strict=True)
    target_version:int=Field(ge=0,strict=True)

def personal_store():
    return PersonalNetworkStore(config.OUT_DIR/'personal-network/private.sqlite3')

def model_service(version='v1'):
    folders={'v1':'network-model','v2':'network-model-v2'}
    if version not in folders:raise ValueError('Unknown installed research version')
    return NetworkModelService(config.DATA_DIR/folders[version])

def read_research_report(path):
    try:
        if path.stat().st_size>1024*1024:return None
        report=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(report,dict):return None
        claimed=report.pop('report_sha256',None)
        if not isinstance(claimed,str) or digest(report)!=claimed:return None
        return dict(**report,report_sha256=claimed)
    except (OSError,ValueError,TypeError):return None

def candidate_evidence(version):
    service=model_service(version)
    report=read_research_report(Path(__file__).resolve().parents[1]/f'docs/evidence/network-training-{version}.json')
    status=service.status();expected=(report or {}).get('model_id') or ((report or {}).get('admission') or {}).get('context',{}).get('model_id')
    binding=dict(model_id_matches=bool(expected and status['model_id']==expected),
        protocol_matches=bool(report and status['protocol_sha256']==report.get('protocol_sha256')))
    binding['verified']=bool(status['available'] and report and all(binding.values()))
    return service,report,binding

def make_router(get_lib,get_retriever,get_identity,require_token):
    router=APIRouter(prefix='/api/personal',tags=['personal-network'],dependencies=[Depends(require_token)])
    def owned(request):return get_identity(request)
    def known():return [s.name for s in get_lib().all()]
    def problem(e):
        raise HTTPException(409 if isinstance(e,Conflict) else 400,str(e)) from None

    @router.get('')
    def state(request:Request):
        context=owned(request);store=personal_store()
        evidence={v:candidate_evidence(v) for v in ['v1','v2']}
        reports={v:row[1] for v,row in evidence.items()};models={v:row[0].status() for v,row in evidence.items()}
        return dict(profile=store.profile(context),model=models['v1'],research=reports['v1'],
            candidates=store.candidates(context),history_versions=store.history_versions(context),
            personal_training_version='private-preference-training-v2',
            research_candidates=reports,model_candidates=models,evidence_bindings={v:row[2] for v,row in evidence.items()})

    @router.put('/profile')
    def edit(req:ProfileEdit,request:Request):
        try:return personal_store().update(owned(request),req.expected_version,req.patch,known())
        except ValueError as e:problem(e)

    @router.post('/rollback')
    def rollback(req:Rollback,request:Request):
        try:return personal_store().rollback(owned(request),req.expected_version,req.target_version,known())
        except ValueError as e:problem(e)

    @router.get('/graph')
    def graph(request:Request):return personal_store().graph(owned(request),get_lib())

    @router.get('/skill/{name}')
    def private_skill(name:str,request:Request):
        profile=personal_store().profile(owned(request))
        for row in profile['custom_skills']:
            if row['name']==name:return dict(**row,private=True,execution_verified=False)
        raise HTTPException(404,'个人技能不存在')

    @router.post('/search')
    def search(req:PersonalSearch,request:Request):
        context=owned(request);store=personal_store();retriever=get_retriever();library=get_lib()
        result=retriever.search(req.query,k=20,mode='hybrid',pool=50,rerank=False)
        rows=[dict(name=c.name,score=c.score,source=c.source,private=False) for c in result.candidates]
        profile=store.profile(context)
        private=profile['custom_skills']
        if private and getattr(retriever.vec,'status',{}).get('kind')=='dense-onnx':
            q=retriever.vec.embed([req.query],'query: ')[0]
            vecs=retriever.vec.embed([s['description']+' '+s['instructions'] for s in private],'passage: ')
            # Scores from fusion and cosine have different scales: keep private
            # reference candidates separate, rather than silently mixing them.
            private_rows=sorted([dict(name=s['name'],score=round(float(v@q),6),source='private',private=True,execution_verified=False) for s,v in zip(private,vecs)],key=lambda x:-x['score'])
        else:private_rows=[]
        picked=store.apply_preferences(context,rows)[:req.k]
        preview=None;candidate_error=None
        if req.compare_candidate:
            try:
                service,report,binding=candidate_evidence(req.candidate_version)
                if service.status()['available'] and not binding['verified']:raise ValueError('候选权重与研究报告的版本不一致，已停止本次模型对照')
                preview=service.preview(req.query,retriever.vec,library,req.k)
                preview.pop('query_features',None)
            except ValueError as e:candidate_error=str(e)
        personal_preview=None
        try:
            personal_preview=preview_private_candidate(store,context,retriever.vec,library,rows,req.query,config.OUT_DIR/'personal-network/models',profile['active_personal_model'],private_rows)
        except ValueError as e:personal_preview=dict(available=False,reason=str(e))
        manual_applied=bool(profile['active_personal_model'] and personal_preview and personal_preview.get('available') and personal_preview.get('within_support',False))
        if personal_preview:personal_preview['applied_to_personal_search']=manual_applied
        if manual_applied:picked=store.apply_preferences(context,personal_preview['ranking'])[:req.k]
        if personal_preview and personal_preview.get('ranking'):personal_preview['ranking']=personal_preview['ranking'][:req.k]
        recorded=store.observe(context,'query',req.query,dict(selected=[r['name'] for r in picked],label_kind='unlabeled_question',manual_personal_model=profile['active_personal_model'] if manual_applied else None))
        return dict(query=req.query,candidate_version=req.candidate_version,selected=picked,private_candidates=store.apply_preferences(context,private_rows)[:req.k],
            candidate=preview,candidate_error=candidate_error,personal_candidate=personal_preview,profile_version=profile['version'],observation=recorded,
            source='owner_selected_preference_adapter' if manual_applied else 'current_hybrid_with_explicit_owner_preferences',formal_model_weights_changed=False,
            manual_personal_model_applied=manual_applied,
            reason='个人偏好版本由你手动选择，只影响本页个人检索；共享权重与能力奖励仍受十二门约束')

    @router.post('/feedback')
    def feedback(req:Preference,request:Request):
        try:return personal_store().feedback(owned(request),req.query,req.preferred,req.rejected,known())
        except ValueError as e:problem(e)

    @router.post('/train')
    def train(req:StrictBody,request:Request):
        context=owned(request)
        if not TRAIN_SLOT.acquire(blocking=False):raise HTTPException(429,'已有个人模型正在训练，请稍后重试',headers={'Retry-After':'3'})
        try:
            return train_private_preference_candidate(personal_store(),context,get_retriever().vec,get_lib(),config.OUT_DIR/'personal-network/models')
        except ValueError as e:problem(e)
        finally:TRAIN_SLOT.release()

    @router.get('/observations')
    def observations(request:Request):return dict(rows=personal_store().observations(owned(request),100))

    @router.get('/export')
    def export(request:Request):
        context=owned(request);store=personal_store()
        return JSONResponse(dict(version='personal-network-export-v1',profile=store.profile(context),
            graph=store.graph(context,get_lib()),observations=store.observations(context,2000),candidates=store.candidates(context)),
            headers={'Content-Disposition':'attachment; filename="my-skill-network.json"','Cache-Control':'private, no-store'})
    return router
