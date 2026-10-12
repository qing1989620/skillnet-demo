/* Catalogue relationships are declarations; the task overlay is a recorded execution. */
(function(root){
  'use strict';
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const groups=[['requires','依赖'],['required_by','被依赖'],['compose','组合'],['similar','相似候选']];
  function relationRows(id,edges,relations,visible){
    const seen=new Set(),rows=[];
    for(const edge of edges||[]){
      if(!relations.has(edge.type)||(edge.source!==id&&edge.target!==id))continue;
      const peer=edge.source===id?edge.target:edge.source;
      if(peer===id||(visible&&!visible.has(peer)))continue;
      const group=edge.type==='depend_on'?(edge.source===id?'requires':'required_by'):edge.type==='compose_with'?'compose':edge.type==='similar_to'?'similar':null;
      if(!group)continue;
      const key=group+'\0'+peer;if(seen.has(key))continue;seen.add(key);
      const label=group==='requires'?'依赖 '+peer:group==='required_by'?'被 '+peer+' 依赖':group==='compose'?'与 '+peer+' 组合':'相似候选 · '+peer;
      rows.push({group,peer,label,type:edge.type});
    }
    return rows.sort((a,b)=>groups.findIndex(g=>g[0]===a.group)-groups.findIndex(g=>g[0]===b.group)||a.peer.localeCompare(b.peer));
  }
  function nodeVisible(node,filter,selected,edges,onlyEvolved){
    if(filter.taskOnly&&filter.task&&!filter.task.has(node.id))return false;
    if(filter.domain&&node.domain!==filter.domain)return false;
    if(onlyEvolved&&!(node.generation>0))return false;
    if(filter.neighbors&&selected&&node.id!==selected.id&&!edges.some(e=>filter.relations.has(e.type)&&((e.source===selected.id&&e.target===node.id)||(e.target===selected.id&&e.source===node.id))))return false;
    return true;
  }
  function stepKey(step){return 'step:'+String(step.idx);}
  function taskView(run,key='all'){
    const all=Array.isArray(run.steps)?run.steps:[],step=key==='all'?null:all.find(s=>stepKey(s)===key);
    const selected=step?[step]:all;
    const names=[...new Set((step?selected.map(s=>s.skill):[...(run.skills||[]),...all.map(s=>s.skill)]).filter(n=>n&&n!=='manual'))];
    const severity={failed:5,running:4,skipped:3,pending:2,done:1},states=new Map();
    for(const s of selected)if(s.skill&&s.skill!=='manual'&&(!states.has(s.skill)||(severity[s.status]||0)>(severity[states.get(s.skill)]||0)))states.set(s.skill,s.status);
    return {key:step?stepKey(step):'all',step,steps:selected,names,states,manual:selected.filter(s=>!s.skill||s.skill==='manual').length};
  }
  function history(){
    const visits=[];let index=-1;
    return {visit(id){if(visits[index]===id)return;visits.splice(index+1);visits.push(id);index=visits.length-1;},back(){return index>0?visits[--index]:null;},canBack:()=>index>0,current:()=>visits[index]??null};
  }
  function checksHTML(checks){
    if(!Array.isArray(checks)||!checks.length)return '<p class="graph-unknown">未记录，无法确认。</p>';
    return '<ul>'+checks.map(c=>'<li><b>'+(c.passed===true?'通过':c.passed===false?'未通过':'未知')+'</b> · '+esc(c.name||c.item||'未命名检查')+(c.detail?'<small>'+esc(c.detail)+'</small>':'')+'</li>').join('')+'</ul>';
  }
  function taskDetailHTML(run,view,product){
    if(!view.step)return '<p>按真实步骤核对输入、产物与条件；技能关系仍来自当前目录，不能据此推断执行依赖。</p><div class="graph-step-list">'+view.steps.map(s=>'<button type="button" data-graph-step="'+esc(stepKey(s))+'">Step '+(Number(s.idx)+1)+' · '+esc(s.skill&&s.skill!=='manual'?s.skill:'通用执行')+'<small>'+esc(s.action||'动作未记录')+'</small></button>').join('')+(view.steps.length?'':'<p class="graph-unknown">尚无执行步骤记录。</p>')+'</div>';
    const s=view.step,contract=s.contract||{},observations=run.staged?.quality_assessment?.observations||[],observation=observations.find(o=>o.idx===s.idx);
    const required=Array.isArray(s.checks)?s.checks.filter(c=>c.required!==false):[],registered=Array.isArray(s.input_artifacts)?s.input_artifacts:[];
    const inputHTML=registered.map(a=>{const full=(run.artifacts||[]).find(f=>f.name===a.name&&f.sha256===a.sha256),origin=a.source_run_id||full?.source_run_id;return '<li><b>'+esc(a.logical_name||a.name||'文件名未记录')+'</b><small>登记文件 '+esc(a.name||'未知')+' · SHA '+esc(a.sha256||'未记录')+(origin&&origin!==run.run_id?' · 来自运行 '+esc(origin):'')+'</small>'+(a.name&&a.sha256?'<button type="button" data-artifact-preview data-run="'+esc(run.run_id)+'" data-file="'+esc(a.name)+'" data-sha="'+esc(a.sha256)+'">读取登记输入 ↗</button>':'')+'</li>';}).join('');
    const policy=run.staged?.state_policy||run.state_kernel?.policy,filtered={...run,steps:[s],staged:{...run.staged,state_composition:{...run.staged?.state_composition,frontier:(run.staged?.state_composition?.frontier||[]).filter(g=>g.step_idx===s.idx)}}};
    return '<div class="graph-step-heading"><b>Step '+(Number(s.idx)+1)+' · '+esc(s.skill&&s.skill!=='manual'?s.skill:'通用执行 · 未绑定技能')+'</b><span>'+esc(({done:'完成',failed:'失败',running:'执行中',pending:'待执行',skipped:'跳过'}[s.status])||'状态未知')+'</span></div><p>'+esc(s.action||'动作未记录')+'</p><div class="graph-step-files"><h4>声明的文件约定</h4><p>输入 '+esc((contract.input_files||[]).join(' / ')||'未声明')+' → 输出 '+esc((contract.output_files||[]).join(' / ')||'未声明')+'</p><h4>执行时登记的输入</h4><ul>'+(inputHTML||'<li class="graph-unknown">未记录输入版本；不能用约定代替实际输入。</li>')+'</ul><h4>执行时登记的产物</h4>'+(s.artifacts?.length?product.filesHTML({...run,artifacts:s.artifacts}):'<p class="graph-unknown">未登记实际产物，预期输出不表示已经产生。</p>')+'</div><details><summary>必要检查 '+(required.length?required.filter(c=>c.passed===true).length+'/'+required.length:'未知')+' · 独立结果检查 '+(observation?.independent_checks?.length?observation.independent_checks.filter(c=>c.passed===true).length+'/'+observation.independent_checks.length:'未知')+'</summary><h4>必要检查（可能包含独立检查）</h4>'+checksHTML(required)+'<h4>服务端独立结果判据</h4>'+checksHTML(observation?.independent_checks)+'<p>模型语义意见仅供参考；这些检查仍限于本次结果，不证明技能因果贡献。</p></details>'+(policy?product.stateKernelHTML(filtered):'<div class="graph-unknown"><b>前后条件实测：未知</b><p>该历史运行未保存可执行状态策略。'+(s.state_evidence?'保留的原始状态记录可在完整轨迹核对。':'未记录执行准入与效果核验，不能事后补写。')+'</p></div>')+'<button type="button" data-kernel-step="'+esc(s.idx)+'" data-run="'+esc(run.run_id)+'">打开本步代码、契约与修复记录 ↗</button>';
  }
  const core={esc,groups,relationRows,nodeVisible,stepKey,taskView,history,taskDetailHTML};
  if(typeof module==='object'&&module.exports){module.exports=core;return;}root.GraphExplorer=core;
})(typeof window==='object'?window:globalThis);

