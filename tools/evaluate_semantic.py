"""Frozen Chinese retrieval smoke evaluation; relevance labels are not exhaustive."""
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skillnet.catalog import SkillLibrary
from skillnet.retriever import Retriever
from skillnet.index import VectorIndex

root=Path(__file__).resolve().parents[1]
source=root/'config/chinese_retrieval_cases.json'
cases=json.loads(source.read_text(encoding='utf-8'))
library=SkillLibrary.load()
retriever=Retriever(library).build()
assert retriever.vec.status['kind']=='dense-onnx', 'Install the real encoder first'
dense=retriever.vec
skills=library.all()
lexical=VectorIndex();lexical.fit([s.name for s in skills],[s.l1_text() for s in skills])
report=dict(kind='frozen-chinese-retrieval-smoke',created_at=time.time(),cases_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            library_size=len(library),encoder=dense.status,weights=None,k=10,
            scope='Hit@10 against manually frozen acceptable skills; labels not exhaustive; not a general quality claim',results=[])
for case in cases:
    row=dict(query=case['query'],expected=case['expected'],split=case.get('split','development'))
    for name,index in [('lexical',lexical),('dense',dense)]:
        hits=[n for n,_ in index.search(case['query'],top_k=10)]
        row[name]=dict(hit=bool(set(hits)&set(case['expected'])),selected=hits)
    hybrid=retriever.search(case['query'],k=10,mode='hybrid',rerank=False,expand=False)
    report['weights']=hybrid.weights
    row['hybrid']=dict(selected=hybrid.selected)
    row['hybrid']['hit']=bool(set(row['hybrid']['selected'])&set(case['expected']))
    report['results'].append(row)
report['hit_at_10']={name:sum(r[name]['hit'] for r in report['results'])/len(cases) for name in ('lexical','dense','hybrid')}
report['splits']={split:{name:sum(r[name]['hit'] for r in report['results'] if r['split']==split)/sum(r['split']==split for r in report['results']) for name in ('lexical','dense','hybrid')} for split in {r['split'] for r in report['results']}}
path=root/'out/chinese-retrieval-evaluation.json'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['hit_at_10']),path)
