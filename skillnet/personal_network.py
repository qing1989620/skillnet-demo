"""Private user/project skill networks and an evidence-first experience ledger.

Settings express the owner's intent. Observations and explicit pair preferences
are different data types; neither can award shared skills or deploy a model.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib,json,math,re,sqlite3,time,uuid
from pathlib import Path
from .learned_network import digest

DEFAULTS = dict(enabled=True, pinned=[], disabled=[], custom_skills=[], edges=[],
    learning_mode='shadow', retention=1000, active_personal_model=None)
RELATIONS = {'depend_on','compose_with','similar_to'}


def scope_key(identity):
    if not isinstance(identity,dict) or set(identity)!={'tenant','user','project'}:
        raise ValueError('A verified user/project context is required')
    if any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',v) for v in identity.values()):
        raise ValueError('Invalid identity')
    return digest(identity)


class Conflict(ValueError): pass

def configuration_sha(profile):
    return digest({k:profile[k] for k in ['pinned','disabled','custom_skills','edges']})


class PersonalNetworkStore:
    def __init__(self,path: Path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.db() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS profiles(
                scope TEXT PRIMARY KEY, version INTEGER NOT NULL, body TEXT NOT NULL, updated REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS observations(
                scope TEXT NOT NULL, id TEXT NOT NULL, kind TEXT NOT NULL, query_sha TEXT NOT NULL,
                body TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(scope,id));
              CREATE INDEX IF NOT EXISTS observations_scope ON observations(scope,created);
              CREATE TABLE IF NOT EXISTS history(
                scope TEXT NOT NULL, version INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(scope,version));
              CREATE TABLE IF NOT EXISTS models(
                scope TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(scope,id));''')

    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        c.execute('PRAGMA busy_timeout=15000');c.row_factory=sqlite3.Row
        try:yield c
        finally:c.close()

    @staticmethod
    def _get(c,key):
        row=c.execute('SELECT version,body FROM profiles WHERE scope=?',(key,)).fetchone()
        if row:return dict(version=row['version'],**json.loads(row['body']))
        return dict(version=0,**json.loads(json.dumps(DEFAULTS)))

    def profile(self,identity):
        key=scope_key(identity)
        with self.db() as c:
            value=self._get(c,key)
            counts={r['kind']:r['n'] for r in c.execute('SELECT kind,count(*) AS n FROM observations WHERE scope=? GROUP BY kind',(key,))}
            distinct=c.execute('SELECT count(DISTINCT query_sha) FROM observations WHERE scope=?',(key,)).fetchone()[0]
        return dict(**value,identity=identity,observations=counts,distinct_queries=distinct,
            isolation='tenant/user/project',weight_updates=0,rewards_applied=0,
            learning_boundary='提问只留下待标注经验；点击不等于成功；明确偏好与技能提升奖励分开处理')

    def update(self,identity,expected_version,patch,known_skills):
        key=scope_key(identity)
        allowed=set(DEFAULTS)
        if not isinstance(patch,dict) or set(patch)-allowed:raise ValueError('Unknown profile setting')
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                current=self._get(c,key)
                if current['version']!=expected_version:raise Conflict('Profile changed; reload before editing')
                version=current.pop('version');value={**current,**patch}
                if configuration_sha(value)!=configuration_sha(current) and 'active_personal_model' not in patch:
                    value['active_personal_model']=None
                self._validate(value,set(known_skills))
                active=value['active_personal_model']
                if active:
                    model=c.execute('SELECT body FROM models WHERE scope=? AND id=?',(key,active)).fetchone()
                    if not model:raise ValueError('Preference candidate does not exist in this private scope')
                    report=json.loads(model['body'])
                    if not report.get('trained') or report['protocol'].get('profile_config_sha256')!=configuration_sha(value):
                        raise ValueError('Preference candidate is untrained or belongs to an older configuration')
                raw=json.dumps(value,ensure_ascii=False,allow_nan=False)
                if len(raw.encode('utf-8'))>100000:raise ValueError('Personal configuration exceeds the 100 KB limit')
                c.execute('INSERT INTO history VALUES(?,?,?)',(key,version,json.dumps(current,ensure_ascii=False)))
                c.execute('INSERT OR REPLACE INTO profiles VALUES(?,?,?,?)',(key,version+1,raw,time.time()))
                c.execute('COMMIT')
            except Exception:c.execute('ROLLBACK');raise
        return self.profile(identity)

    @staticmethod
    def _validate(value,known):
        if type(value['enabled']) is not bool or value['learning_mode']!='shadow':raise ValueError('Only shadow learning is currently admitted')
        active=value['active_personal_model']
        if active is not None and (not isinstance(active,str) or not re.fullmatch(r'personal-[a-f0-9]{20}',active)):raise ValueError('Invalid private preference model id')
        if type(value['retention']) is not int or not 100<=value['retention']<=2000:raise ValueError('Retention must be 100..2000')
        custom=value['custom_skills']
        if not isinstance(custom,list) or len(custom)>40:raise ValueError('At most 40 private skills')
        private=set()
        for s in custom:
            if not isinstance(s,dict) or set(s)!={'name','description','instructions'}:raise ValueError('Invalid private skill fields')
            if not isinstance(s['name'],str) or not re.fullmatch(r'personal-[a-z0-9]+(?:-[a-z0-9]+)*',s['name']) or len(s['name'])>64:raise ValueError('Private skill names must start personal-')
            if s['name'] in private or s['name'] in known:raise ValueError('Duplicate skill name')
            if any(not isinstance(s[k],str) or not 1<=len(s[k])<=limit for k,limit in [('description',1000),('instructions',16000)]):raise ValueError('Private skill text is empty or too long')
            private.add(s['name'])
        valid=known|private
        for key in ['pinned','disabled']:
            xs=value[key]
            if not isinstance(xs,list) or len(xs)>100 or any(not isinstance(x,str) or x not in valid for x in xs) or len(set(xs))!=len(xs):raise ValueError('Unknown / duplicate configured skill')
        if set(value['pinned'])&set(value['disabled']):raise ValueError('A skill cannot be pinned and disabled together')
        edges=value['edges']
        if not isinstance(edges,list) or len(edges)>120:raise ValueError('Too many private edges')
        seen=set();requires={x:[] for x in valid}
        for e in edges:
            if not isinstance(e,dict) or set(e)!={'source','target','type'}:raise ValueError('Invalid private edge')
            a,b,r=e['source'],e['target'],e['type']
            if a not in valid or b not in valid or a==b or r not in RELATIONS or (a,b,r) in seen:raise ValueError('Unknown, repeated or self-referencing edge')
            seen.add((a,b,r))
            if r=='depend_on':requires[a].append(b)
        visited=set();active=set()
        def visit(n):
            if n in active:raise ValueError('Private dependency graph contains a cycle')
            if n in visited:return
            active.add(n)
            for nxt in requires[n]:visit(nxt)
            active.remove(n);visited.add(n)
        for n in requires:visit(n)

    def rollback(self,identity,expected_version,target_version,known):
        key=scope_key(identity)
        with self.db() as c:row=c.execute('SELECT body FROM history WHERE scope=? AND version=?',(key,target_version)).fetchone()
        if not row:raise ValueError('Profile version does not exist in this scope')
        return self.update(identity,expected_version,json.loads(row['body']),known)

    def observe(self,identity,kind,query,body,*,event_id=None):
        if kind not in {'query','run_observation','preference_pair'} or not isinstance(query,str) or not query.strip() or len(query)>6000:raise ValueError('Invalid observation')
        key=scope_key(identity);query=query.strip();sha=hashlib.sha256(query.encode()).hexdigest()
        payload=dict(body,query=query,query_sha256=sha,quality_label=None,reward=0)
        encoded=json.dumps(payload,ensure_ascii=False,allow_nan=False)
        if len(encoded)>32000:raise ValueError('Observation too large')
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            try:
                profile=self._get(c,key)
                if not profile['enabled']:c.execute('ROLLBACK');return dict(recorded=False,reason='personal_learning_disabled')
                token=event_id or uuid.uuid4().hex
                added=c.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?,?,?,?)',(key,token,kind,sha,encoded,time.time())).rowcount
                c.execute('DELETE FROM observations WHERE scope=? AND id NOT IN (SELECT id FROM observations WHERE scope=? ORDER BY created DESC,id DESC LIMIT ?)',(key,key,profile['retention']))
                c.execute('COMMIT')
            except Exception:c.execute('ROLLBACK');raise
        return dict(recorded=bool(added),id=token,query_sha256=sha,quality_label=None,reward=0)

    def feedback(self,identity,query,preferred,rejected,known):
        profile=self.profile(identity);valid=set(known)|{x['name'] for x in profile['custom_skills']}
        if preferred==rejected or preferred not in valid or rejected not in valid:raise ValueError('Choose two different known skills')
        return self.observe(identity,'preference_pair',query,dict(preferred=preferred,rejected=rejected,
            label_kind='owner_explicit_pair_preference',execution_quality_claim=False))

    def observations(self,identity,limit=100):
        key=scope_key(identity)
        with self.db() as c:
            rows=c.execute('SELECT id,kind,body,created FROM observations WHERE scope=? ORDER BY created DESC,id DESC LIMIT ?',(key,min(2000,max(1,limit)))).fetchall()
        return [dict(id=r['id'],kind=r['kind'],created=r['created'],**json.loads(r['body'])) for r in rows]

    def graph(self,identity,library):
        profile=self.profile(identity);pinned=set(profile['pinned']);disabled=set(profile['disabled'])
        nodes=[dict(id=s.name,domain=s.domain,source=s.source,pinned=s.name in pinned,disabled=s.name in disabled,private=False) for s in library.all()]
        nodes.extend(dict(id=s['name'],domain='我的方法',source='private',pinned=s['name'] in pinned,disabled=s['name'] in disabled,private=True,description=s['description']) for s in profile['custom_skills'])
        edges=[{**e,'private':False,'evidence_kind':'catalog_declaration'} for e in library.relation_edges()]
        edges.extend({**e,'private':True,'evidence_kind':'owner_defined_not_causally_verified'} for e in profile['edges'])
        return dict(nodes=nodes,edges=edges,profile_version=profile['version'],identity=identity,
            relation_boundary='用户关系是个人编排意图，不能作为已验证的因果效果')

    def apply_preferences(self,identity,ranking):
        profile=self.profile(identity)
        disabled=set(profile['disabled']);pins=set(profile['pinned'])
        kept=[dict(x) for x in ranking if x['name'] not in disabled]
        kept.sort(key=lambda x:x['name'] not in pins)  # Stable, explicit owner intent.
        return kept

    def save_candidate(self,identity,report):
        key=scope_key(identity)
        if report.get('stage')!='shadow' or report.get('deployed') is not False or report.get('reward')!=0:raise ValueError('An observation cannot deploy or award a model')
        model_id='personal-'+digest(report)[:20]
        with self.db() as c:c.execute('INSERT OR IGNORE INTO models VALUES(?,?,?,?)',(key,model_id,json.dumps(report,ensure_ascii=False,allow_nan=False),time.time()))
        return dict(model_id=model_id,**report)

    def candidates(self,identity):
        key=scope_key(identity)
        with self.db() as c:rows=c.execute('SELECT id,body FROM models WHERE scope=? ORDER BY created DESC LIMIT 20',(key,)).fetchall()
        return [dict(model_id=r['id'],**json.loads(r['body'])) for r in rows]

    def candidate(self,identity,model_id):
        key=scope_key(identity)
        with self.db() as c:row=c.execute('SELECT body FROM models WHERE scope=? AND id=?',(key,model_id)).fetchone()
        return dict(model_id=model_id,**json.loads(row['body'])) if row else None