(function(){
  'use strict';
  if(typeof document==='undefined')return;
  const $=id=>document.getElementById(id),esc=UI.esc,core=window.GraphExplorer;
  const S={nodes:[],edges:[],byId:new Map(),selected:null,onlyEvolved:false,showLabel:true};
  const filter={domain:'',relations:new Set(['depend_on','compose_with','similar_to']),neighbors:false,taskOnly:false,task:null};
  const exploration=core.history();let generation=0,run=null,visibleIds=new Set(),selectionFocus=null,passportRequest=null,taskKey='all';
  const sphere=SkillSphere.create($('cv'),{
    center:(w,h)=>({x:w>1000?w*.57:w/2,y:h<750?h*.56:h*.52}),
    onPause:paused=>{$('btnPause').textContent=paused?'继续旋转':'暂停旋转';$('btnPause').setAttribute('aria-pressed',String(paused));},
    onSelect:n=>n?selectNode(n):closeCard(),
    onHover(n,p){const tip=$('tip');tip.style.display=n?'block':'none';if(n){tip.textContent=n.id+' · '+n.domain;tip.style.left=Math.min(p.x+12,innerWidth-240)+'px';tip.style.top=Math.min(p.y+12,innerHeight-60)+'px';}}
  });
  function renderRelations(){
    if(!S.selected)return;
    const all=core.relationRows(S.selected.id,S.edges,new Set(['depend_on','compose_with','similar_to'])),rows=core.relationRows(S.selected.id,S.edges,filter.relations,visibleIds);
    $('cRel').innerHTML='<div class="graph-rel-heading"><b>当前筛选下 '+rows.length+' 条关系</b><small>全部登记 '+all.length+' 条 · 当前目录声明</small></div>'+core.groups.map(([key,title])=>{const group=rows.filter(r=>r.group===key);return group.length?'<section><h4>'+title+' <span>'+group.length+'</span></h4>'+group.map(r=>'<button type="button" data-related="'+esc(r.peer)+'">'+esc(r.label)+'</button>').join('')+'</section>':'';}).join('')+(!rows.length?'<p class="graph-unknown">当前筛选下没有可见关系。'+(all.length?'可调整领域、关系或本次技能筛选。':'该技能尚未登记此类关系。')+'</p>':'')+'<p class="graph-rel-boundary">依赖方向按技能声明显示；组合与相似关系不表示已经协同执行或行为等价。</p>';
    $('cRel').querySelectorAll('[data-related]').forEach(b=>b.onclick=()=>{const node=S.byId.get(b.dataset.related);if(node)selectNode(node);});
    $('graph-back').disabled=!exploration.canBack();
    $('graph-selected-note').textContent=visibleIds.has(S.selected.id)?'': '此技能被当前筛选隐藏；详情与本次运行上下文仍保留。';
  }
  function refresh(){
    $('graph-neighbors').disabled=!S.selected;
    if(!S.selected){filter.neighbors=false;$('graph-neighbors').checked=false;}
    visibleIds=new Set(S.nodes.filter(n=>core.nodeVisible(n,filter,S.selected,S.edges,S.onlyEvolved)).map(n=>n.id));
    sphere.setFilter(n=>visibleIds.has(n.id),filter.relations);
    $('graph-visible').textContent='当前显示 '+visibleIds.size+' / '+S.nodes.length+' 个技能';renderRelations();if(run)renderTaskNote();
  }
  function closeCard(){const focused=$('card').contains(document.activeElement);S.selected=null;generation++;passportRequest?.abort();sphere.select(null);$('card').classList.remove('show');document.body.classList.remove('graph-skill-open');refresh();if(focused)(selectionFocus?.isConnected?selectionFocus:$('graph-q')).focus({preventScroll:true});}
  async function selectNode(node,{remember=true}={}){
    if(!$('card').contains(document.activeElement))selectionFocus=document.activeElement;
    if(remember)exploration.visit(node.id);S.selected=node;sphere.select(node.id);sphere.focus(node.id);
    $('cName').textContent=node.id;$('cDom').textContent=node.domain+' · '+(node.source==='github'?'社区导入 · 尚未执行认证':node.generation>0?'演化资产':'种子资产');
    $('cKv').textContent='历史调用 '+(node.pulls||0)+' 次 · 核验提升积分 +'+Number(node.verified_improvement_points||0).toFixed(2)+'（仅适用已验证版本）';
    $('cContractLink').href='/dashboard#skills?skill='+encodeURIComponent(node.id);
    $('graph-card-context').textContent=run?'保留运行 '+run.run_id+' · '+(taskKey==='all'?'全部采用':'Step '+(Number(core.taskView(run,taskKey).step?.idx)+1)):'探索当前目录';
    $('card').classList.add('show');document.body.classList.add('graph-skill-open');$('cName').focus({preventScroll:true});refresh();
    const current=++generation;passportRequest?.abort();passportRequest=new AbortController();$('cContract').textContent='读取能力边界…';
    try{const data=await UI.json('/api/skill/'+encodeURIComponent(node.id),{signal:passportRequest.signal});if(current!==generation)return;
      const p=data.passport||{},s=data.skill||{},list=xs=>Array.isArray(xs)&&xs.length?'<ul>'+xs.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'<p>尚未声明</p>';
      $('cContract').innerHTML='<small>CAPABILITY PASSPORT / 当前版本声明</small><h4>'+esc(p.capability||s.capability||s.description||'能力摘要未声明')+'</h4><b>何时启用</b>'+list(p.activation||s.use_when)+'<b>需要的输入 → 预期产物</b>'+list(p.inputs||s.inputs)+list(p.effects||s.outputs)+'<b>失效边界与注意事项</b>'+list(p.failure_boundary||s.pitfalls)+'<b>如何验收</b>'+list(p.verification||s.verification)+'<p>'+esc(p.boundary||'声明不代表已经实测')+'</p><details><summary>版本与环境</summary><p>'+esc(p.environment||'环境要求未声明')+'<br>SHA-256 <code>'+esc(p.skill_sha256||'未记录')+'</code></p></details>'+Product.rewardReceiptHTML(s)+Product.resourcesButtonHTML(s);
    }catch(e){if(current===generation&&e.name!=='AbortError')$('cContract').textContent=e.message;}
  }
  $('card').querySelector('.close').onclick=closeCard;
  $('graph-back').onclick=()=>{const id=exploration.back(),node=S.byId.get(id);if(node)selectNode(node,{remember:false});};
  $('graph-domain').onchange=e=>{filter.domain=e.target.value;refresh();};
  document.querySelectorAll('[data-relation]').forEach(input=>input.onchange=()=>{input.checked?filter.relations.add(input.dataset.relation):filter.relations.delete(input.dataset.relation);refresh();});
  $('graph-neighbors').onchange=e=>{filter.neighbors=e.target.checked;refresh();};
  $('graph-task-only').onchange=e=>{filter.taskOnly=e.target.checked;refresh();};
  $('graph-q').oninput=e=>{
    const query=e.target.value.trim().toLowerCase(),host=$('graph-results');
    const matches=query?S.nodes.filter(n=>(n.id+' '+n.domain).toLowerCase().includes(query)).slice(0,20):[];
    host.innerHTML=matches.map(n=>'<button type="button" data-node="'+esc(n.id)+'">'+esc(n.id)+'<small>'+esc(n.domain)+'</small></button>').join('')||(query?'<p>没有匹配技能</p>':'');
    host.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>{const node=S.byId.get(b.dataset.node);filter.domain='';$('graph-domain').value='';S.onlyEvolved=false;$('btnEvolved').classList.remove('on');$('btnEvolved').setAttribute('aria-pressed','false');filter.taskOnly=false;$('graph-task-only').checked=false;selectNode(node);host.innerHTML='';});
  };
  $('graph-q').onkeydown=e=>{if(e.key==='Enter'||e.key==='ArrowDown'){const first=$('graph-results').querySelector('[data-node]');if(first){e.preventDefault();if(e.key==='Enter')first.click();else first.focus();}}};
  $('btnZoomIn').onclick=()=>sphere.zoom(1.2);$('btnZoomOut').onclick=()=>sphere.zoom(1/1.2);
  $('btnReset').onclick=()=>{sphere.reset();closeCard();if(run)applyTask();};
  $('btnPause').textContent=matchMedia('(prefers-reduced-motion: reduce)').matches?'继续旋转':'暂停旋转';$('btnPause').setAttribute('aria-pressed',String(sphere.snapshot().paused));
  $('btnLabel').setAttribute('aria-pressed',String(S.showLabel));$('btnEvolved').setAttribute('aria-pressed',String(S.onlyEvolved));
  $('btnPause').onclick=()=>sphere.pause();
  $('btnLabel').onclick=e=>{S.showLabel=!S.showLabel;sphere.labels(S.showLabel);e.target.classList.toggle('on',S.showLabel);e.target.setAttribute('aria-pressed',String(S.showLabel));};
  $('btnEvolved').onclick=e=>{S.onlyEvolved=!S.onlyEvolved;e.target.classList.toggle('on',S.onlyEvolved);e.target.setAttribute('aria-pressed',String(S.onlyEvolved));refresh();};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!e.defaultPrevented&&!e.target.closest?.('dialog[open]')){closeCard();$('graph-results').innerHTML='';}});
  window.addEventListener('pagehide',()=>{generation++;passportRequest?.abort();});
  function renderTaskNote(){
    const view=core.taskView(run,taskKey),missing=view.names.filter(n=>!S.byId.has(n)),hidden=view.names.filter(id=>S.byId.has(id)&&!visibleIds.has(id));
    $('graph-task-note').textContent=(view.step?'Step '+(Number(view.step.idx)+1)+' · '+(view.manual?'通用执行，未绑定技能；本步不高亮任何技能':view.names.join(' / ')):'本轮采用 '+view.names.length+' 项 · '+(view.steps.length-view.manual)+' 个技能步骤 · '+view.manual+' 个通用步骤')+(missing.length?'。历史技能 '+missing.join(' / ')+' 不在当前库，保留当时记录，不补造节点':'')+(hidden.length?'。'+hidden.length+' 项被当前筛选隐藏':'')+'。高亮是当时采用记录；底图是当前目录。';
  }
  function applyTask(){
    const view=core.taskView(run,taskKey);taskKey=view.key;$('graph-step').value=taskKey;
    filter.task=new Set(view.names);sphere.highlight(view.names);sphere.states(view.states);$('graph-task-label').hidden=false;
    $('graph-task-detail').innerHTML=core.taskDetailHTML(run,view,Product);
    $('graph-task-detail').querySelectorAll('[data-graph-step]').forEach(button=>button.onclick=()=>setStep(button.dataset.graphStep));
    $('graph-capabilities').dataset.run=run.run_id;
    $('graph-run-link').href=typeof Product.runURL==='function'?Product.runURL({run:run.run_id,step:view.step?.idx}):'/run?id='+encodeURIComponent(run.run_id);
    $('graph-task-panel').hidden=false;refresh();
    if(view.step&&view.names.length===1&&S.byId.has(view.names[0])&&visibleIds.has(view.names[0]))sphere.focus(view.names[0]);
  }
  function setStep(key){taskKey=key;applyTask();const url=new URL(location.href);if(taskKey==='all')url.searchParams.delete('step');else url.searchParams.set('step',String(core.taskView(run,taskKey).step.idx));window.history.replaceState(null,'',url);if(S.selected)$('graph-card-context').textContent='保留运行 '+run.run_id+' · '+(taskKey==='all'?'全部采用':'Step '+(Number(core.taskView(run,taskKey).step?.idx)+1));}
  $('graph-step').onchange=e=>setStep(e.target.value);
  (async()=>{try{
    const graph=await UI.json('/api/graph');S.nodes=graph.nodes||[];S.edges=graph.edges||[];S.byId=new Map(S.nodes.map(n=>[n.id,n]));sphere.setData(graph);window.__GRAPHN__=S.nodes.length;
    const domains=[...new Set(S.nodes.map(n=>n.domain))].sort();$('graph-domain').insertAdjacentHTML('beforeend',domains.map(d=>'<option>'+esc(d)+'</option>').join(''));
    $('nN').textContent=S.nodes.length;$('nE').textContent=S.edges.length;$('nD').textContent=domains.length;
    const query=new URLSearchParams(location.search);if(domains.includes(query.get('domain'))){filter.domain=query.get('domain');$('graph-domain').value=filter.domain;}
    if(query.get('run')){try{run=await UI.json('/api/runs/'+encodeURIComponent(query.get('run')));$('graph-step').innerHTML='<option value="all">全部采用技能</option>'+(run.steps||[]).map(s=>'<option value="'+esc(core.stepKey(s))+'">Step '+(Number(s.idx)+1)+' · '+esc(s.skill&&s.skill!=='manual'?s.skill:'通用执行')+'</option>').join('');taskKey=query.has('step')?'step:'+query.get('step'):'all';applyTask();}catch(error){UI.toast('任务读取失败：'+error.message);}}
    refresh();if(S.byId.has(query.get('skill'))){filter.domain='';$('graph-domain').value='';selectNode(S.byId.get(query.get('skill')));}
    $('load').hidden=true;$('load').style.display='none';
  }catch(error){$('load').textContent='技能网络读取失败：'+error.message;}})();
  window.__SELFTEST__=()=>({'canvas存在':!!$('cv'),'球体已加载节点':window.__GRAPHN__>0,'关系返回控件存在':!!$('graph-back'),'步骤选择器存在':!!$('graph-step')});
})();
