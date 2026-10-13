# PAGE-013 Retrieval/routing laboratory

Route `/dashboard#search`; source `web/index.html`; entry evidence EV-007, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-130 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013 | behavior:blocked(CHK-1081); states:blocked(CHK-1082); semantics_accessibility:blocked(CHK-1083); layout_content:blocked(CHK-1084); data_effects:blocked(CHK-1085); security_privacy:blocked(CHK-1086); performance_lifecycle:blocked(CHK-1087); maintainability_integration:passed(CHK-1088) |
| CMP-131 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013, TASK-017 | behavior:blocked(CHK-1089); states:blocked(CHK-1090); semantics_accessibility:blocked(CHK-1091); layout_content:blocked(CHK-1092); data_effects:blocked(CHK-1093); security_privacy:blocked(CHK-1094); performance_lifecycle:blocked(CHK-1095); maintainability_integration:passed(CHK-1096); security_privacy:passed(CHK-1293) |
| CMP-132 Query/task/top-K inputs | DEF-020 / BP-020 | page | web/index.html: searchQ / searchTask / searchK; implementation web/index.html: doSearch / doRoute / searchOut / routeOut; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013 | behavior:blocked(CHK-1097); states:blocked(CHK-1098); semantics_accessibility:blocked(CHK-1099); layout_content:blocked(CHK-1100); data_effects:blocked(CHK-1101); security_privacy:blocked(CHK-1102); performance_lifecycle:blocked(CHK-1103); maintainability_integration:passed(CHK-1104) |
| CMP-133 Search action | DEF-020 / BP-020 | page | web/index.html: searchBtn; implementation web/index.html: doSearch / doRoute / searchOut / routeOut; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013 | behavior:blocked(CHK-1105); states:blocked(CHK-1106); semantics_accessibility:blocked(CHK-1107); layout_content:blocked(CHK-1108); data_effects:blocked(CHK-1109); security_privacy:blocked(CHK-1110); performance_lifecycle:blocked(CHK-1111); maintainability_integration:passed(CHK-1112) |
| CMP-134 Three-channel search results | DEF-020 / BP-020 | page | web/index.html: searchOut; implementation web/index.html: doSearch / doRoute / searchOut / routeOut; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013 | behavior:blocked(CHK-1113); states:blocked(CHK-1114); semantics_accessibility:blocked(CHK-1115); layout_content:blocked(CHK-1116); data_effects:blocked(CHK-1117); security_privacy:blocked(CHK-1118); performance_lifecycle:blocked(CHK-1119); maintainability_integration:passed(CHK-1120) |
| CMP-135 Routing query input | DEF-020 / BP-020 | page | web/index.html: routeQ; implementation web/index.html: doSearch / doRoute / searchOut / routeOut; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013 | behavior:blocked(CHK-1121); states:blocked(CHK-1122); semantics_accessibility:blocked(CHK-1123); layout_content:blocked(CHK-1124); data_effects:blocked(CHK-1125); security_privacy:blocked(CHK-1126); performance_lifecycle:blocked(CHK-1127); maintainability_integration:passed(CHK-1128) |
| CMP-136 Routing action/result | DEF-020 / BP-020 | page | web/index.html: routeBtn / routeOut; implementation web/index.html: doSearch / doRoute / searchOut / routeOut; variants: route /dashboard#search; conditional and repeated data templates listed in label/locator | investigate / TASK-013 | behavior:blocked(CHK-1129); states:blocked(CHK-1130); semantics_accessibility:blocked(CHK-1131); layout_content:blocked(CHK-1132); data_effects:blocked(CHK-1133); security_privacy:blocked(CHK-1134); performance_lifecycle:blocked(CHK-1135); maintainability_integration:passed(CHK-1136) |
| CMP-173 Capability frontier experiment launcher/dialog — Retrieval/routing laboratory | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#search #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1569); states:blocked(CHK-1570); semantics_accessibility:blocked(CHK-1571); layout_content:blocked(CHK-1572); data_effects:blocked(CHK-1573); security_privacy:blocked(CHK-1574); performance_lifecycle:blocked(CHK-1575); maintainability_integration:blocked(CHK-1576); maintainability_integration:passed(CHK-1577) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-013 Retrieval/routing laboratory browser journey and recovery | blocked | CMP-130, CMP-131, CMP-132, CMP-133, CMP-134, CMP-135, CMP-136; The user can complete Retrieval/routing laboratory without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-076 Final full frontier integration on /dashboard#search | blocked | CMP-173; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-130 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#search and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-131 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#search and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-132 Query/task/top-K inputs

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Query/task/top-K inputs is missing.

**Instance changes:** Keep route /dashboard#search and locator searchQ / searchTask / searchK behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Query/task/top-K inputs remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-133 Search action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Search action is missing.

**Instance changes:** Keep route /dashboard#search and locator searchBtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Search action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-134 Three-channel search results

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Three-channel search results is missing.

**Instance changes:** Keep route /dashboard#search and locator searchOut behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Three-channel search results remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-135 Routing query input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Routing query input is missing.

**Instance changes:** Keep route /dashboard#search and locator routeQ behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Routing query input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-136 Routing action/result

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Routing action/result is missing.

**Instance changes:** Keep route /dashboard#search and locator routeBtn / routeOut behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Routing action/result remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-013

### CMP-173 Capability frontier experiment launcher/dialog — Retrieval/routing laboratory

**Rationale:** Shared logic/source inspected; /dashboard#search has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#search task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#search preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-076
