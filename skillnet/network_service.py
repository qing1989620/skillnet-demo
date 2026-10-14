"""Read-only pretrained model preview and genuinely trained private preference drafts."""
from __future__ import annotations
from pathlib import Path
import hashlib,json,math,os,time,re,zipfile
import numpy as np
from .learned_network import NetworkAdapter,digest,normalize
from .personal_network import configuration_sha


class NetworkModelService:
    def __init__(self,directory: Path):
        self.directory=Path(directory);self.adapter=None;self.catalog=None;self.features=None;self.neighbours=None
        self.problem=''
        if not self.directory.exists():return
        try:
            self.adapter=NetworkAdapter.load(self.directory)
            if (self.directory/'catalog.json').stat().st_size>2*1024*1024:raise ValueError('Oversized model catalog manifest')
            self.catalog=json.loads((self.directory/'catalog.json').read_text(encoding='utf-8'))
            p=self.directory/'catalog.npz'
            if p.stat().st_size>24*1024*1024 or hashlib.sha256(p.read_bytes()).hexdigest()!=self.catalog['file_sha256']:raise ValueError('Trained catalog fingerprint mismatch')
            with zipfile.ZipFile(p) as archive:
                if sum(i.file_size for i in archive.infolist())>40*1024*1024:raise ValueError('Expanded catalog too large')
            with np.load(p,allow_pickle=False) as f:self.features=f['features'];self.neighbours=f['neighbours']
            n=len(self.catalog['names'])
            if self.features.shape!=(n,384) or self.neighbours.shape!=(n,4,384) or len(self.catalog['body_sha256'])!=n or len(set(self.catalog['names']))!=n:raise ValueError('Trained catalog shape mismatch')
            if not np.isfinite(self.features).all() or not np.isfinite(self.neighbours).all():raise ValueError('Nonfinite catalog features')
        except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as e:
            self.adapter=None;self.catalog=None;self.features=None;self.neighbours=None;self.problem=str(e)

    def status(self):
        m=self.adapter.metadata if self.adapter else {}
        return dict(available=self.adapter is not None,model_id=m.get('model_id'),
            stage='research_candidate_not_admitted' if self.adapter else 'unavailable',
            protocol_sha256=m.get('protocol_sha256'),
            trainable_parameters=m.get('trainable_parameters',0),dimension=384,
            active_trainable_parameters=m.get('active_trainable_parameters'),
            recommended_shadow_alpha=m.get('recommended_shadow_alpha'),
            graph_messages=bool(m.get('graph')),encoder=m.get('encoder'),
            scope='技能相关度表示与路由；不是会执行任务的通用语言模型',
            serving_weights_changed=False,rewards_applied=0,shadow_only=True,
            reason=self.problem or ('十二门准入未完成，正式排序保持原策略' if self.adapter else '本地没有安装候选模型'))

    def preview(self,query,encoder,library,k=10):
        if self.adapter is None:raise ValueError('No verified local candidate checkpoint')
        expected=self.adapter.metadata.get('encoder') or {}
        status=getattr(encoder,'status',{})
        if status.get('kind')!='dense-onnx' or status.get('revision')!=expected.get('revision'):raise ValueError('Candidate requires the exact frozen dense encoder')
        q=encoder.embed([query],'query: ')[0]
        rows=self.adapter.rank(q,self.features,self.catalog['names'],self.neighbours,k=min(len(self.catalog['names']),max(50,k)))
        allowed={s.name:s for s in library.all()};expected_sha=dict(zip(self.catalog['names'],self.catalog['body_sha256']));current=[];stale=[]
        for row in rows:
            skill=allowed.get(row['name'])
            if not skill:continue
            raw=(skill.reference_body() or skill.l2_text()).replace('\r\n','\n').strip()
            match=re.match(r'\A---\s*\n.*?\n---\s*\n(.*)',raw,re.S);body=match[1].strip() if match else raw
            if hashlib.sha256(body.encode()).hexdigest()!=expected_sha[row['name']]:stale.append(row['name']);continue
            current.append(row)
        rows=current[:k]
        return dict(model=self.status(),ranking=rows,query_features=q,
            score_kind='learned_relevance_not_success_probability',applied_to_formal_router=False,stale_versions=stale)


