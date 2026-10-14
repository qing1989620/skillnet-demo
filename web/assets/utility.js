(function(){
  'use strict';
  const $=id=>document.getElementById(id),el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n;};
  const pct=n=>Number.isFinite(n)?(100*n).toFixed(2)+'%':'—';
  const names={deduplicate:'按样本键去重',exclude_cross_split:'排除跨集合实体',drop_missing:'删除空值行'};
  const strategies={none:'直接汇总',all:'全部调用（原始对照）',contract:'按明确契约选择',contract_preflight:'契约 + 基础条件检查',learned:'训练后的条件选择'};
  let generation=0,controller=null,busy=false,available=false;
  $('utility-nav').innerHTML=UI.productNav('utility');
  const api=path=>'/api/frontier/utility'+($('version').value==='v2'?'/boundary':'')+path;
  function status(message,error=false){$('run-status').textContent=message;$('run-status').className=error?'error':'';}
  function detail(host,title,value){const d=el('details');d.append(el('summary',title),el('pre',typeof value==='string'?value:JSON.stringify(value,null,2)));host.append(d);}
  function contract(caseData){$('contract').replaceChildren();Object.entries(caseData.intent).forEach(([k,v])=>{const row=el('div',undefined,'contract-row');row.append(el('span',names[k]||'目标'),el('b',k==='goal'?v:v?'执行':'保留原记录'));$('contract').append(row);});}
  function paintPrediction(p){const h=$('prediction');h.replaceChildren();const v2=$('version').value==='v2';
    h.append(el('p',p.abstain?'本次建议先停止执行':'本次建议使用登记技能组合','decision'+(p.abstain?' stopped':'')));
    const mask=v2?p.observed.mask:(p.mask??p.proposed_mask);if(Number.isInteger(mask))h.append(el('p',(p.abstain?'候选组合（未执行）：':'组合：')+Object.keys(names).filter((_,j)=>mask&(1<<j)).map(k=>names[k]).concat('分组汇总').join(' → '),'prediction-note'));
    if(v2){h.append(el('p','失败分数 '+pct(p.failure_score)+' · 校准选择阈值 '+pct(p.threshold),'prediction-note'));Object.entries(p.observed.conditions||{}).forEach(([k,v])=>{const row=el('div',undefined,'contract-row');row.append(el('span',({no_projected_test_rows:'预计没有 test 行',any_projected_group_without_number:'预计存在全空值分组',bad_projected_number:'预计存在非法数值'})[k]||k),el('b',v?'是':'否'));h.append(row);});}
    else{h.append(el('p','预测交付质量 '+pct(p.predicted_quality)+' · 预测执行失败 '+pct(p.predicted_execution_failure),'prediction-note'));
      (p.marginal||[]).forEach(m=>{const gain=m.predicted_marginal_gain,row=el('div',undefined,'gain-row');row.append(el('span',names[m.skill]||m.skill),el('b',(gain>0?'+':'')+(gain*100).toFixed(1)+' pp',gain<0?'negative':'positive'));h.append(row);});h.append(el('p','边际收益按四种共存技能组合平均，不能把三个数直接相加作为本题收益。','note'));}
    const reason={outside_training_support:'超出训练条件支持',predicted_failure_or_low_quality:'预测存在失败或质量不足',within_finite_training_support:'条件落在有限训练支持内',unsupported_contract:'目标或结构超出支持范围',learned_failure_boundary:'触发已学习的失败边界',no_learned_boundary_triggered:'没有触发已学习边界，仍须执行验算',calibration_kept_baseline:'校准保留原始对照'};
    h.append(el('p',reason[p.reason]||p.reason,'prediction-note'));detail(h,'查看完整预测与指纹',p);
  }
  async function preview(){const own=++generation;controller?.abort();controller=new AbortController();available=false;$('execute').disabled=true;$('execution-results').replaceChildren();status('正在读取冻结输入并计算执行前预测…');
    try{const d=await UI.json(api('/predict'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:$('case').value}),signal:controller.signal});if(own!==generation)return;contract(d.case);$('input').textContent=d.input_csv;paintPrediction(d.prediction);available=true;status('预测已记录。可以重新运行本次对照，核验实际文件。');}
    catch(e){if(own===generation&&e.name!=='AbortError')status(e.message||'预测未完成，请重试。',true);}finally{if(own===generation)$('execute').disabled=!available||busy;}
  }
  async function loadCases(){const own=++generation;controller?.abort();controller=new AbortController();available=false;$('case').disabled=true;$('execute').disabled=true;status('正在核验研究版本…');
    try{const d=await UI.json(api('/cases'),{signal:controller.signal});if(own!==generation)return;$('case').replaceChildren();for(const c of d.cases){const o=el('option',c.label||c.id);o.value=c.id;$('case').append(o);}$('case').disabled=false;await preview();}
    catch(e){if(own===generation&&e.name!=='AbortError')status(e.message||'任务读取失败，请重试。',true);}
  }
  $('case').onchange=preview;$('version').onchange=loadCases;$('retry').onclick=loadCases;
  $('execute').onclick=async()=>{if(busy||!available)return;busy=true;const own=++generation;controller?.abort();controller=new AbortController();['execute','case','version','retry'].forEach(id=>$(id).disabled=true);status('正在启动登记程序，随后逐项验算真实 CSV…');
    try{const d=await UI.json(api('/execute'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:$('case').value}),signal:controller.signal});if(own!==generation)return;const host=$('execution-results');host.replaceChildren();
      for(const [arm,r] of Object.entries(d.results)){const passed=!!r.oracle?.deliverable,card=el('article',undefined,'execution-card '+(passed?'passed':'rejected'));
        card.append(el('h4',({all:'原始对照：全部调用',conditional:'候选：条件选择',baseline:'对照：基础条件检查',candidate:'候选：学习后的边界',diagnostic:'诊断：强制执行复核'})[arm]||arm));
        card.append(el('p',r.state==='abstained'?'执行前停止，未生成交付物':passed?'独立验算通过，可交付':'未通过独立验算，拒绝交付',passed?'positive':'neutral'));
        if(r.oracle?.reason)card.append(el('p',r.oracle.reason,'note'));for(const [name,a] of Object.entries(r.artifacts||{}))detail(card,name+' · '+a.sha256.slice(0,12),a.text);
        detail(card,'查看文件指纹与验算项',r);host.append(card);}
      status('本次配对完成。奖励 0；正式技能与个人网络配置均未修改。');}
    catch(e){if(own===generation&&e.name!=='AbortError')status(e.message||'执行未完成，请重试。',true);}finally{busy=false;['case','version','retry'].forEach(id=>$(id).disabled=false);$('execute').disabled=!available;}
  };
  async function evidence(){try{const d=await UI.json('/api/frontier/utility');$('page-status').textContent='模型、协议和 '+d.artifact_audit.checked_subprocesses+' 次原始执行记录已核验。';
      [['160','训练任务 · 合成控制'],['68','校准任务 · 独立于训练'],[d.summary.tasks,'第一轮封存任务'],[d.summary.actual_subprocesses,'封存测试实际程序执行']].forEach(([v,label])=>{const s=el('div',undefined,'stat');s.append(el('strong',v),el('span',label));$('stats').append(s);});
      for(const [key,m] of Object.entries(d.strong_baselines)){const row=el('tr');row.dataset.learned=String(key==='learned');[strategies[key]||key,pct(m.verified_delivery_rate),m.invalid_abstentions+' / '+m.invalid_tasks,m.invalid_execution_attempts].forEach(v=>row.append(el('td',v)));$('strategies').append(row);}
      $('baseline-note').textContent='训练策略在本批任务中与“契约 + 基础条件检查”持平。第一轮漏掉 1 道分组全空反例；同源任务共享测量记录，不能据此宣称通用网络持续变强。';
      const l=d.llm,comp=el('div',undefined,'big-comparison');for(const [v,label] of [[l.plain_delivery_rate,'原模型选择'],[l.evidence_delivery_rate,'加入条件预测']]){const box=el('div');box.append(el('span',pct(v)),el('small',label));comp.append(box);}$('llm-result').append(comp,el('p',l.plain_delivery_rate===l.evidence_delivery_rate?'本轮没有观察到额外质量提升。':'本轮观察到差异，完整结果见原始证据。','neutral'),el('p',d.usage.calls+' 次真实 API 调用 · '+d.usage.total_tokens.toLocaleString()+' tokens · 返回模型 '+l.response_models.join(', '),'note'));
      for(const gate of d.admission.gates){const block=el('details',undefined,'gate '+gate.status);block.append(el('summary',(gate.status==='passed'?'✓ ':gate.status==='failed'?'× ':'? ')+gate.title),el('p',gate.reason));$('gates').append(block);}
      $('admission').textContent=d.admission.passed+' / 12 道门通过 · 当前奖励 0 · 候选保持实验状态';$('fingerprints').textContent=JSON.stringify({model_sha256:d.model_sha256,protocol_sha256:d.protocol_sha256,scope:d.scope,limitations:d.limitations},null,2);
    }catch(e){$('page-status').textContent=e.message||'研究证据不可用，请核验完整交付。';$('page-status').className='error';}}
  async function boundaryEvidence(){try{const d=await UI.json('/api/frontier/utility/boundary');const a=d.metrics.contract_preflight_v1,b=d.metrics.learned_boundary_v2;const host=$('boundary-result');host.replaceChildren();const comp=el('div',undefined,'big-comparison');for(const [v,label] of [[a.invalid_refusals,'原检查提前拒绝'],[b.invalid_refusals,'修正候选提前拒绝']]){const box=el('div');box.append(el('span',v+' / '+b.invalid_tasks),el('small',label));comp.append(box);}host.append(comp,el('p','有效任务交付：'+a.valid_deliveries+' / '+a.valid_tasks+' → '+b.valid_deliveries+' / '+b.valid_tasks,'positive'),el('p','更细的分组条件也可直接实现规则检查；事后诊断中规则达到相同结果，尚未证明学习头更优。奖励仍为 0。','note'));}
    catch(e){$('boundary-result').replaceChildren(el('p',e.message||'边界修正证据不可用，请稍后重试。','error'));}}
  window.addEventListener('pagehide',()=>{generation++;controller?.abort();});evidence();boundaryEvidence();loadCases();
  document.querySelectorAll('.download').forEach(link=>link.addEventListener('click',async event=>{event.preventDefault();if(link.getAttribute('aria-disabled')==='true')return;link.setAttribute('aria-disabled','true');try{const r=await UI.fetch(link.getAttribute('href'));if(!r.ok)throw new Error('证据下载未完成，请检查连接设置后重试。');const url=URL.createObjectURL(await r.blob()),a=el('a');a.href=url;a.download=link.href.includes('/boundary/')?'skillnet-boundary-evidence-v2.zip':'skillnet-utility-evidence-v1.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch(e){UI.toast(e.message||'证据下载失败');}finally{link.removeAttribute('aria-disabled');}}));
})();
