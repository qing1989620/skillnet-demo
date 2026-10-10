/* Exercise the actual homepage renderers and reconnect logic without model calls. */
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const html = fs.readFileSync(path.join(__dirname, "../web/briefing.html"), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace(/^boot\(\);\s*$/m, "")
  .replace(/^loadRunCenter\(\);\s*$/m, "")
  .replace(/^fillLiveNumbers\(\);\s*$/m, "");
const elements = new Map();
const el = id => {
  if (!elements.has(id)) elements.set(id, {style:{},className:"ph",textContent:"",addEventListener(){}});
  return elements.get(id);
};
const document = {getElementById:el,addEventListener(){},querySelectorAll:()=>[]};
const heroCalls = [];
const HeroNet = Object.fromEntries(["highlight","select","dagify","stepState"]
  .map(key=>[key,(...args)=>heroCalls.push([key,...args])]));
const UI = {};
const api = new Function("document","window","location","UI","HeroNet","setTimeout", script+
  "\nreturn {streamRunUntilFinal,wsOnEvent,renderFeedback,renderStage3,renderSandbox,apiBase:API};")(
  document,{HeroNet},{origin:"https://example.test",port:""},UI,HeroNet,
  (fn,ms)=>setTimeout(fn,ms===1000?0:ms));
async function main() {
  assert.equal(api.apiBase,"https://example.test");
  const urls=[],events=[];
  let reads=0;
  UI.consumeSSE = async (url,emit) => {
    urls.push(url);
    if (urls.length===1) { emit({seq:1,type:"retrieval.completed"}); emit({seq:2,type:"ranking.completed"}); }
    else { emit({seq:2,type:"ranking.completed"}); emit({seq:3,type:"run.reply"}); }
  };
  UI.json = async()=>({status:++reads===1?"EXECUTING":"COMPLETED"});
  const final=await api.streamRunUntilFinal("run-1",ev=>events.push(ev.seq));
  assert.equal(final.status,"COMPLETED");
  assert.deepEqual(events,[1,2,3]);
  assert.ok(urls[1].endsWith("/stream?after=2"));
  UI.consumeSSE=async()=>{throw Object.assign(new Error("访问令牌无效"),{status:401});};
  UI.json=async()=>{throw new Error("must not read state after auth failure");};
  await assert.rejects(api.streamRunUntilFinal("protected",()=>{}),/访问令牌无效/);
  api.wsOnEvent(0,{type:"plan.created",data:{steps:2}});
  api.wsOnEvent(0,{type:"dag.ready",data:{nodes:[{index:0}]}});
  assert.equal(el("wsp-0-plan").className,"ph ok");
  api.wsOnEvent(0,{type:"step.started",step:1,data:{}});
  api.wsOnEvent(0,{type:"step.completed",step:1,data:{status:"done"}});
  assert.ok(heroCalls.some(c=>c[0]==="dagify"));
  assert.ok(heroCalls.some(c=>c[0]==="stepState"&&c[1]===1&&c[2]==="done"));
  const unavailable=api.renderStage3({adoption:0,steps:0,judge:{weighted:0,score_valid:false,coverage_valid:false}});
  assert.ok(unavailable.includes("不可用"));
  assert.ok(!unavailable.includes("0.00/10"));
  const feedback={reward:null,accepted:false,library_size:108,skip_reason:"评审不可用",feedback:[]};
  assert.ok(api.renderFeedback(feedback).includes("未写回正式策略参数"));
  assert.ok(api.renderFeedback({...feedback,reward:0,feedback:[{name:"demo",exploit_before:0,exploit_after:0,delta:0}]}).includes("0.00/1.0"));
  const sandbox=api.renderSandbox({step_index:0,final_ok:true,n_attempts:1,attempts:[{n:1,ok:true}],
    artifacts:[{name:"figure.png",bytes:100}]}, "demo",[{name:"step1_figure.png"}]);
  assert.ok(sandbox.includes("/api/artifact/demo/step1_figure.png"));
  const depth = html.slice(html.indexOf("  function dagDepth("), html.indexOf("  function tickDag("));
  const layout = html.slice(html.indexOf("  function layoutDagTargets("), html.indexOf("  window.HeroNet ="));
  const reflow = new Function("dagMode", "W", "H", depth + layout + "\nlayoutDagTargets(); return dagMode.targets;");
  const dag = {nodes:[{idx:0,depends_on:[]},{idx:1,depends_on:[0]},{idx:2,depends_on:[1]}],state:new Map([[1,"done"]])};
  reflow(dag,1440,480);
  const narrow = reflow(dag,340,320);
  assert.equal(narrow.size,3);
  for (const target of narrow.values()) assert.ok(target.x>=0&&target.x<=340&&target.y>=0&&target.y<=320);
  assert.equal(dag.state.get(1),"done");
  assert.equal((html.match(/class="tl-item" data-s="[1-7]"/g)||[]).length,7);
  assert.ok(html.includes('id="heroNet"')&&html.includes('id="demo-seven"')&&html.includes('id="evpanel"'));
  console.log("Homepage flow: replay cursor, auth, phase order, graph events, score validity, artifact URLs and all seven stages passed.");
}
main().catch(error=>{console.error(error);process.exitCode=1;});