def train_private_preference_candidate(store,identity,encoder,library,output_root: Path):
    """Fit a small residual from explicit A>B labels. Never deploy / award it.

    Questions, clicks and single-run success are not positive skill labels.
    A deterministic split is frozen before fitting; tiny data is reported as
    insufficient, and no held-out result is recycled into optimizer updates.
    """
    profile=store.profile(identity)
    if not profile['enabled']:raise ValueError('Personal learning is disabled')
    if getattr(encoder,'status',{}).get('kind')!='dense-onnx':raise ValueError('Exact dense encoder is required for preference training')
    known={s.name:s for s in library.all()};private={s['name']:s for s in profile['custom_skills']}
    all_rows=store.observations(identity,2000)
    pairs={}
    for row in reversed(all_rows):
        if row['kind']=='preference_pair' and row.get('preferred') in known.keys()|private.keys() and row.get('rejected') in known.keys()|private.keys():
            pairs[(row['query_sha256'],*sorted([row['preferred'],row['rejected']]))]=row
    # Unlabelled questions must not crowd explicit preferences out of the fit.
    rows=sorted(pairs.values(),key=lambda r:(r['created'],r['id']))[-200:]
    protocol=dict(version='private-preference-training-v2',profile_version=profile['version'],
        profile_config_sha256=configuration_sha(profile),
        data_sha256=digest([{k:r[k] for k in ['id','query_sha256','preferred','rejected']} for r in rows]),
        label_kind='owner_explicit_pair_preference',epochs=120,learning_rate=.08,rank=8,
        max_explicit_pairs=200,pair_selection='latest explicit preference for each query/unordered pair; newest 200 eligible pairs',
        scope_min_cosine=.88,scope_reference='unique explicit training questions only; holdout questions excluded',
        outside_scope_action='use current personal search, without applying the preference adapter',
        preference_temperature=.1,residual_strength=.25,max_up_norm=4.,
        split='query SHA256 modulo 5: zero is holdout; repeated query stays in one partition',
        global_weights_frozen=True,quality_reward=False,
        encoder_revision=encoder.status.get('revision'))
    # Freeze the actual representations used for labels. A shared skill may
    # change without changing this owner's configuration version.
    protocol['label_text_sha256']={name:hashlib.sha256(known[name].l2_text().encode()).hexdigest()
        for name in sorted({r[key] for r in rows for key in ['preferred','rejected']} & known.keys())}
    if len(rows)<2:
        return store.save_candidate(identity,dict(stage='shadow',deployed=False,reward=0,
            trained=False,protocol=protocol,examples=len(rows),reason='至少需要两组明确的 A 优于 B 偏好；提问或点击不作为训练标签',gate=dict(eligible=False,passed=0,total=12,blockers=['insufficient_explicit_preferences'])))
    texts={}
    for r in rows:
        for n in [r['preferred'],r['rejected']]:
            texts[n]=known[n].l2_text() if n in known else private[n]['description']+' '+private[n]['instructions']
    names=sorted(texts);by={n:i for i,n in enumerate(names)}
    S=encoder.embed([texts[n][:5000] for n in names],'passage: ')
    Q=encoder.embed([r['query'] for r in rows],'query: ')
    diff=np.stack([S[by[r['preferred']]]-S[by[r['rejected']]] for r in rows])
    hold=np.array([int(r['query_sha256'][:8],16)%5==0 for r in rows]);train=np.where(~hold)[0];test=np.where(hold)[0]
    support_indices=list({rows[i]['query_sha256']:int(i) for i in train}.values())
    if len(support_indices)<2:raise ValueError('至少需要两道不同问题的明确偏好；固定留出样本不能挪入训练')
    query_support=Q[support_indices].astype(np.float32)
    protocol['scope_training_targets']=[sorted({r[key] for i,r in enumerate(rows) if i in train and r['query_sha256']==rows[j]['query_sha256'] for key in ['preferred','rejected']}) for j in support_indices]
    protocol['max_extra_supported_candidates']=40
    rng=np.random.default_rng(17);down=rng.normal(0,1/math.sqrt(8),(384,8)).astype(np.float32);up=np.zeros((8,384),np.float32)
    projected=Q@down;trace=[];started=time.monotonic()
    for step in range(protocol['epochs']):
        adjusted=Q[train]+.25*(projected[train]@up);margin=np.sum(adjusted*diff[train],axis=1)/.1
        scale=-1/(1+np.exp(np.clip(margin,-40,40)))
        gradient=2.5*(projected[train].T@(scale[:,None]*diff[train]))/len(train)+.02*up
        up-=protocol['learning_rate']*gradient
        norm=float(np.linalg.norm(up))
        if norm>4:up*=4/norm
        trace.append(float(np.logaddexp(0,-margin).mean()))
    assert np.isfinite(up).all()
    changed=float(np.linalg.norm(up))
    identity_sha=digest(identity);model_key=digest(protocol)[:24];directory=Path(output_root)/identity_sha/model_key;directory.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(directory/'model.npz',down=down,up=up,query_support=query_support)
    weights_sha=hashlib.sha256((directory/'model.npz').read_bytes()).hexdigest()
    before=np.sum(Q*diff,1);adapted=np.sum(normalize(Q+.25*(projected@up))*diff,1)
    support_similarity=np.max(Q@query_support.T,axis=1);within=support_similarity>=protocol['scope_min_cosine']
    after=np.where(within,adapted,before)
    result=dict(stage='shadow',deployed=False,reward=0,trained=True,protocol=protocol,
        examples=len(rows),train_queries=len({rows[i]['query_sha256'] for i in train}),holdout_queries=len({rows[i]['query_sha256'] for i in test}),
        loss_before=trace[0],loss_after=trace[-1],parameter_delta_l2=changed,
        weights_sha256=weights_sha,training_seconds=round(time.monotonic()-started,4),
        holdout_preference_accuracy_before=float((before[test]>0).mean()) if len(test) else None,
        holdout_preference_accuracy_after=float((after[test]>0).mean()) if len(test) else None,
        scope_min_cosine=protocol['scope_min_cosine'],support_questions=len(query_support),
        holdout_scope_coverage=float(within[test].mean()) if len(test) else None,
        reason='个人偏好候选已真实训练；没有能力增益准入证书，保持影子预览',
        gate=dict(eligible=False,passed=0,total=12,blockers=['no_complete_preregistered_paired_admission','preference_labels_are_not_capability_rewards']))
    (directory/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    (directory/'training-curve.json').write_text(json.dumps(trace),encoding='utf-8')
    (directory/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return store.save_candidate(identity,result)


def preview_private_candidate(store,identity,encoder,library,ranking,query,output_root,model_id=None,private_ranking=None):
    candidates=[c for c in store.candidates(identity) if c.get('trained')]
    if model_id:
        chosen=store.candidate(identity,model_id);candidates=[chosen] if chosen and chosen.get('trained') else []
    if not candidates:return None
    report=candidates[0];protocol=report['protocol'];profile=store.profile(identity)
    if protocol.get('version')!='private-preference-training-v2':return dict(available=False,model_id=report['model_id'],reason='旧个人候选没有作用范围检查，请重新训练；已保留旧版本')
    if protocol.get('profile_config_sha256')!=configuration_sha(profile):return dict(available=False,reason='个人配置已经变化；旧候选未被应用，请重新训练')
    if protocol.get('encoder_revision')!=getattr(encoder,'status',{}).get('revision'):return dict(available=False,reason='编码器版本已变化')
    known={s.name:s for s in library.all()};private={s['name']:s for s in profile['custom_skills']}
    for name,sha in protocol.get('label_text_sha256',{}).items():
        if name not in known or hashlib.sha256(known[name].l2_text().encode()).hexdigest()!=sha:
            return dict(available=False,reason='训练偏好所用技能正文已经变化，请重新训练')
    directory=Path(output_root)/digest(identity)/digest(protocol)[:24];p=directory/'model.npz'
    if not p.is_file() or p.stat().st_size>512*1024 or hashlib.sha256(p.read_bytes()).hexdigest()!=report['weights_sha256']:raise ValueError('Private checkpoint integrity failed')
    with zipfile.ZipFile(p) as archive:
        if sum(i.file_size for i in archive.infolist())>512*1024:raise ValueError('Expanded private checkpoint too large')
    with np.load(p,allow_pickle=False) as z:
        if set(z.files)!={'down','up','query_support'}:raise ValueError('Invalid private checkpoint fields')
        down,up,query_support=z['down'],z['up'],z['query_support']
    if down.shape!=(384,8) or up.shape!=(8,384) or not np.isfinite(down).all() or not np.isfinite(up).all():raise ValueError('Invalid private checkpoint shape')
    if query_support.ndim!=2 or not 2<=len(query_support)<=200 or query_support.shape[1]!=384 or not np.isfinite(query_support).all():raise ValueError('Invalid private question support')
    q=encoder.embed([query],'query: ')[0];support_scores=query_support@q;max_similarity=float(np.max(support_scores))
    minimum=protocol.get('scope_min_cosine')
    if minimum!=.88:raise ValueError('Unsupported private scope policy')
    if max_similarity<minimum:
        return dict(available=True,model_id=report['model_id'],within_support=False,max_support_similarity=round(max_similarity,6),scope_min_cosine=minimum,
            ranking=list(ranking),applied=False,score_kind='current_personal_search_outside_learned_scope',
            reason='这个问题超出已标注偏好的相似范围，本次沿用原个人检索；这项相似度检查不是能力成功率保证')
    names=list(dict.fromkeys(r['name'] for r in [*ranking,*(private_ranking or [])] if r['name'] in known or r['name'] in private))
    targets=protocol.get('scope_training_targets',[])
    if targets:
        if len(targets)!=len(query_support):raise ValueError('Invalid private support target mapping')
        added=0
        for index in np.argsort(-support_scores,kind='stable')[:3]:
            if support_scores[index]<minimum:continue
            for name in targets[index]:
                if added>=40:break
                if name not in names and (name in known or name in private):names.append(name);added+=1
    if not names:return dict(available=True,model_id=report['model_id'],ranking=[],applied=False)
    texts=[known[n].l2_text() if n in known else private[n]['description']+' '+private[n]['instructions'] for n in names]
    s=encoder.embed([text[:5000] for text in texts],'passage: ')
    scores=s@normalize(q+.25*((q@down)@up));order=np.argsort(-scores,kind='stable')
    return dict(available=True,model_id=report['model_id'],within_support=True,max_support_similarity=round(max_similarity,6),scope_min_cosine=minimum,ranking=[dict(name=names[i],score=round(float(scores[i]),6),private=names[i] in private,
        source='owner_preference_adapter',execution_verified=False) for i in order],applied=False,score_kind='learned_owner_preference_not_execution_success')
