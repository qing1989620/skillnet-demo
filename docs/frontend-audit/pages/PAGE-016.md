# PAGE-016 S1/export laboratory

路由 `/dashboard#adapters`；源码 `web/index.html`；源码证据 EV-007；运行浏览器证据：该独立 hash 视图未单独运行验收；同文档其它入口证据不能替代。

身份/数据/环境：{"role": "local demo viewer, configured token as required; S1 tenant runtime unavailable", "data": "empty, real stored fixture, long names and hostile filename/text variants", "network": "normal, reordered completion, HTTP failure, reconnect; actual browser interception pending", "viewport": "390×844, 1440×900, 200% zoom; not yet executed", "input": "mouse, touch, keyboard Tab/Enter/Space/Escape; not yet executed", "lifecycle": "initial entry, repeated entry, query change, interruption, back/forward, page hide"}。

## 全部逻辑实例

| CMP | DEF / BP | 定位 | 处置 / TASK | 检查 |
|---|---|---|---|---|
| CMP-147 Page shell/navigation/status | DEF-016 / BP-016 | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show | investigate / TASK-016 | behavior:blocked(CHK-1229); states:blocked(CHK-1230); semantics_accessibility:blocked(CHK-1231); layout_content:blocked(CHK-1232); data_effects:blocked(CHK-1233); security_privacy:blocked(CHK-1234); performance_lifecycle:blocked(CHK-1235); maintainability_integration:passed(CHK-1236) |
| CMP-148 Connection settings and toast | DEF-001 / BP-001 | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions | investigate / TASK-016, TASK-017 | behavior:blocked(CHK-1237); states:blocked(CHK-1238); semantics_accessibility:blocked(CHK-1239); layout_content:blocked(CHK-1240); data_effects:blocked(CHK-1241); security_privacy:blocked(CHK-1242); performance_lifecycle:blocked(CHK-1243); maintainability_integration:passed(CHK-1244); security_privacy:passed(CHK-1296) |
| CMP-149 S1 service contract | DEF-023 / BP-023 | web/index.html: s1-contract; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live | investigate / TASK-016, TASK-030 | behavior:blocked(CHK-1245); states:blocked(CHK-1246); semantics_accessibility:blocked(CHK-1247); layout_content:blocked(CHK-1248); data_effects:blocked(CHK-1249); security_privacy:blocked(CHK-1250); performance_lifecycle:blocked(CHK-1251); maintainability_integration:passed(CHK-1252) |
| CMP-150 Export action | DEF-023 / BP-023 | web/index.html: adapterBtn; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live | investigate / TASK-016 | behavior:blocked(CHK-1253); states:blocked(CHK-1254); semantics_accessibility:blocked(CHK-1255); layout_content:blocked(CHK-1256); data_effects:blocked(CHK-1257); security_privacy:blocked(CHK-1258); performance_lifecycle:blocked(CHK-1259); maintainability_integration:passed(CHK-1260) |
| CMP-151 Export result/error template | DEF-023 / BP-023 | web/index.html: adapterOut; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live | investigate / TASK-016 | behavior:blocked(CHK-1261); states:blocked(CHK-1262); semantics_accessibility:blocked(CHK-1263); layout_content:blocked(CHK-1264); data_effects:blocked(CHK-1265); security_privacy:blocked(CHK-1266); performance_lifecycle:blocked(CHK-1267); maintainability_integration:passed(CHK-1268) |
| CMP-152 Live laboratory status | DEF-023 / BP-023 | web/index.html: lab-status / laboratory-live; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live | investigate / TASK-016 | behavior:blocked(CHK-1269); states:blocked(CHK-1270); semantics_accessibility:blocked(CHK-1271); layout_content:blocked(CHK-1272); data_effects:blocked(CHK-1273); security_privacy:blocked(CHK-1274); performance_lifecycle:blocked(CHK-1275); maintainability_integration:passed(CHK-1276) |

每项八维及独立回归的证据/阻塞原因详见对应 CHK。source traceability 通过仅表示来源可追溯；其他运行项没有被自动变为通过。

## 场景

| SCN | 状态 | 操作顺序 | 预期 | 证据/阻塞 |
|---|---|---|---|---|
| SCN-016 S1/export laboratory browser journey and recovery | blocked | Open /dashboard#adapters directly and via navigation; use back/forward. → Visit every registered control/template on this view using pointer and Tab/Enter/Space/Escape. → Exercise loading, empty, failure, late response, repeated action and long/untrusted content; recover. → Repeat at 390×844, 1440×900 and 200% zoom; capture scroll, dialog focus, console/network and screenshot evidence. | The user can complete S1/export laboratory without lost state, stale overwrite or duplicate side effects.；All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent.；Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | Partial actual IAB evidence exists for six initial pages at two sizes and selected keyboard/replay interactions. This full-route scenario still lacks complete controls/error/re-entry/network-fault/zoom/accessibility evidence; execute the remaining assertions on a named final deployment. |
| SCN-017 Token clear/close race — bounded Node regression | passed | token validation pending → clear → reject late request → validate new candidate → close → resolve old response | Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.；All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019 |

## 保持与补证

保留原有视觉背景、球体、七阶段和真实运行/跨轮文件契约。该视图运行、键盘焦点、布局和异常恢复均以列出的浏览器 SCN 继续补证；只改可复现问题，不能以其它页面或共享函数单测替代本视图验收。
