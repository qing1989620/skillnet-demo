"""Grouped, source-aware routing experiments. These metrics are not execution rewards."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import math
import numpy as np

from .learned_network import digest


def query_fingerprint(text):
    return hashlib.sha256(' '.join(text.lower().split()).encode()).hexdigest()


def grouped_source_split(tasks, external_sources=('theoremqa', 'bigcodebench')):
    """Keep identical questions and exact reference sets together, without scores.

    A component touching a fully external source is always external. Remaining
    components are hash-ordered within source: 20/20/20/40 test/val/cal/train.
    """
    parent=list(range(len(tasks)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(i,j):
        a,b=find(i),find(j)
        if a!=b:parent[max(a,b)]=min(a,b)
    seen={}
    for i,t in enumerate(tasks):
        for key in [('query',query_fingerprint(t['query'])),('gold',digest(sorted(t['gold'])))]:
            if key in seen:union(i,seen[key])
            else:seen[key]=i
    groups=defaultdict(list)
    for i in range(len(tasks)):groups[find(i)].append(i)
    buckets=defaultdict(list);output={}
    for indices in groups.values():
        members=[tasks[i] for i in indices]
        key=digest(sorted(t['id'] for t in members))
        if any(t['source'] in external_sources for t in members):split='external_test'
        else:
            buckets[min(t['source'] for t in members)].append((key,indices));continue
        for i in indices:output[tasks[i]['id']]=(split,key)
    for groups in buckets.values():
        for j,(key,indices) in enumerate(sorted(groups)):
            fold=j%10
            split='test' if fold<2 else 'validation' if fold<4 else 'calibration' if fold<6 else 'train'
            for i in indices:output[tasks[i]['id']]=(split,key)
    return output


def routing_metrics(scores,tasks,node_ids,pool_indices):
    scores=np.asarray(scores)
    if scores.shape!=(len(tasks),len(node_ids)) or not np.isfinite(scores).all() or len(set(node_ids))!=len(node_ids):
        raise ValueError('Incomplete, nonfinite or ambiguously indexed routing scores')
    pools={key:np.asarray(values,dtype=np.int64) for key,values in pool_indices.items()}
    for pool in pools.values():
        if pool.ndim!=1 or not len(pool) or len(set(pool.tolist()))!=len(pool) or pool.min()<0 or pool.max()>=len(node_ids):
            raise ValueError('Invalid declared candidate pool')
    pool_sets={key:set(values.tolist()) for key,values in pools.items()}
    by={n:i for i,n in enumerate(node_ids)};rows=[]
    for score,t in zip(scores,tasks):
        pool=pools[t['pool']]
        gold={by[n] for n in t['gold']}
        if not gold or not gold.issubset(pool_sets[t['pool']]):
            raise ValueError('Routing references are empty or outside the declared pool')
        order=pool[np.argsort(-np.asarray(score)[pool],kind='stable')]
        head=set(order[:5].tolist());rank=next(i+1 for i,n in enumerate(order) if n in gold)
        rows.append(dict(id=t['id'],source=t['source'],family=t['family'],
            query_sha256=query_fingerprint(t['query']),recall5=len(gold&head)/len(gold),
            mrr=1/rank,top5=[node_ids[i] for i in order[:5]]))
    families=defaultdict(list);sources=defaultdict(list)
    for r in rows:families[(r['source'],r['family'])].append(r['recall5'])
    for (source,family),values in families.items():sources[source].append(float(np.mean(values)))
    per_source={s:float(np.mean(v)) for s,v in sorted(sources.items())}
    return dict(tasks=len(rows),families=len(families),
        recall5=float(np.mean([r['recall5'] for r in rows])) if rows else None,
        source_family_macro=float(np.mean(list(per_source.values()))) if rows else None,
        per_source_family_macro=per_source,rows=rows)


def paired_routing_comparison(baseline,candidate):
    if [r['id'] for r in baseline['rows']]!=[r['id'] for r in candidate['rows']]:
        raise ValueError('Paired results must contain every matching task in the same order')
    diffs=[];families=defaultdict(list);sources=defaultdict(list)
    for b,c in zip(baseline['rows'],candidate['rows']):
        if b['query_sha256']!=c['query_sha256'] or b['family']!=c['family'] or b['source']!=c['source']:
            raise ValueError('Paired task, source or family version mismatch')
        d=c['recall5']-b['recall5'];diffs.append(d);families[(b['source'],b['family'])].append(d)
    values=[float(np.mean(v)) for v in families.values()]
    for (source,family),v in families.items():sources[source].append(float(np.mean(v)))
    wins=sum(v>1e-10 for v in values);losses=sum(v< -1e-10 for v in values);n=wins+losses
    p=sum(math.comb(n,k) for k in range(wins,n+1))/2**n if n else 1.
    return dict(mean_task_gain=float(np.mean(diffs)) if diffs else None,
        source_family_macro_gain=float(np.mean([np.mean(v) for v in sources.values()])) if values else None,
        task_wins=sum(d>1e-10 for d in diffs),task_losses=sum(d< -1e-10 for d in diffs),
        task_ties=sum(abs(d)<=1e-10 for d in diffs),family_wins=wins,family_losses=losses,
        family_ties=len(values)-n,family_sign_p=p,
        statistical_boundary='One-sided sign statistic on reference-set components; independence across families is an assumption, not a proved anytime-valid guarantee.')


def binomial_risk_upper(failures,total,delta):
    """Exact one-sided binomial upper bound, conditional on iid units.

    A numerical bound cannot establish independence or transfer under shift.
    Empty cohorts have unknown risk (upper bound 1), never a free certificate.
    """
    if type(failures) is not int or type(total) is not int or not 0<=failures<=total or not 0<delta<1:
        raise ValueError('Invalid binomial confidence inputs')
    if not total or failures==total:return 1.
    if failures==0:return 1-delta**(1/total)
    def cdf(p):
        return math.fsum(math.exp(math.lgamma(total+1)-math.lgamma(k+1)-math.lgamma(total-k+1)
            +k*math.log(p)+(total-k)*math.log1p(-p)) for k in range(failures+1))
    lo,hi=failures/total,1.
    for _ in range(64):
        mid=(lo+hi)/2
        if mid>=1:break
        if cdf(mid)>delta:lo=mid
        else:hi=mid
    return hi
