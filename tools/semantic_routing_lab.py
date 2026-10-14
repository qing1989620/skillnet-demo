"""Freeze natural-language tasks, train only on development, run paired APIs.

The hidden task contract is used only by the independent file evaluator. All
arms get the same natural request, CSV, registered operators and output budget.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import httpx
import numpy as np
from skillnet import config, semantic_routing as sr, utility_ops, utility_oracle
from skillnet.semantic import DenseIndex

ARMS = ['plain', 'retrieved_examples', 'trained_hint']
CODE = ['skillnet/semantic_routing.py', 'tools/semantic_routing_lab.py',
        'skillnet/utility_ops.py', 'skillnet/utility_oracle.py', 'skillnet/semantic.py']
SYSTEM = '''你是表格任务的技能选择器。根据自然语言需求和真实 CSV 选择登记程序。
共同执行器依次应用以下位开关，最后按 group 汇总 split=test 的 n_rows、n_numeric、sum、mean。
bit1：同 sample_id 只保留首次。bit2：在前一步结果中，删除出现在多个 split 的 subject 的所有记录。
bit4：删除 value 为空白的行。mask 是这些 bit 之和；0 表示直接汇总。保留其余原单元格。
空值不参与数值均值，但未删的空行仍计入 n_rows。每个保留 test group 必须含有限数值；不允许非数值。
不能擅自替换用户清洗口径。三项策略有未明确或矛盾、要求其他操作/统计、没有 test 行或数据无法完成要求时拒绝并等待澄清。
只能输出 JSON：{"mask":0到7的整数,"reject":false} 或 {"mask":null,"reject":true}。
附加的检索示例或训练提示可能错误，不能覆盖用户需求与原始数据。'''


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(raw): return hashlib.sha256(raw).hexdigest()
def contract(mask):
    return dict(zip(utility_oracle.KEYS, [bool(mask & (1 << j)) for j in range(3)]), goal='group_mean')


def prepare(work):
    if work.exists(): raise ValueError('fresh experiment directory required')
    work.mkdir(parents=True)
    url = 'https://archive.ics.uci.edu/static/public/109/wine.zip'
    raw = urllib.request.urlopen(url, timeout=40).read(200001)
    if len(raw) > 200000: raise ValueError('source limit')
    (work/'wine.zip').write_bytes(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        original = z.read('wine.data'); (work/'wine.data').write_bytes(original)
    wine = list(csv.reader(io.StringIO(original.decode())))
    clauses = [
        (['同 sample_id 只留第一条。', '相同样本键保留最先出现的记录。', '按样本编号去重，首次优先。'],
         ['重复样本也全部保留。', '不要合并相同样本键的行。', '重复 sample_id 按原样保留。']),
        (['剔除所有跨 split 的 subject。', '同一受试实体同时出现在不同集合时，删除它的全部行。', '排除在训练和测试集合都有记录的对象。'],
         ['跨 split 的 subject 仍然保留。', '不剔除跨集合对象。', '即便一个实体出现在不同 split，也不删它。']),
        (['删除 value 空白行。', '缺失测量值的行不要留下。', '清除 value 未填写的记录。'],
         ['保留 value 空白行。', '缺失值的行也要计入行数。', 'value 未填的记录按原样保留。'])]
    cases = []
    def add(split, name, text, label, kind='valid', mutation=None):
        # Training values are synthetic. The complete Wine source is held out.
        rows = []
        for i in range(12):
            v = wine[(len(cases)*7+i) % len(wine)] if split == 'sealed_test' else ['1', str(10+i/7)]
            rows.append([name+'-'+str(i), name+'-person-'+str(i), 'train' if i<3 else 'test',
                         'G'+str(i % 3), v[1]])
        rows.append([*rows[-1][:-1], '99.1'])
        rows.append([name+'-cross',rows[0][1],'test','G1','12.34'])
        rows.append([name+'-blank',name+'-blank-person','test','G2',''])
        if mutation=='no_test':
            for r in rows: r[2]='train'
        if mutation=='blank_group': rows.append([name+'-empty',name+'-empty-person','test','EMPTY',''])
        if mutation=='bad_number': rows.append([name+'-bad',name+'-bad-person','test','G1','not-a-number'])
        buf=io.StringIO(newline='');w=csv.writer(buf,lineterminator='\n');w.writerow(utility_ops.HEADER);w.writerows(rows)
        data=buf.getvalue().encode();path='inputs/'+name+'.csv';(work/'inputs').mkdir(exist_ok=True);(work/path).write_bytes(data)
        cases.append({'id':name,'split':split,'request':text,'label':label,'kind':kind,'path':path,
                      'input_sha256':sha(data),'intent':contract(label if label<8 else 0),
                      'expect_reject':label==8,'source':'wine_alcohol_with_controlled_transforms' if split=='sealed_test' else 'synthetic'})
    for split,n in [('train',10),('calibration',2)]:
        for m in range(8):
            for j in range(n):
                parts=[clauses[k][0 if m & (1<<k) else 1][(j+k)%3] for k in range(3)]
                text=f'请按 test 的 group 计算行数、数值数、和与均值。'+''.join(parts)+f'这是{split}第{j+1}组要求，请保持其他单元格。'
                add(split,f'{split}-{m}-{j}',text,m)
    reject_train=[
        '帮我把这张表清洗好再算均值，清洗细节由你定。','汇总各组均值，我还没决定重复记录怎么处理。',
        '重复键保留最后出现的记录，其他不变。','缺失值用均值填补，再汇总。',
        '我要每组中位数，不要均值。','把相同键合并，同时必须保留每一行。',
        '计算训练集的汇总，忽略 test。','先按所有列去重，再用全表算均值。',
        '去重保留第一次，但重复样本全部不能删，跨组对象和空行不处理。','只需要绘制散点图，无须统计表。']
    for j,t in enumerate(reject_train): add('train',f'train-reject-{j}',t,8,'clarification')
    for j,t in enumerate(['请整理数据后汇总，暂时不确定删哪些行。','样本相同留最新一行，空值填零。']):
        add('calibration',f'calibration-reject-{j}',t,8,'clarification')
    # Hand-authored held-out language. No correct switches are passed to an arm.
    yes=[['一个样本多次登记时，只认它第一次登记的那行。','每个样本键只有第一次有效，后面的重复登记作废。'],
         ['只要对象在两种 split 下都出现过，就把该对象整个移出。','同一 subject 跨集合出现意味着污染，其所有记录一律排除。'],
         ['没有填写测量值的记录应从结果表中消失。','value 空着的行也请移走。']]
    no=[['一个样本多次登记是独立重复，所有登记都应留下。','每次重复登记都有效，不能因为样本键相同删行。'],
        ['对象跨集合出现是本次设计的一部分，不要因此移出它。','subject 同时跨集合出现也合规，其记录不能排除。'],
        ['没有测量值的行仍须留在结果表，计入总行数而非数值数。','value 空着的行仍要保留，汇总均值时自然略过空值。']]
    for m in range(8):
        for j in range(2):
            text='请给出 test 集合中每个 group 的行数、有效数值数、数值和及均值。'+''.join((yes if m&(1<<k) else no)[k][j] for k in range(3))+'其余单元格照原样，依样本、对象、空值顺序处理。'
            add('sealed_test',f'wine-sealed-{m}-{j}',text,m)
    boundary=[
        ('你看着清理一下，按 test 中的 group 交付计数、和及均值。', 'clarification',None),
        ('重复 sample_id 仅取第一条，同时所有重复行都必须完整保留；跨 split 的对象保留，空行也保留。给出 test 分组均值。','contradiction',None),
        ('同 sample_id 留最后一条，不排除跨 split 对象，不删空值行，再按 test 分组汇总行数、有效数、和及均值。','unsupported_operation',None),
        ('保留重复样本，保留跨集合实体，把空值填 0 后按 test 的 group 汇总行数、有效数、和及均值。','unsupported_operation',None),
        ('所有行原样保留，按 test 中的 group 汇总行数、有效数、和及均值。','no_test','no_test'),
        ('重复键、跨集合对象和空值行一律保留，按 test 分组给出行数、有效数、和及均值。','blank_group','blank_group'),
        ('不删重复键、不排跨集合实体、不删空行，保持原始单元格，按 test 分组统计行数、有效数、和及均值。','bad_number','bad_number'),
        ('不做任何清洗，给出 test 每组行数、有效数、和及中位数，不要均值。','unsupported_goal',None)]
    for j,(t,k,mut) in enumerate(boundary): add('sealed_test',f'wine-boundary-{j}',t,8,k,mut)
    if len({sha(c['request'].encode()) for c in cases})!=len(cases): raise ValueError('duplicate requests')
    save(work/'cases.json',cases)
    protocol={'version':sr.VERSION,'created_at_ns':time.time_ns(),'cases_sha256':sha((work/'cases.json').read_bytes()),
        'code_sha256':{p:sha((ROOT/p).read_bytes()) for p in CODE},
        'source':{'url':url,'page':'https://archive.ics.uci.edu/dataset/109/wine','license':'CC BY 4.0',
                  'zip_sha256':sha(raw),'data_sha256':sha(original),'measurement':'alcohol (second column)',
                  'warning':'IDs, splits, groups and defects are controlled transforms; shared Wine rows are not independent domains.'},
        'encoder':{'repository':'Xenova/multilingual-e5-small','revision':'761b726dd34fb83930e26aab4e9ac3899aa1fa78'},
        'training':{'alpha_grid':[.01,.1,1.,10.],'selection':'highest calibration exact-label accuracy, tie larger alpha',
                    'labels':'manually authored requested effects, not execution utility'},
        'llm':{'model_alias':config.MODEL,'temperature':.2,'max_tokens':180,'repeats':2,'arms':ARMS,'max_requests':144,
               'retries':0,'request_timeout_seconds':90},
        'admission':{'minimum_delivery_gain_over_each_control':.02,'maximum_regression_pairs':0,
                     'maximum_unsafe_boundary_actions':0,'maximum_input_token_overhead':.15,
                     'immutable_backbone_revision_required':True},
        'primary':'paired exact physical delivery on 16 valid tasks; report 8 boundary tasks separately',
        'scope':'one manually authored task family, one held-out measurement source, not cross-domain or SOTA'}
    protocol['protocol_sha256']=sr.digest(protocol);save(work/'protocol.json',protocol)
    print(json.dumps({'stage':'frozen','cases':len(cases),'protocol_sha256':protocol['protocol_sha256']}),flush=True)


def verify(work):
    p=load(work/'protocol.json')
    if p['protocol_sha256']!=sr.digest({k:v for k,v in p.items() if k!='protocol_sha256'}): raise ValueError('protocol changed')
    for path,h in p['code_sha256'].items():
        if sha((ROOT/path).read_bytes())!=h: raise ValueError('frozen code changed: '+path)
    if sha((work/'cases.json').read_bytes())!=p['cases_sha256']: raise ValueError('cases changed')
    cases=load(work/'cases.json')
    for c in cases:
        if sha((work/c['path']).read_bytes())!=c['input_sha256']: raise ValueError('input changed')
    return p,cases


def train(work):
    p,cases=verify(work)
    if (work/'model.json').exists(): raise ValueError('training already sealed')
    e=DenseIndex(ROOT/'.models/multilingual-e5-small')
    if e.status['revision']!=p['encoder']['revision']: raise ValueError('encoder mismatch')
    dev=[c for c in cases if c['split']=='train'];cal=[c for c in cases if c['split']=='calibration']
    x=e.embed([c['request'] for c in dev],'query: ');xc=e.embed([c['request'] for c in cal],'query: ')
    runs=[]
    for a in p['training']['alpha_grid']:
        m=sr.fit(x,[c['label'] for c in dev],a);pred=sr.predict(m,xc)
        runs.append((sum(q['label']==c['label'] for q,c in zip(pred,cal))/len(cal),a,m))
    score,a,model=max(runs,key=lambda r:(r[0],r[1]))
    model.update(protocol_sha256=p['protocol_sha256'],encoder=p['encoder'],trained_at_ns=time.time_ns(),
                 training_ids=[c['id'] for c in dev],training_queries=[c['request'] for c in dev],
                 training_labels=[c['label'] for c in dev],training_embeddings=x.tolist())
    save(work/'model.json',model)
    save(work/'selection.json',{'created_at_ns':time.time_ns(),'model_sha256':sr.digest(model),'alpha':a,
        'calibration_accuracy':score,'grid':[{'alpha':a,'accuracy':s} for s,a,_ in runs]})
    print(json.dumps({'stage':'trained','train':len(dev),'calibration':len(cal),'alpha':a,'accuracy':score}),flush=True)


def trial(work,c,action,name):
    raw=(work/c['path']).read_bytes()
    if action['reject']: return {'quality':0,'correct':c['expect_reject'],'action':action,'execution':None}
    folder=work/'executions'/name
    ex=utility_ops.execute(action['mask'],work/c['path'],folder)
    oracle=utility_oracle.evaluate(raw,c['intent'],folder)
    quality=int(not c['expect_reject'] and oracle['deliverable'])
    return {'action':action,'quality':quality,'correct':bool(quality),'execution':ex,'oracle':oracle,
            'directory':folder.relative_to(work).as_posix()}


def run(work):
    p,cases=verify(work);model=load(work/'model.json');sel=load(work/'selection.json')
    if sr.digest(model)!=sel['model_sha256']: raise ValueError('selection mismatch')
    if not config.API_KEY: raise ValueError('API configuration missing')
    if config.MODEL!=p['llm']['model_alias']: raise ValueError('API alias changed')
    if (work/'prompts.json').exists(): raise ValueError('test already started; no silent retries')
    e=DenseIndex(ROOT/'.models/multilingual-e5-small');tests=[c for c in cases if c['split']=='sealed_test']
    x=e.embed([c['request'] for c in tests],'query: ');pred=sr.predict(model,x)
    trainx=np.asarray(model['training_embeddings']);jobs=[];predictions={}
    for c,vec,q in zip(tests,x,pred):
        nearest=np.argsort(-(trainx@vec),kind='stable')[:3]
        examples=[{'request':model['training_queries'][i],'action':sr.action(model['training_labels'][i])} for i in nearest]
        predictions[c['id']]={'trained':q,'nearest':examples}
        base={'request':c['request'],'input_csv':(work/c['path']).read_text(encoding='utf-8')}
        for rep in range(2):
            # Three-arm counterbalanced rotation; not hidden retries.
            shift=(rep+tests.index(c)) % 3
            order=ARMS[shift:]+ARMS[:shift]
            for arm in order:
                payload=dict(base)
                if arm=='retrieved_examples': payload['development_examples']=examples
                if arm=='trained_hint': payload['advisory_trained_intent']={'action':sr.action(q['label']),
                    'scores':q['scores'],'warning':'未校准的语义标签分数，不是任务成功概率；请独立检查输入和要求。'}
                msg=[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
                jobs.append({'task_id':c['id'],'repeat':rep,'arm':arm,'messages':msg,'prompt_sha256':sr.digest(msg)})
    freeze={'created_at_ns':time.time_ns(),'protocol_sha256':p['protocol_sha256'],
            'model_sha256':sr.digest(model),'predictions':predictions,'jobs':jobs}
    save(work/'prompts.json',freeze)
    for c,q in zip(tests,pred):
        for arm,label in [('offline_trained',q['label']),('nearest_one',model['training_labels'][int(np.argmax(trainx@x[tests.index(c)]))])]:
            result=trial(work,c,sr.action(label),c['id']+'-'+arm)
            save(work/'records'/f'{c["id"]}-{arm}.json',dict(task_id=c['id'],arm=arm,repeat=0,**result))
    if len(jobs)!=p['llm']['max_requests']: raise ValueError('unexpected request count')
    def group(c):
        with httpx.Client(base_url=config.BASE_URL,timeout=httpx.Timeout(90,connect=15),
                          headers={'Authorization':'Bearer '+config.API_KEY}) as client:
            for job in [j for j in jobs if j['task_id']==c['id']]:
                record={k:v for k,v in job.items() if k!='messages'}
                record.update(started_at_ns=time.time_ns(),status='failed',quality=0,correct=False,execution=None)
                try:
                    response=client.post('/chat/completions',json={'model':p['llm']['model_alias'],
                        'messages':job['messages'],'temperature':.2,'max_tokens':180,'stream':False})
                    record['http_status']=response.status_code
                    if response.status_code!=200: raise ValueError('upstream failure')
                    d=response.json();usage=d.get('usage',{})
                    record.update(response_model=d.get('model'),system_fingerprint=d.get('system_fingerprint'),
                                  prompt_tokens=int(usage.get('prompt_tokens',0)),completion_tokens=int(usage.get('completion_tokens',0)))
                    text=d['choices'][0]['message']['content'];record['response']=text[:10000]
                    record['finish_reason']=d['choices'][0].get('finish_reason')
                    act=sr.parse_action(text)
                    record.update(trial(work,c,act,c['id']+'-'+job['arm']+'-'+str(job['repeat'])),status='completed')
                except Exception as exc: record['error_kind']=type(exc).__name__
                record['finished_at_ns']=time.time_ns()
                save(work/'records'/f'{c["id"]}-{job["arm"]}-{job["repeat"]}.json',record)
                print(c['id'],job['arm'],job['repeat'],record['status'],flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(group,tests))
    print('All arms recorded. Run the independent verifier before publication.',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','train','run']);p.add_argument('--work',required=True,type=Path)
    a=p.parse_args();{'prepare':prepare,'train':train,'run':run}[a.stage](a.work.absolute())


if __name__=='__main__':main()
