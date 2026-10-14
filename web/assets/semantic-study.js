(function(){
  'use strict';
  const $=id=>document.getElementById(id), node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e;};
  const names={plain:'模型独立选择',retrieved_examples:'加入检索示例',trained_hint:'加入训练提示',guarded_plain:'独立选择 + 数据检查'};
  const states={verified:'实际产物验收通过',rejected:'实际产物未通过',preflight_rejected:'执行前数据检查拦截',recorded_refusal:'原始模型拒绝执行',invalid_recorded_action:'原始决策格式无效，停止执行'};
  let data=null,busy=false,epoch=0,controller=null;
  function lock(value){busy=value;$('semantic-case').disabled=value||!data;$('semantic-repeat').disabled=value;$('semantic-replay').disabled=value||!data;$('semantic-retry').disabled=value;}
  function choice(){const c=data?.cases.find(c=>c.id===$('semantic-case').value);$('semantic-request').textContent=c?.request||'';$('semantic-results').replaceChildren();$('semantic-input').textContent='';$('semantic-replay-status').textContent='';}
  async function load(){const ticket=++epoch;controller?.abort();controller=new AbortController();data=null;lock(true);
    try{const d=await UI.json('/api/frontier/utility/semantic',{signal:controller.signal});if(ticket!==epoch)return;data=d;
      $('semantic-metrics').replaceChildren();for(const arm of ['plain','retrieved_examples','trained_hint']){const m=d.report.metrics[arm],tr=node('tr');for(const v of [names[arm],m.valid_deliveries+' / '+m.valid_trials,m.boundary_refusals+' / '+m.boundary_trials,m.unsafe_boundary_actions,m.failed_calls])tr.append(node('td',v));$('semantic-metrics').append(tr);}
      const cmp=d.report.paired_comparisons.plain;$('semantic-status').textContent='完整记录 '+d.report.api_requests+' 次 API 请求与 '+d.report.physical_executions+' 次物理执行。训练提示相对独立模型：'+cmp.win_pairs+' 胜 / '+cmp.loss_pairs+' 负 / '+cmp.tie_pairs+' 平；输入 token '+(cmp.input_token_overhead>=0?'+':'')+(cmp.input_token_overhead*100).toFixed(1)+'%。';
      const m=d.report.metrics.offline_trained;$('semantic-generalization').textContent='开发措辞下的校准标签准确率 '+(d.selection.calibration_accuracy*100).toFixed(0)+'%。直接使用训练头，在新措辞的有效任务上只交付 '+m.valid_deliveries+' / '+m.valid_trials+'。两者衡量不同阶段，不能把校准分数当成泛化证书。';
      const a=d.report.admission;$('semantic-admission').textContent=a.passed+' / 12 道门通过 · 未晋级 · 奖励 0';$('semantic-gates').textContent=a.gates.map(g=>g.title+' ['+g.status+']\n'+g.reason).join('\n\n');
      const g=d.guard_validation.metrics;$('semantic-guard').textContent='另外 12 道全新 Glass 输入 × 8 种动作，强制执行 96 次：'+g.valid_actions+' 个可执行动作没有误拦，'+g.invalid_actions+' 个不可执行动作没有漏拦。此结果只覆盖这份冻结验证集。';
      $('semantic-case').replaceChildren(...d.cases.map(c=>{const o=node('option',c.id+' · '+c.kind);o.value=c.id;return o;}));choice();
    }catch(e){if(ticket===epoch&&e.name!=='AbortError')$('semantic-status').textContent=e.message||'研究文件暂不可用，请重新加载。';}
    finally{if(ticket===epoch)lock(false);}}
  async function replay(){if(busy||!data)return;const ticket=++epoch;controller?.abort();controller=new AbortController();lock(true);$('semantic-results').replaceChildren();$('semantic-replay-status').textContent='正在按原始决策重跑固定程序并核验产物…';
    try{const r=await UI.json('/api/frontier/utility/semantic/replay',{method:'POST',body:JSON.stringify({case_id:$('semantic-case').value,repeat:Number($('semantic-repeat').value)}),signal:controller.signal});if(ticket!==epoch)return;
      $('semantic-input').textContent=r.input_csv;
      for(const [arm,result] of Object.entries(r.results)){const card=node('article',undefined,'execution-card '+(result.state==='verified'?'passed':'rejected'));card.append(node('h4',names[arm]),node('p',states[result.state]||result.state),node('p','原始决策：'+JSON.stringify(result.recorded_action),'note'));
        if(result.preflight)card.append(node('p','数据检查：'+(result.preflight.allowed?'可尝试执行':result.preflight.reasons.join(' / ')),'note'));
        for(const [name,file] of Object.entries(result.artifacts||{})){const detail=node('details');detail.append(node('summary',name+' · SHA '+file.sha256.slice(0,12)),node('pre',file.text));card.append(detail);}$('semantic-results').append(card);}
      $('semantic-replay-status').textContent='重跑完成 · 新增 API 调用 '+r.new_api_calls+' · 正式库与奖励未改变。';
    }catch(e){if(ticket===epoch&&e.name!=='AbortError')$('semantic-replay-status').textContent=e.message||'重跑未完成，可重试。';}
    finally{if(ticket===epoch)lock(false);}}
  $('semantic-case').addEventListener('change',choice);$('semantic-repeat').addEventListener('change',choice);$('semantic-retry').addEventListener('click',load);$('semantic-replay').addEventListener('click',replay);
  document.querySelector('.semantic-download').addEventListener('click',async event=>{event.preventDefault();const link=event.currentTarget;if(link.getAttribute('aria-disabled')==='true')return;link.setAttribute('aria-disabled','true');try{const r=await UI.fetch(link.getAttribute('href'));if(!r.ok)throw new Error('证据下载失败');const url=URL.createObjectURL(await r.blob()),a=node('a');a.href=url;a.download='skillnet-semantic-routing-physical-evidence-v1.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch(e){$('semantic-replay-status').textContent=e.message||'证据下载失败';}finally{link.removeAttribute('aria-disabled');}});
  window.addEventListener('pagehide',()=>{epoch++;controller?.abort();});load();
})();
