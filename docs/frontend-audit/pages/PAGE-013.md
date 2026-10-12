# PAGE-013 Retrieval/routing laboratory

路由 `/dashboard#search`；源码 `web/index.html`；源码证据 EV-007；运行浏览器证据：该独立 hash 视图未单独运行验收；同文档其它入口证据不能替代。

身份/数据/环境：{"role": "local demo viewer, configured token as required; S1 tenant runtime unavailable", "data": "empty, real stored fixture, long names and hostile filename/text variants", "network": "normal, reordered completion, HTTP failure, reconnect; actual browser interception pending", "viewport": "390×844, 1440×900, 200% zoom; not yet executed", "input": "mouse, touch, keyboard Tab/Enter/Space/Escape; not yet executed", "lifecycle": "initial entry, repeated entry, query change, interruption, back/forward, page hide"}。

## 全部逻辑实例

| CMP | DEF / BP | 定位 | 处置 / TASK | 检查 |
|---|---|---|---|---|
| CMP-130 Page shell/navigation/status | DEF-016 / BP-016 | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show | investigate / TASK-013 | behavior:blocked(CHK-1081); states:blocked(CHK-1082); semantics_accessibility:blocked(CHK-1083); layout_content:blocked(CHK-1084); data_effects:blocked(CHK-1085); security_privacy:blocked(CHK-1086); performance_lifecycle:blocked(CHK-1087); maintainability_integration:passed(CHK-1088) |
| CMP-131 Connection settings and toast | DEF-001 / BP-001 | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions | investigate / TASK-013, TASK-017 | behavior:blocked(CHK-1089); states:blocked(CHK-1090); semantics_accessibility:blocked(CHK-1091); layout_content:blocked(CHK-1092); data_effects:blocked(CHK-1093); security_privacy:blocked(CHK-1094); performance_lifecycle:blocked(CHK-1095); maintainability_integration:passed(CHK-1096); security_privacy:passed(CHK-1293) |
| CMP-132 Query/task/top-K inputs | DEF-020 / BP-020 | web/index.html: searchQ / searchTask / searchK; implementation web/index.html: doSearch / doRoute / searchOut / routeOut | investigate / TASK-013 | behavior:blocked(CHK-1097); states:blocked(CHK-1098); semantics_accessibility:blocked(CHK-1099); layout_content:blocked(CHK-1100); data_effects:blocked(CHK-1101); security_privacy:blocked(CHK-1102); performance_lifecycle:blocked(CHK-1103); maintainability_integration:passed(CHK-1104) |
| CMP-133 Search action | DEF-020 / BP-020 | web/index.html: searchBtn; implementation web/index.html: doSearch / doRoute / searchOut / routeOut | investigate / TASK-013 | behavior:blocked(CHK-1105); states:blocked(CHK-1106); semantics_accessibility:blocked(CHK-1107); layout_content:blocked(CHK-1108); data_effects:blocked(CHK-1109); security_privacy:blocked(CHK-1110); performance_lifecycle:blocked(CHK-1111); maintainability_integration:passed(CHK-1112) |
| CMP-134 Three-channel search results | DEF-020 / BP-020 | web/index.html: searchOut; implementation web/index.html: doSearch / doRoute / searchOut / routeOut | investigate / TASK-013 | behavior:blocked(CHK-1113); states:blocked(CHK-1114); semantics_accessibility:blocked(CHK-1115); layout_content:blocked(CHK-1116); data_effects:blocked(CHK-1117); security_privacy:blocked(CHK-1118); performance_lifecycle:blocked(CHK-1119); maintainability_integration:passed(CHK-1120) |
| CMP-135 Routing query input | DEF-020 / BP-020 | web/index.html: routeQ; implementation web/index.html: doSearch / doRoute / searchOut / routeOut | investigate / TASK-013 | behavior:blocked(CHK-1121); states:blocked(CHK-1122); semantics_accessibility:blocked(CHK-1123); layout_content:blocked(CHK-1124); data_effects:blocked(CHK-1125); security_privacy:blocked(CHK-1126); performance_lifecycle:blocked(CHK-1127); maintainability_integration:passed(CHK-1128) |
| CMP-136 Routing action/result | DEF-020 / BP-020 | web/index.html: routeBtn / routeOut; implementation web/index.html: doSearch / doRoute / searchOut / routeOut | investigate / TASK-013 | behavior:blocked(CHK-1129); states:blocked(CHK-1130); semantics_accessibility:blocked(CHK-1131); layout_content:blocked(CHK-1132); data_effects:blocked(CHK-1133); security_privacy:blocked(CHK-1134); performance_lifecycle:blocked(CHK-1135); maintainability_integration:passed(CHK-1136) |

每项八维及独立回归的证据/阻塞原因详见对应 CHK。source traceability 通过仅表示来源可追溯；其他运行项没有被自动变为通过。

## 场景

| SCN | 状态 | 操作顺序 | 预期 | 证据/阻塞 |
|---|---|---|---|---|
| SCN-013 Retrieval/routing laboratory browser journey and recovery | blocked | Open /dashboard#search directly and via navigation; use back/forward. → Visit every registered control/template on this view using pointer and Tab/Enter/Space/Escape. → Exercise loading, empty, failure, late response, repeated action and long/untrusted content; recover. → Repeat at 390×844, 1440×900 and 200% zoom; capture scroll, dialog focus, console/network and screenshot evidence. | The user can complete Retrieval/routing laboratory without lost state, stale overwrite or duplicate side effects.；All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent.；Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | Partial actual IAB evidence exists for six initial pages at two sizes and selected keyboard/replay interactions. This full-route scenario still lacks complete controls/error/re-entry/network-fault/zoom/accessibility evidence; execute the remaining assertions on a named final deployment. |
| SCN-017 Token clear/close race — bounded Node regression | passed | token validation pending → clear → reject late request → validate new candidate → close → resolve old response | Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.；All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019 |

## 保持与补证

保留原有视觉背景、球体、七阶段和真实运行/跨轮文件契约。该视图运行、键盘焦点、布局和异常恢复均以列出的浏览器 SCN 继续补证；只改可复现问题，不能以其它页面或共享函数单测替代本视图验收。
