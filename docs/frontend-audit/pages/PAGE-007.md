# PAGE-007 Deployment information

路由 `/runs#system`；源码 `web/app.html`；源码证据 EV-004；运行浏览器证据：该独立 hash 视图未单独运行验收；同文档其它入口证据不能替代。

身份/数据/环境：{"role": "local demo viewer, configured token as required; S1 tenant runtime unavailable", "data": "empty, real stored fixture, long names and hostile filename/text variants", "network": "normal, reordered completion, HTTP failure, reconnect; actual browser interception pending", "viewport": "390×844, 1440×900, 200% zoom; not yet executed", "input": "mouse, touch, keyboard Tab/Enter/Space/Escape; not yet executed", "lifecycle": "initial entry, repeated entry, query change, interruption, back/forward, page hide"}。

## 全部逻辑实例

| CMP | DEF / BP | 定位 | 处置 / TASK | 检查 |
|---|---|---|---|---|
| CMP-071 Page shell/navigation/status | DEF-009 / BP-009 | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro | investigate / TASK-007 | behavior:blocked(CHK-0585); states:blocked(CHK-0586); semantics_accessibility:blocked(CHK-0587); layout_content:blocked(CHK-0588); data_effects:blocked(CHK-0589); security_privacy:blocked(CHK-0590); performance_lifecycle:blocked(CHK-0591); maintainability_integration:passed(CHK-0592) |
| CMP-072 Connection settings and toast | DEF-001 / BP-001 | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions | investigate / TASK-007, TASK-017 | behavior:blocked(CHK-0593); states:blocked(CHK-0594); semantics_accessibility:blocked(CHK-0595); layout_content:blocked(CHK-0596); data_effects:blocked(CHK-0597); security_privacy:blocked(CHK-0598); performance_lifecycle:blocked(CHK-0599); maintainability_integration:passed(CHK-0600); security_privacy:passed(CHK-1287) |
| CMP-073 Current runtime/API/worker details | DEF-013 / BP-013 | web/app.html: sys-meta / sys-body / loadSystem; implementation web/app.html: loadSystem / v-system | investigate / TASK-007, TASK-024 | behavior:blocked(CHK-0601); states:blocked(CHK-0602); semantics_accessibility:blocked(CHK-0603); layout_content:blocked(CHK-0604); data_effects:blocked(CHK-0605); security_privacy:blocked(CHK-0606); performance_lifecycle:blocked(CHK-0607); maintainability_integration:passed(CHK-0608); data_effects:passed(CHK-1308) |
| CMP-074 S1 implementation/production boundary | DEF-013 / BP-013 | web/app.html: v-system; implementation web/app.html: loadSystem / v-system | investigate / TASK-007, TASK-030 | behavior:blocked(CHK-0609); states:blocked(CHK-0610); semantics_accessibility:blocked(CHK-0611); layout_content:blocked(CHK-0612); data_effects:blocked(CHK-0613); security_privacy:blocked(CHK-0614); performance_lifecycle:blocked(CHK-0615); maintainability_integration:passed(CHK-0616) |

每项八维及独立回归的证据/阻塞原因详见对应 CHK。source traceability 通过仅表示来源可追溯；其他运行项没有被自动变为通过。

## 场景

| SCN | 状态 | 操作顺序 | 预期 | 证据/阻塞 |
|---|---|---|---|---|
| SCN-007 Deployment information browser journey and recovery | blocked | Open /runs#system directly and via navigation; use back/forward. → Visit every registered control/template on this view using pointer and Tab/Enter/Space/Escape. → Exercise loading, empty, failure, late response, repeated action and long/untrusted content; recover. → Repeat at 390×844, 1440×900 and 200% zoom; capture scroll, dialog focus, console/network and screenshot evidence. | The user can complete Deployment information without lost state, stale overwrite or duplicate side effects.；All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent.；Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | Partial actual IAB evidence exists for six initial pages at two sizes and selected keyboard/replay interactions. This full-route scenario still lacks complete controls/error/re-entry/network-fault/zoom/accessibility evidence; execute the remaining assertions on a named final deployment. |
| SCN-017 Token clear/close race — bounded Node regression | passed | token validation pending → clear → reject late request → validate new candidate → close → resolve old response | Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.；All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019 |
| SCN-024 Late mission/evaluation/system/health responses overwrite newer state — bounded Node regression | passed | health B completes then health A fails → latest A waits for detail; B completes; A detail fails → evaluation/system B completes; A fails | Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result.；All assertions in tools/frontend_resilience_check.js: centreRequestOwnership pass. | EV-019 |

## 保持与补证

保留原有视觉背景、球体、七阶段和真实运行/跨轮文件契约。该视图运行、键盘焦点、布局和异常恢复均以列出的浏览器 SCN 继续补证；只改可复现问题，不能以其它页面或共享函数单测替代本视图验收。


## CMP-167 能力边界研究界面增量

DEF-032 / BP-032；web/app.html: frontier.js/frontier.css includes; /runs#system #frontier-launch → #frontier-dialog。处置 investigate；TASK TASK-035, TASK-038；SCN SCN-070。

Composite responsibility includes native close/select/execute/evidence-link/details/error/status children; their independent states and actions are explicitly separated by SCN-054..060. Wrappers, cards and text are layout/content of this composite. Shared controlled DOM assertions are not inherited full-page passes; this parent context retains its own blocked scenario.

| CHK | 维度 | 状态 | 证据/范围 |
|---|---|---|---|
| CHK-1515 | behavior | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1516 | states | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1517 | semantics_accessibility | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1518 | layout_content | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1519 | data_effects | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1520 | security_privacy | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1521 | performance_lifecycle | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1522 | maintainability_integration | blocked | Current shared IIFE has controlled DOM logic evidence, but this distinct route/hash parent layout, keyboard/focus, scroll/error/re-entry and browser networking state matrix has not been fully executed. Final v8 named partial observations are being collected separately; screen reader, 200% zoom, performance and production S1 remain blocked. |
| CHK-1523 | maintainability_integration | passed | EV-050 |
