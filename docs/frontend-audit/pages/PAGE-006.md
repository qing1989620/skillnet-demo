# PAGE-006 Evaluation reports

路由 `/runs#eval`；源码 `web/app.html`；源码证据 EV-004；运行浏览器证据：该独立 hash 视图未单独运行验收；同文档其它入口证据不能替代。

身份/数据/环境：{"role": "local demo viewer, configured token as required; S1 tenant runtime unavailable", "data": "empty, real stored fixture, long names and hostile filename/text variants", "network": "normal, reordered completion, HTTP failure, reconnect; actual browser interception pending", "viewport": "390×844, 1440×900, 200% zoom; not yet executed", "input": "mouse, touch, keyboard Tab/Enter/Space/Escape; not yet executed", "lifecycle": "initial entry, repeated entry, query change, interruption, back/forward, page hide"}。

## 全部逻辑实例

| CMP | DEF / BP | 定位 | 处置 / TASK | 检查 |
|---|---|---|---|---|
| CMP-068 Page shell/navigation/status | DEF-009 / BP-009 | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro | investigate / TASK-006 | behavior:blocked(CHK-0557); states:blocked(CHK-0558); semantics_accessibility:blocked(CHK-0559); layout_content:blocked(CHK-0560); data_effects:blocked(CHK-0561); security_privacy:blocked(CHK-0562); performance_lifecycle:blocked(CHK-0563); maintainability_integration:passed(CHK-0564) |
| CMP-069 Connection settings and toast | DEF-001 / BP-001 | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions | investigate / TASK-006, TASK-017 | behavior:blocked(CHK-0565); states:blocked(CHK-0566); semantics_accessibility:blocked(CHK-0567); layout_content:blocked(CHK-0568); data_effects:blocked(CHK-0569); security_privacy:blocked(CHK-0570); performance_lifecycle:blocked(CHK-0571); maintainability_integration:passed(CHK-0572); security_privacy:passed(CHK-1286) |
| CMP-070 Actual experiment/empty/error template | DEF-012 / BP-012 | web/app.html: eval-body / loadEval; implementation web/app.html: loadEval / v-eval | investigate / TASK-006, TASK-024 | behavior:blocked(CHK-0573); states:blocked(CHK-0574); semantics_accessibility:blocked(CHK-0575); layout_content:blocked(CHK-0576); data_effects:blocked(CHK-0577); security_privacy:blocked(CHK-0578); performance_lifecycle:blocked(CHK-0579); maintainability_integration:passed(CHK-0580); data_effects:passed(CHK-1307) |

每项八维及独立回归的证据/阻塞原因详见对应 CHK。source traceability 通过仅表示来源可追溯；其他运行项没有被自动变为通过。

## 场景

| SCN | 状态 | 操作顺序 | 预期 | 证据/阻塞 |
|---|---|---|---|---|
| SCN-006 Evaluation reports browser journey and recovery | blocked | Open /runs#eval directly and via navigation; use back/forward. → Visit every registered control/template on this view using pointer and Tab/Enter/Space/Escape. → Exercise loading, empty, failure, late response, repeated action and long/untrusted content; recover. → Repeat at 390×844, 1440×900 and 200% zoom; capture scroll, dialog focus, console/network and screenshot evidence. | The user can complete Evaluation reports without lost state, stale overwrite or duplicate side effects.；All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent.；Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | Partial actual IAB evidence exists for six initial pages at two sizes and selected keyboard/replay interactions. This full-route scenario still lacks complete controls/error/re-entry/network-fault/zoom/accessibility evidence; execute the remaining assertions on a named final deployment. |
| SCN-017 Token clear/close race — bounded Node regression | passed | token validation pending → clear → reject late request → validate new candidate → close → resolve old response | Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.；All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019 |
| SCN-024 Late mission/evaluation/system/health responses overwrite newer state — bounded Node regression | passed | health B completes then health A fails → latest A waits for detail; B completes; A detail fails → evaluation/system B completes; A fails | Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result.；All assertions in tools/frontend_resilience_check.js: centreRequestOwnership pass. | EV-019 |

## 保持与补证

保留原有视觉背景、球体、七阶段和真实运行/跨轮文件契约。该视图运行、键盘焦点、布局和异常恢复均以列出的浏览器 SCN 继续补证；只改可复现问题，不能以其它页面或共享函数单测替代本视图验收。
