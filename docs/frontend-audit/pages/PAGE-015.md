# PAGE-015 Historical results

路由 `/dashboard#results`；源码 `web/index.html`；源码证据 EV-007；运行浏览器证据：该独立 hash 视图未单独运行验收；同文档其它入口证据不能替代。

身份/数据/环境：{"role": "local demo viewer, configured token as required; S1 tenant runtime unavailable", "data": "empty, real stored fixture, long names and hostile filename/text variants", "network": "normal, reordered completion, HTTP failure, reconnect; actual browser interception pending", "viewport": "390×844, 1440×900, 200% zoom; not yet executed", "input": "mouse, touch, keyboard Tab/Enter/Space/Escape; not yet executed", "lifecycle": "initial entry, repeated entry, query change, interruption, back/forward, page hide"}。

## 全部逻辑实例

| CMP | DEF / BP | 定位 | 处置 / TASK | 检查 |
|---|---|---|---|---|
| CMP-144 Page shell/navigation/status | DEF-016 / BP-016 | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show | investigate / TASK-015 | behavior:blocked(CHK-1201); states:blocked(CHK-1202); semantics_accessibility:blocked(CHK-1203); layout_content:blocked(CHK-1204); data_effects:blocked(CHK-1205); security_privacy:blocked(CHK-1206); performance_lifecycle:blocked(CHK-1207); maintainability_integration:passed(CHK-1208) |
| CMP-145 Connection settings and toast | DEF-001 / BP-001 | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions | investigate / TASK-015, TASK-017 | behavior:blocked(CHK-1209); states:blocked(CHK-1210); semantics_accessibility:blocked(CHK-1211); layout_content:blocked(CHK-1212); data_effects:blocked(CHK-1213); security_privacy:blocked(CHK-1214); performance_lifecycle:blocked(CHK-1215); maintainability_integration:passed(CHK-1216); security_privacy:passed(CHK-1295) |
| CMP-146 Actual result/empty/error template | DEF-022 / BP-022 | web/index.html: resultsOut; implementation web/index.html: resultsOut / renderResults | investigate / TASK-015 | behavior:blocked(CHK-1217); states:blocked(CHK-1218); semantics_accessibility:blocked(CHK-1219); layout_content:blocked(CHK-1220); data_effects:blocked(CHK-1221); security_privacy:blocked(CHK-1222); performance_lifecycle:blocked(CHK-1223); maintainability_integration:passed(CHK-1224) |

每项八维及独立回归的证据/阻塞原因详见对应 CHK。source traceability 通过仅表示来源可追溯；其他运行项没有被自动变为通过。

## 场景

| SCN | 状态 | 操作顺序 | 预期 | 证据/阻塞 |
|---|---|---|---|---|
| SCN-015 Historical results browser journey and recovery | blocked | Open /dashboard#results directly and via navigation; use back/forward. → Visit every registered control/template on this view using pointer and Tab/Enter/Space/Escape. → Exercise loading, empty, failure, late response, repeated action and long/untrusted content; recover. → Repeat at 390×844, 1440×900 and 200% zoom; capture scroll, dialog focus, console/network and screenshot evidence. | The user can complete Historical results without lost state, stale overwrite or duplicate side effects.；All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent.；Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | Partial actual IAB evidence exists for six initial pages at two sizes and selected keyboard/replay interactions. This full-route scenario still lacks complete controls/error/re-entry/network-fault/zoom/accessibility evidence; execute the remaining assertions on a named final deployment. |
| SCN-017 Token clear/close race — bounded Node regression | passed | token validation pending → clear → reject late request → validate new candidate → close → resolve old response | Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.；All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019 |

## 保持与补证

保留原有视觉背景、球体、七阶段和真实运行/跨轮文件契约。该视图运行、键盘焦点、布局和异常恢复均以列出的浏览器 SCN 继续补证；只改可复现问题，不能以其它页面或共享函数单测替代本视图验收。


## CMP-175 能力边界研究界面增量

DEF-032 / BP-032；web/index.html: frontier.js/frontier.css includes; /dashboard#results #frontier-launch → #frontier-dialog。处置 investigate；TASK TASK-035, TASK-038；SCN SCN-078。

Composite responsibility includes native close/select/execute/evidence-link/details/error/status children; their independent states and actions are explicitly separated by SCN-054..060. Wrappers, cards and text are layout/content of this composite. Shared controlled DOM assertions are not inherited full-page passes; this parent context retains its own blocked scenario.

| CHK | 维度 | 状态 | 证据/范围 |
|---|---|---|---|
| CHK-1587 | behavior | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1588 | states | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1589 | semantics_accessibility | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1590 | layout_content | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1591 | data_effects | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1592 | security_privacy | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1593 | performance_lifecycle | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1594 | maintainability_integration | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1595 | maintainability_integration | passed | EV-050 |
