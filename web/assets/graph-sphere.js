/* Full catalogue exploration, plus a recorded task overlay. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),esc=UI.esc;
  const S={nodes:[],edges:[],byId:new Map(),selected:null,onlyEvolved:false,showLabel:true};
  const filter={domain:'',relations:new Set(['depend_on','compose_with','similar_to']),neighbors:false,taskOnly:false,task:null};
  let generation=0,run=null,visibleIds=new Set(),selectionFocus=null;
  const sphere=SkillSphere.create($('cv'),{
    center:(w,h)=>({x:w>1000?w*.57:w/2,y:h<750?h*.56:h*.52}),
    onPause:paused=>{$('btnPause').textContent=paused?'继续旋转':'暂停旋转';$('btnPause').setAttribute('aria-pressed',String(paused));},
    onSelect:n=>n?selectNode(n):closeCard(),
    onHover(n,p){const tip=$('tip');tip.style.display=n?'block':'none';if(n){tip.textContent=n.id+' · '+n.domain;tip.style.left=Math.min(p.x+12,innerWidth-240)+'px';tip.style.top=Math.min(p.y+12,innerHeight-60)+'px';}}
  });
  function nodeVisible(n){
    if(filter.taskOnly&&filter.task&&!filter.task.has(n.id))return false;
    if(filter.domain&&n.domain!==filter.domain)return false;
    if(S.onlyEvolved&&!(n.generation>0))return false;
    if(filter.neighbors&&S.selected&&n.id!==S.selected.id&&!S.edges.some(e=>filter.relations.has(e.type)&&((e.source===S.selected.id&&e.target===n.id)||(e.target===S.selected.id&&e.source===n.id))))return false;
    return true;
  }
  function refresh(){
    $('graph-neighbors').disabled=!S.selected;
    if(!S.selected){filter.neighbors=false;$('graph-neighbors').checked=false;}
    visibleIds=new Set(S.nodes.filter(nodeVisible).map(n=>n.id));
    sphere.setFilter(n=>visibleIds.has(n.id),filter.relations);
    $('graph-visible').textContent=`当前显示 ${visibleIds.size} / ${S.nodes.length} 个技能`;
  }
  function closeCard(){const focused=$('card').contains(document.activeElement);S.selected=null;generation++;sphere.select(null);$('card').classList.remove('show');refresh();if(focused)(selectionFocus?.isConnected?selectionFocus:$('graph-q')).focus({preventScroll:true});}
  async function selectNode(node){
    if(!$('card').contains(document.activeElement))selectionFocus=document.activeElement;
    S.selected=node;sphere.select(node.id);sphere.focus(node.id);
    $('cName').textContent=node.id;$('cDom').textContent=node.domain+' · '+(node.source==='github'?'社区导入 · 尚未执行认证':node.generation>0?'演化资产':'种子资产');
    $('cKv').textContent='历史调用 '+(node.pulls||0)+' 次 · 核验提升积分 +'+Number(node.verified_improvement_points||0).toFixed(2)+'（仅适用已验证版本）';
    $('cRel').innerHTML=S.edges.filter(e=>e.source===node.id||e.target===node.id).map(e=>`<button type="button" data-related="${esc(e.source===node.id?e.target:e.source)}">${esc(e.type)} → ${esc(e.source===node.id?e.target:e.source)}</button>`).join('');
    $('cRel').querySelectorAll('[data-related]').forEach(b=>b.onclick=()=>{const n=S.byId.get(b.dataset.related);if(n){filter.domain='';$('graph-domain').value='';S.onlyEvolved=false;$('btnEvolved').classList.remove('on');$('btnEvolved').setAttribute('aria-pressed','false');selectNode(n);}});
    $('cContractLink').href='/dashboard#skills?skill='+encodeURIComponent(node.id);
    $('card').classList.add('show');$('cName').focus({preventScroll:true});refresh();const current=++generation;$('cContract').textContent='读取能力边界…';
    try{const data=await UI.json('/api/skill/'+encodeURIComponent(node.id));if(current!==generation)return;
      const p=data.passport||{},s=data.skill,list=xs=>(xs||[]).length?`<ul>${xs.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>尚未声明</p>';
      $('cContract').innerHTML=`<small>CAPABILITY PASSPORT / 当前版本声明</small><h4>${esc(p.capability||s.capability||s.description)}</h4><b>何时启用</b>${list(p.activation||s.use_when)}<b>需要的输入 → 预期产物</b>${list(p.inputs||s.inputs)}${list(p.effects||s.outputs)}<b>失效边界与注意事项</b>${list(p.failure_boundary||s.pitfalls)}<b>如何验收</b>${list(p.verification||s.verification)}<p>${esc(p.boundary||'声明不代表已经实测')}</p><details><summary>版本与环境</summary><p>${esc(p.environment||'环境要求未声明')}<br>SHA-256 <code>${esc(p.skill_sha256||'未记录')}</code></p></details>${Product.rewardReceiptHTML(s)}${Product.resourcesButtonHTML(s)}`;
    }catch(e){if(current===generation)$('cContract').textContent=e.message;}
  }
  $('card').querySelector('.close').onclick=closeCard;
  $('graph-domain').onchange=e=>{filter.domain=e.target.value;refresh();};
  document.querySelectorAll('[data-relation]').forEach(input=>input.onchange=()=>{input.checked?filter.relations.add(input.dataset.relation):filter.relations.delete(input.dataset.relation);refresh();});
  $('graph-neighbors').onchange=e=>{filter.neighbors=e.target.checked;refresh();};
  $('graph-task-only').onchange=e=>{filter.taskOnly=e.target.checked;refresh();};
  $('graph-q').oninput=e=>{
    const query=e.target.value.trim().toLowerCase(),host=$('graph-results');
    const matches=query?S.nodes.filter(n=>(n.id+' '+n.domain).toLowerCase().includes(query)).slice(0,20):[];
    host.innerHTML=matches.map(n=>`<button type="button" data-node="${esc(n.id)}">${esc(n.id)}<small>${esc(n.domain)}</small></button>`).join('')||(query?'<p>没有匹配技能</p>':'');
    host.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>{const n=S.byId.get(b.dataset.node);filter.domain='';$('graph-domain').value='';S.onlyEvolved=false;$('btnEvolved').classList.remove('on');$('btnEvolved').setAttribute('aria-pressed','false');filter.taskOnly=false;$('graph-task-only').checked=false;selectNode(n);host.innerHTML='';});
  };
  $('graph-q').onkeydown=e=>{
    if(e.key==='Enter'||e.key==='ArrowDown'){
      const first=$('graph-results').querySelector('[data-node]');
      if(first){e.preventDefault();if(e.key==='Enter')first.click();else first.focus();}
    }
  };
  $('btnZoomIn').onclick=()=>sphere.zoom(1.2);$('btnZoomOut').onclick=()=>sphere.zoom(1/1.2);
  $('btnReset').onclick=()=>{sphere.reset();closeCard();if(run)applyTask();};
  $('btnPause').textContent=matchMedia('(prefers-reduced-motion: reduce)').matches?'继续旋转':'暂停旋转';
  $('btnPause').setAttribute('aria-pressed',String(sphere.snapshot().paused));
  $('btnLabel').setAttribute('aria-pressed',String(S.showLabel));$('btnEvolved').setAttribute('aria-pressed',String(S.onlyEvolved));
  $('btnPause').onclick=()=>sphere.pause();
  $('btnLabel').onclick=e=>{S.showLabel=!S.showLabel;sphere.labels(S.showLabel);e.target.classList.toggle('on',S.showLabel);e.target.setAttribute('aria-pressed',String(S.showLabel));};
  $('btnEvolved').onclick=e=>{S.onlyEvolved=!S.onlyEvolved;e.target.classList.toggle('on',S.onlyEvolved);e.target.setAttribute('aria-pressed',String(S.onlyEvolved));refresh();};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeCard();$('graph-results').innerHTML='';}});
  function applyTask(){
    const steps=(run.steps||[]).filter(s=>s.skill&&s.skill!=='manual'),names=[...new Set([...(run.skills||[]),...steps.map(s=>s.skill)])];
    filter.task=new Set(names);sphere.highlight(names);
    const severity={failed:5,running:4,skipped:3,pending:2,done:1},states=new Map();
    for(const s of steps)if(!states.has(s.skill)||severity[s.status]>severity[states.get(s.skill)])states.set(s.skill,s.status);
    sphere.states(states);$('graph-task-label').hidden=false;
    const missing=names.filter(n=>!S.byId.has(n));
    $('graph-task-note').textContent=`本轮采用 ${names.length} 项 · ${steps.length} 个技能步骤 · ${(run.steps||[]).length-steps.length} 个通用步骤${missing.length?' · '+missing.length+' 项不在当前库':''}。任务高亮是当时采用记录，球体底图是当前目录。`;
    $('graph-capabilities').dataset.run=run.run_id;
    $('graph-run-link').href='/run?id='+encodeURIComponent(run.run_id);$('graph-task-panel').hidden=false;
  }
  (async()=>{try{
    const g=await UI.json('/api/graph');S.nodes=g.nodes||[];S.edges=g.edges||[];S.byId=new Map(S.nodes.map(n=>[n.id,n]));sphere.setData(g);
    window.__GRAPHN__=S.nodes.length;
    const domains=[...new Set(S.nodes.map(n=>n.domain))].sort();$('graph-domain').insertAdjacentHTML('beforeend',domains.map(d=>`<option>${esc(d)}</option>`).join(''));
    $('nN').textContent=S.nodes.length;$('nE').textContent=S.edges.length;$('nD').textContent=domains.length;
    const q=new URLSearchParams(location.search);if(domains.includes(q.get('domain'))){filter.domain=q.get('domain');$('graph-domain').value=filter.domain;}
    if(q.get('run')){try{run=await UI.json('/api/runs/'+encodeURIComponent(q.get('run')));applyTask();}catch(e){UI.toast('任务读取失败：'+e.message);}}
    refresh();if(S.byId.has(q.get('skill'))){filter.domain='';$('graph-domain').value='';selectNode(S.byId.get(q.get('skill')));}
    $('load').hidden=true;$('load').style.display='none';
  }catch(e){$('load').textContent='技能网络读取失败：'+e.message;}})();
  window.__SELFTEST__=()=>({'canvas存在':!!$('cv'),'球体已加载节点':window.__GRAPHN__>0});
})();
