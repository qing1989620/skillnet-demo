# PAGE-015 Historical results

Route `/dashboard#results`; source `web/index.html`; entry evidence EV-007, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-144 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#results; conditional and repeated data templates listed in label/locator | investigate / TASK-015 | behavior:blocked(CHK-1201); states:blocked(CHK-1202); semantics_accessibility:blocked(CHK-1203); layout_content:blocked(CHK-1204); data_effects:blocked(CHK-1205); security_privacy:blocked(CHK-1206); performance_lifecycle:blocked(CHK-1207); maintainability_integration:passed(CHK-1208) |
| CMP-145 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#results; conditional and repeated data templates listed in label/locator | investigate / TASK-015, TASK-017 | behavior:blocked(CHK-1209); states:blocked(CHK-1210); semantics_accessibility:blocked(CHK-1211); layout_content:blocked(CHK-1212); data_effects:blocked(CHK-1213); security_privacy:blocked(CHK-1214); performance_lifecycle:blocked(CHK-1215); maintainability_integration:passed(CHK-1216); security_privacy:passed(CHK-1295) |
| CMP-146 Actual result/empty/error template | DEF-022 / BP-022 | page | web/index.html: resultsOut; implementation web/index.html: resultsOut / renderResults; variants: route /dashboard#results; conditional and repeated data templates listed in label/locator | investigate / TASK-015 | behavior:blocked(CHK-1217); states:blocked(CHK-1218); semantics_accessibility:blocked(CHK-1219); layout_content:blocked(CHK-1220); data_effects:blocked(CHK-1221); security_privacy:blocked(CHK-1222); performance_lifecycle:blocked(CHK-1223); maintainability_integration:passed(CHK-1224) |
| CMP-175 Capability frontier experiment launcher/dialog — Historical results | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#results #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1587); states:blocked(CHK-1588); semantics_accessibility:blocked(CHK-1589); layout_content:blocked(CHK-1590); data_effects:blocked(CHK-1591); security_privacy:blocked(CHK-1592); performance_lifecycle:blocked(CHK-1593); maintainability_integration:blocked(CHK-1594); maintainability_integration:passed(CHK-1595) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-015 Historical results browser journey and recovery | blocked | CMP-144, CMP-145, CMP-146; The user can complete Historical results without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-078 Final full frontier integration on /dashboard#results | blocked | CMP-175; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-144 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#results and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-015

### CMP-145 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#results and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-015

### CMP-146 Actual result/empty/error template

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Actual result/empty/error template is missing.

**Instance changes:** Keep route /dashboard#results and locator resultsOut behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Actual result/empty/error template remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-015

### CMP-175 Capability frontier experiment launcher/dialog — Historical results

**Rationale:** Shared logic/source inspected; /dashboard#results has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#results task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#results preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-078
