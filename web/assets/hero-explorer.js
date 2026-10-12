/* The hero explores the actual catalogue. Locations and relation counts are
 * navigation aids; declarations never certify an executable capability. */
(function(root){
  'use strict';
  function graphURL(skill,domain){
    const query=new URLSearchParams();
    if(skill)query.set('skill',skill);
    if(domain)query.set('domain',domain);
    return '/graph'+(query.size?'?'+query.toString():'');
  }
  function catalogue(data){
    const nodes=[],byId=new Map(),domains=new Map();
    for(const node of Array.isArray(data?.nodes)?data.nodes:[]){
      if(!node||typeof node.id!=='string'||!node.id||byId.has(node.id))continue;
      const item={...node,domain:typeof node.domain==='string'?node.domain:''};
      nodes.push(item);byId.set(item.id,item);domains.set(item.domain,(domains.get(item.domain)||0)+1);
    }
    const edges=(Array.isArray(data?.edges)?data.edges:[]).filter(e=>e&&byId.has(e.source)&&byId.has(e.target));
    return {nodes,byId,edges,domains:[...domains].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))};
  }
  function mount(options){
    const {host,sphere,graphLink}=options,doc=root.document;
    let data=catalogue({}),domain='',selected=null,detailEpoch=0,controller=null,timer=null,destroyed=false,suspended=false,selectionFocus=null;
    const cleanups=[];
    const listen=(el,type,fn)=>{el.addEventListener(type,fn);cleanups.push(()=>el.removeEventListener(type,fn));};
    const node=(tag,className,text)=>{const el=doc.createElement(tag);if(className)el.className=className;if(text!=null)el.textContent=text;return el;};
    const heading=node('div','hero-explorer-heading');
    heading.append(node('span','','探索真实能力'));
    const scope=node('p','hero-explorer-scope','正在读取技能目录…');scope.id='hero-explorer-scope';scope.setAttribute('role','status');heading.append(scope);
    const retryCatalogue=node('button','hero-catalogue-retry','重试读取目录');retryCatalogue.type='button';retryCatalogue.hidden=true;
    const legend=node('div','hero-domain-choices');legend.id='netlegend';legend.setAttribute('role','group');legend.setAttribute('aria-label','聚焦真实技能领域');
    const searchPanel=node('details','hero-search-panel'),searchToggle=node('summary','','搜索全部技能');searchPanel.append(searchToggle);
    const form=node('div','hero-search-row'),label=node('label','','搜索并定位技能');label.setAttribute('for','hero-skill-search');
    const input=node('input');input.id='hero-skill-search';input.type='search';input.autocomplete='off';input.placeholder='输入技能名称或领域';input.disabled=true;
    input.setAttribute('aria-controls','hero-skill-results');input.setAttribute('aria-describedby','hero-search-hint');
    const hint=node('p','hero-search-hint','方向键向下进入结果，Enter 选择，Esc 收起。');hint.id='hero-search-hint';
    form.append(label,input);
    const results=node('ul','hero-search-results');results.id='hero-skill-results';results.hidden=true;
    const searchStatus=node('p','hero-search-status');searchStatus.setAttribute('role','status');searchStatus.hidden=true;
    const card=node('div','hero-skill-card');card.hidden=true;card.setAttribute('role','region');card.setAttribute('aria-labelledby','hero-skill-name');
    const cardHead=node('div','hero-skill-heading'),title=node('h3');title.id='hero-skill-name';title.tabIndex=-1;
    const close=node('button','hero-skill-close','×');close.type='button';close.setAttribute('aria-label','收起所选技能');cardHead.append(title,close);
    const source=node('p','hero-skill-source'),purpose=node('p','hero-skill-purpose'),relations=node('p','hero-skill-relations');
    purpose.setAttribute('role','status');
    const actions=node('div','hero-skill-actions'),passport=node('button','','查看适用条件与失效边界 ↗');passport.type='button';passport.setAttribute('aria-haspopup','dialog');
    const retry=node('button','','重试读取用途');retry.type='button';retry.hidden=true;
    const inspect=node('a','','在完整球体中探索 ↗');
    actions.append(passport,retry,inspect);
    card.append(cardHead,source,purpose,relations,actions,node('p','hero-skill-boundary','这是当前技能声明。被检索、有关联或曾被调用，都不证明当前版本已通过执行认证。'));
    searchPanel.append(form,hint,results,searchStatus);host.append(heading,retryCatalogue,legend,searchPanel,card);
    function stopRequest(){detailEpoch++;if(timer!==null)root.clearTimeout(timer);timer=null;controller?.abort();controller=null;}
    function updateLink(){graphLink.href=graphURL(selected?.id,domain);inspect.href=graphURL(selected?.id,domain);}
    function updateScope(){scope.textContent=domain?`${domain||'未分类'} · ${data.domains.find(([d])=>d===domain)?.[1]||0} / ${data.nodes.length} 个技能`:`全部领域 · ${data.nodes.length} 个真实技能`;}
    function paintLegend(){
      const restore=legend.contains(doc.activeElement);
      const choices=[['',data.nodes.length],...data.domains.filter(([name])=>name).slice(0,4)];
      legend.replaceChildren();
      for(const [name,count] of choices){
        const button=node('button','hero-domain',`${name||'全部'} ${count}`);button.type='button';button.setAttribute('aria-pressed',String(domain===name));button.setAttribute('aria-label',`${name||'全部领域'}，${count} 个技能`);
        button.setAttribute('data-hero-domain',name);
        if(name){const dot=node('i');dot.setAttribute('aria-hidden','true');dot.style.background=root.SkillSphere?.color(name)||'#98e6cf';button.prepend(dot);}
        legend.append(button);if(restore&&domain===name)button.focus({preventScroll:true});
      }
    }
    function clearResults(){results.replaceChildren();results.hidden=true;searchStatus.hidden=true;}
    function closeSelection(restore=true){
      const contained=card.contains(doc.activeElement);
      stopRequest();selected=null;card.hidden=true;sphere.select(null);updateLink();
      const fallback=searchPanel.open?input:(options.canvas||graphLink);
      if(restore&&contained)(selectionFocus?.isConnected&&selectionFocus!==doc.body?selectionFocus:fallback).focus({preventScroll:true});
    }
    function setDomain(value){
      if(destroyed||suspended)return;
      const previous=domain;domain=data.domains.some(([name])=>name===value)?value:'';
      closeSelection(false);input.value='';clearResults();
      sphere.highlight([]);sphere.setFilter(n=>!domain||n.domain===domain);
      if(domain){
        const members=data.nodes.filter(n=>n.domain===domain),counts=new Map(members.map(n=>[n.id,0]));
        for(const edge of data.edges){if(counts.has(edge.source))counts.set(edge.source,counts.get(edge.source)+1);if(counts.has(edge.target))counts.set(edge.target,counts.get(edge.target)+1);}
        members.sort((a,b)=>counts.get(b.id)-counts.get(a.id)||a.id.localeCompare(b.id));
        if(members.length){sphere.focus(members[0].id);sphere.select(null);}
      }else if(previous)sphere.reset();
      searchToggle.textContent=domain?'在此领域搜索技能':'搜索全部技能';paintLegend();updateScope();updateLink();
    }
    function showError(message){purpose.textContent=message;purpose.dataset.state='error';retry.hidden=false;}
    async function loadDetails(item){
      stopRequest();const epoch=detailEpoch;controller=new AbortController();
      purpose.textContent='正在读取当前技能的用途声明…';purpose.dataset.state='loading';retry.hidden=true;
      timer=root.setTimeout(()=>{if(epoch!==detailEpoch||destroyed)return;stopRequest();showError('用途读取超时，可重试；球体与来源信息仍可浏览。');},12000);
      try{
        const response=await (options.request||root.UI.json)('/api/skill/'+encodeURIComponent(item.id),{signal:controller.signal});
        if(epoch!==detailEpoch||destroyed||selected?.id!==item.id||suspended)return;
        if(!response?.skill||response.skill.name!==item.id||(response.passport?.name&&response.passport.name!==item.id))throw new Error('返回的技能与当前选择不一致，请重试。');
        purpose.textContent=String(response.passport?.capability||response.skill.capability||response.skill.description||'当前版本尚未声明具体用途。');purpose.dataset.state='ready';
      }catch(error){if(epoch===detailEpoch&&!destroyed&&selected?.id===item.id&&!suspended)showError('用途读取失败：'+(error.message||'请重试。'));}
      finally{if(epoch===detailEpoch){if(timer!==null)root.clearTimeout(timer);timer=null;controller=null;}}
    }
    function select(item,toggle=false){
      if(destroyed||suspended)return;
      const current=data.byId.get(typeof item==='string'?item:item?.id);
      if(!current||(toggle&&selected?.id===current.id)){closeSelection();return;}
      if(!card.contains(doc.activeElement))selectionFocus=doc.activeElement;
      if(domain&&current.domain!==domain){domain='';sphere.setFilter(()=>true);paintLegend();updateScope();searchToggle.textContent='搜索全部技能';}
      selected=current;clearResults();input.value='';
      sphere.select(current.id);sphere.focus(current.id);card.hidden=false;title.textContent=current.id;
      source.textContent=`${current.domain||'未分类'} · ${current.source==='github'?'社区导入 · 来源不代表执行认证':current.generation>0?'演化来源 · 当前版本仍需验证':'种子资产 · 声明仍需实测'}`;
      const links=data.edges.filter(e=>e.source===current.id||e.target===current.id),counts=type=>links.filter(e=>e.type===type).length;
      relations.textContent=`${links.length} 条登记关系 · 依赖 ${counts('depend_on')} / 组合 ${counts('compose_with')} / 相似 ${counts('similar_to')}`;
      passport.setAttribute('data-capability-skill',current.id);updateLink();title.focus({preventScroll:true});loadDetails(current);
    }
    function search(){
      clearResults();const query=input.value.trim().toLowerCase();if(!query)return;
      const matches=data.nodes.filter(n=>(!domain||n.domain===domain)&&(n.id+' '+n.domain).toLowerCase().includes(query));
      searchStatus.hidden=false;searchStatus.textContent=matches.length?`找到 ${matches.length} 个技能${matches.length>8?'，先显示前 8 个，可继续输入缩小范围':''}。`:'没有匹配技能，可调整关键词或切回全部领域。';
      for(const item of matches.slice(0,8)){
        const li=node('li'),button=node('button');button.type='button';button.setAttribute('data-hero-skill',item.id);button.append(node('span','',item.id),node('small','',item.domain||'未分类'));
        li.append(button);results.append(li);
      }
      results.hidden=!matches.length;
    }
    listen(legend,'click',event=>{const button=event.target.closest('[data-hero-domain]');if(button&&legend.contains(button)){const name=button.getAttribute('data-hero-domain');setDomain(domain===name?'':name);}});
    listen(results,'click',event=>{const button=event.target.closest('[data-hero-skill]');if(button&&results.contains(button))select(button.getAttribute('data-hero-skill'));});
    listen(input,'input',search);
    listen(input,'keydown',event=>{if(['Enter','ArrowDown'].includes(event.key)){const first=results.querySelector('button');if(first){event.preventDefault();event.key==='Enter'?first.click():first.focus();}}else if(event.key==='Escape'){event.preventDefault();input.value='';clearResults();closeSelection(false);}});
    listen(results,'keydown',event=>{const buttons=[...results.querySelectorAll('button')],at=buttons.indexOf(doc.activeElement);if(event.key==='Escape'){event.preventDefault();clearResults();input.focus();}else if(['ArrowDown','ArrowUp'].includes(event.key)&&at>=0){event.preventDefault();buttons[Math.max(0,Math.min(buttons.length-1,at+(event.key==='ArrowDown'?1:-1)))].focus();}});
    listen(close,'click',()=>closeSelection());listen(retry,'click',()=>{if(selected)loadDetails(selected);});
    listen(retryCatalogue,'click',async()=>{if(!options.reload||retryCatalogue.disabled||destroyed)return;retryCatalogue.disabled=true;try{await options.reload();}catch(error){if(!destroyed){scope.textContent='能力目录读取失败：'+(error.message||String(error));}}finally{if(!destroyed)retryCatalogue.disabled=false;}});
    listen(host,'keydown',event=>{if(event.key==='Escape'&&selected&&!event.defaultPrevented){event.preventDefault();closeSelection();}});
    listen(root,'pagehide',()=>{const pending=!!controller;stopRequest();if(pending&&selected&&!destroyed)showError('用途读取已暂停，可在返回后重试。');});
    return {
      select,
      setData(value){if(destroyed)return;stopRequest();data=catalogue(value);domain='';closeSelection(false);input.value='';clearResults();input.disabled=!data.nodes.length;retryCatalogue.hidden=true;searchToggle.textContent='搜索全部 '+data.nodes.length+' 个技能';paintLegend();updateScope();sphere.setFilter(()=>true);updateLink();},
      failed(error){if(destroyed)return;stopRequest();input.disabled=true;scope.textContent='能力目录读取失败：'+(error?.message||String(error));legend.replaceChildren();retryCatalogue.hidden=!options.reload;},
      suspend(value){if(destroyed)return;suspended=!!value;if(suspended&&host.contains(doc.activeElement))graphLink.focus({preventScroll:true});host.hidden=suspended;if(suspended){closeSelection(false);clearResults();}else {sphere.setFilter(n=>!domain||n.domain===domain);updateScope();}},
      destroy(){if(destroyed)return;destroyed=true;stopRequest();cleanups.splice(0).forEach(fn=>fn());},
      snapshot(){return {domain,selected:selected?.id||null,nodes:data.nodes.length,suspended};}
    };
  }
  const api={mount,catalogue,graphURL};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.HeroExplorer=api;
})(typeof window==='undefined'?globalThis:window);
