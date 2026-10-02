/* 前端渲染自检。
 *
 * 为什么需要它：Dashboard 是单文件原生 JS，其中技能关系图是手写的力导向布局，
 * 语法检查（node --check）发现不了运行期错误。这里用 mock DOM 直接执行
 * web/index.html 里的脚本，喂入真实接口数据快照，验证渲染函数不抛异常且产出预期结构。
 *
 * 用法：
 *     node tools/front_check.js
 * 数据快照位于 tools/fixtures/（由 API 抓取一次后固定，保证可复现）。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const FIX = path.join(__dirname, 'fixtures');

function loadJSON(name) {
  const p = path.join(FIX, name);
  if (!fs.existsSync(p)) throw new Error(`缺少数据快照 ${p}`);
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

const html = fs.readFileSync(path.join(ROOT, 'web', 'index.html'), 'utf8');
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) throw new Error('未在 index.html 中找到 <script> 块');
const code = m[1];

/* ---------- mock DOM ---------- */
const captured = {};
function mkEl(id) {
  const el = {
    _id: id, _html: '', value: '', textContent: '',
    dataset: {}, style: {}, disabled: false,
    classList: { toggle() {}, contains() { return false; }, add() {}, remove() {} },
    set innerHTML(v) { el._html = v; captured[id] = v; },
    get innerHTML() { return el._html; },
    onclick: null, onchange: null, oninput: null,
    insertAdjacentHTML() {},
  };
  return el;
}
const mockDocument = {
  querySelector: (s) => mkEl(s),
  querySelectorAll: () => [],
  body: { insertAdjacentHTML() {} },
};
const mockFetch = async () => ({ ok: true, json: async () => ({}) });

// 去掉自动启动，避免测试时发起真实网络请求
const patched = code.replace(/^boot\(\);\s*$/m, '');

const factory = new Function(
  'document', 'fetch', 'window',
  patched + `
  return {renderGraph, renderMeta, renderDomains, renderQuality, renderPipeline,
          renderRefs, recallOf, esc, pct, num};`
);
const api = factory(mockDocument, mockFetch, {});

const graph = loadJSON('graph.json');
const stats = loadJSON('stats.json');

const results = [];
function t(name, fn) {
  try {
    const d = fn();
    results.push([name, true]);
    console.log('  PASS ', name, d || '');
  } catch (e) {
    results.push([name, false]);
    console.log('  FAIL ', name, e.message);
  }
}

t('渲染函数全套执行（注入真实数据）', () => {
  const run = new Function(
    'document', 'fetch', 'window',
    patched
    + '\nGRAPH = ' + JSON.stringify(graph) + ';\n'
    + 'STATS = ' + JSON.stringify(stats) + ';\n'
    + 'renderMeta(); renderDomains(); renderQuality(); renderPipeline(); renderRefs(); renderGraph();\n'
    + 'return 1;'
  );
  run(mockDocument, mockFetch, {});
  const svg = captured['#graph'] || '';
  if (!svg.includes('<svg ')) throw new Error('未生成 SVG');
  const circles = (svg.match(/<circle/g) || []).length;
  const lines = (svg.match(/<line/g) || []).length;
  if (circles !== graph.nodes.length) {
    throw new Error(`节点数不符: ${circles} vs ${graph.nodes.length}`);
  }
  if (lines === 0) throw new Error('未生成关系边');
  if (!svg.includes('<title>')) throw new Error('节点缺少悬停提示');
  if (!captured['#metabar'] || !captured['#domains'] || !captured['#refs']) {
    throw new Error('概览区渲染不完整');
  }
  return `SVG 节点 ${circles} / 连线 ${lines}；概览各区块均已生成`;
});

t('recallOf 计算正确', () => {
  const r = api.recallOf(['a', 'b', 'c'], ['a', 'b', 'x', 'y']);
  if (Math.abs(r - 0.5) > 1e-9) throw new Error('recall 计算错误: ' + r);
  return '命中 2/4 = 0.5';
});

t('recallOf 处理空 gold', () => {
  if (api.recallOf(['a'], []) !== null) throw new Error('空 gold 应返回 null');
  return '返回 null（不误报 0）';
});

t('pct / num 格式化与 null 安全', () => {
  if (api.pct(0.967) !== '96.7%') throw new Error('pct 异常: ' + api.pct(0.967));
  if (api.num(1.2345, 2) !== '1.23') throw new Error('num 异常');
  if (api.pct(null) !== '—') throw new Error('pct(null) 异常');
  return '百分比/数值格式化正确';
});

t('esc 防 XSS 转义', () => {
  const s = api.esc('<script>alert("x")</script>');
  if (s.includes('<script>')) throw new Error('未转义: ' + s);
  return '危险字符已转义';
});

const failed = results.filter(r => !r[1]);
console.log(`\n前端渲染自检：${results.length - failed.length}/${results.length} 通过`);
process.exit(failed.length ? 1 : 0);
