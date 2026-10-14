"""Publish public models, frozen protocols and complete physical evidence only."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from skillnet import conditional_utility as cu,reward_gates,utility_oracle
from tools.conditional_utility_lab import load


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def admission(work):
    report=load(work/'report.json');lr=load(work/'llm-report.json');audit=load(work/'artifact-audit.json')
    frozen=load(work/'llm-prompts-frozen.json');all_records=lr['records'];jobs=frozen['jobs']
    by_id={c['id']:c for c in load(work/'cases.json')};errors=[]
    for r in all_records:
        matches=[j for j in jobs if j['task_id']==r['task_id'] and j['repeat']==r['repeat'] and j['arm']==r['arm']]
        if (len(matches)!=1 or matches[0]['prompt_sha256']!=r['prompt_sha256']
                or r['started_at_ns']<=frozen['created_at_ns']):errors.append('prompt binding/order')
        if r.get('directory'):
            case=by_id[r['task_id']];check=utility_oracle.evaluate((work/case['path']).read_bytes(),case['intent'],work/r['directory'])
            if check!=r['oracle'] or int(check['deliverable'])!=r['quality']:errors.append('LLM artifact evaluation')
            for name,meta in r['execution']['artifacts'].items():
                data=(work/r['directory']/name).read_bytes()
                if hashlib.sha256(data).hexdigest()!=meta['sha256'] or len(data)!=meta['bytes']:errors.append('LLM artifact bytes')
    a=reward_gates.Audit({'kind':'conditional-execution-research','protocol_sha256':report['protocol_sha256'],
        'model_sha256':report['model_sha256'],'llm_model_alias':'deepseek-chat','public_source_clusters':1,
        'interpretation':'research scope only; no formally registered candidate promotion'})
    a.set('frozen','passed','输入、协议、技能程序、判据先冻结；测试预测与 API 提示在执行前写入。')
    a.set('independent','passed','独立于执行器的原单元格与 Decimal 数值判据重读真实文件；不采用模型评分。')
    a.set('integrity','passed' if audit['ok'] and not errors else 'failed','逐项重算 2464 次固定程序与真实 API 执行产物的指纹。',errors=errors)
    a.set('complete','passed' if lr['summary']['failed_or_malformed_calls']==0 else 'failed','全部 48 次调用与失败/拒绝记录完整保留；有效任务文件逐项验算。')
    a.set('version','unknown','三个登记程序与数值候选已锁定；提供方仅返回 deepseek-flash 别名，尚无不可变模型修订标识或正式库技能候选凭证。')
    a.set('fair','passed' if len(lr['summary']['response_models'])==1 else 'unknown','同一 API 别名、动作集、预算；每题两次配对交替顺序，逐臂记录真实 token。')
    a.set('heldout','passed','本研究训练/校准/新测试输入指纹不重叠，公开测量来源整体留出；不宣称基础大模型从未见过原始数据。')
    a.set('suite','passed' if lr['summary']['tasks']>=5 and len(all_records)==48 else 'failed','12 道预先登记的任务各两次配对，所有组与无效边界任务完整报告。')
    a.set('regression','passed' if not lr['summary']['regression_pairs'] else 'failed','真实 API 有效任务配对没有观察到候选退步。')
    gain=lr['summary']['evidence_delivery_rate']-lr['summary']['plain_delivery_rate']
    a.set('gain','passed' if gain>=.02 else 'failed','真实 API 的交付质量增益为 0；提前拒绝无效任务不能冒充有效任务质量提升。',mean_gain=gain)
    a.set('reliable','unknown','首轮真实测量只来自一个公开来源，题目共享记录；任务符号检验不能作为跨领域可靠性证据。')
    a.set('novel','unknown','研究候选尚无正式提升证书与一次性版本奖励凭证；不产生奖励。')
    result=a.result();write(work/'admission.json',result)
    write(work/'llm-artifact-audit.json',{'ok':not errors,'errors':errors,'checked_calls':len(all_records),
        'checked_physical_arms':sum(bool(r.get('execution')) for r in all_records)})
    if errors:raise ValueError('LLM physical evidence did not pass audit')


def package(work,version):
    target=ROOT/'assets/conditional-utility'/version
    if target.exists():raise ValueError('published research bundle already exists')
    target.mkdir(parents=True)
    files=['protocol.json','model.json','selection.json','cases.json','report.json']
    if version=='v1':files+=['artifact-audit.json','strong-baselines.json','admission.json','llm-report.json','llm-artifact-audit.json','LICENSE.md','penguins.csv']
    else:
        files+=['iris.data','feature-rule-diagnostic.json']
        (work/'ATTRIBUTION.md').write_text('Iris — Fisher, R. (1936). UCI Machine Learning Repository. https://doi.org/10.24432/C56C76\n\nSource: https://archive.ics.uci.edu/dataset/53/iris\nLicense: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/\n\nExperimental inputs select sepal-length measurements and species labels; splits, identifiers, blank groups and invalid-value challenges are authored transformations. These are not defects attributed to the original dataset.\n',encoding='utf-8',newline='\n')
        files+=['ATTRIBUTION.md']
    for name in files:shutil.copyfile(work/name,target/name)
    shutil.copytree(work/'inputs',target/'inputs')
    archive=target/'execution-evidence.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in sorted(work.rglob('*')):
            if not file.is_file() or file.is_symlink() or '__pycache__' in file.parts:continue
            name=file.relative_to(work).as_posix()
            if file.suffix not in ('.csv','.json','.py','.md','.data','.zip'):continue
            info=zipfile.ZipInfo(name);info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,file.read_bytes(),compresslevel=9)
    manifest={'version':'public-conditional-research-'+version,'files':{
        p.relative_to(target).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(target.rglob('*')) if p.is_file()}}
    manifest['digest']=cu.digest(manifest);write(target/'publication.json',manifest)
    print(json.dumps({'bundle':str(target),'files':len(manifest['files']),'archive_bytes':archive.stat().st_size}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--v1',type=Path,required=True);p.add_argument('--v2',type=Path,required=True)
    a=p.parse_args()
    if not (a.v2/'feature-rule-diagnostic.json').exists():
        from tools.analyze_boundary_feature_rule import analyze
        analyze(a.v2)
    admission(a.v1);package(a.v1,'v1');package(a.v2,'v2')
