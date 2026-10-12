# PAGE-004 Run catalogue

Route `/runs#runs`; source `web/app.html`; entry evidence EV-004, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-053 Page shell/navigation/status | DEF-009 / BP-009 | page | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0429); states:blocked(CHK-0430); semantics_accessibility:blocked(CHK-0431); layout_content:blocked(CHK-0432); data_effects:blocked(CHK-0433); security_privacy:blocked(CHK-0434); performance_lifecycle:blocked(CHK-0435); maintainability_integration:passed(CHK-0436) |
| CMP-054 Connection settings and toast | DEF-001 / BP-001 | page | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004, TASK-017 | behavior:blocked(CHK-0437); states:blocked(CHK-0438); semantics_accessibility:blocked(CHK-0439); layout_content:blocked(CHK-0440); data_effects:blocked(CHK-0441); security_privacy:blocked(CHK-0442); performance_lifecycle:blocked(CHK-0443); maintainability_integration:passed(CHK-0444); security_privacy:passed(CHK-1284) |
| CMP-055 Query input | DEF-010 / BP-010 | page | web/app.html: run-query; implementation web/app.html: loadRuns / run-query / run-status / run-prev / run-next; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0445); states:blocked(CHK-0446); semantics_accessibility:blocked(CHK-0447); layout_content:blocked(CHK-0448); data_effects:blocked(CHK-0449); security_privacy:blocked(CHK-0450); performance_lifecycle:blocked(CHK-0451); maintainability_integration:passed(CHK-0452) |
| CMP-056 Status filter | DEF-010 / BP-010 | page | web/app.html: run-status; implementation web/app.html: loadRuns / run-query / run-status / run-prev / run-next; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0453); states:blocked(CHK-0454); semantics_accessibility:blocked(CHK-0455); layout_content:blocked(CHK-0456); data_effects:blocked(CHK-0457); security_privacy:blocked(CHK-0458); performance_lifecycle:blocked(CHK-0459); maintainability_integration:passed(CHK-0460) |
| CMP-057 Refresh action | DEF-010 / BP-010 | page | web/app.html: run-refresh; implementation web/app.html: loadRuns / run-query / run-status / run-prev / run-next; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0461); states:blocked(CHK-0462); semantics_accessibility:blocked(CHK-0463); layout_content:blocked(CHK-0464); data_effects:blocked(CHK-0465); security_privacy:blocked(CHK-0466); performance_lifecycle:blocked(CHK-0467); maintainability_integration:passed(CHK-0468) |
| CMP-058 Loading/error/empty/list templates | DEF-010 / BP-010 | page | web/app.html: runs-body / loadRuns; implementation web/app.html: loadRuns / run-query / run-status / run-prev / run-next; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0469); states:blocked(CHK-0470); semantics_accessibility:blocked(CHK-0471); layout_content:blocked(CHK-0472); data_effects:blocked(CHK-0473); security_privacy:blocked(CHK-0474); performance_lifecycle:blocked(CHK-0475); maintainability_integration:passed(CHK-0476) |
| CMP-059 Previous/next-page actions | DEF-010 / BP-010 | page | web/app.html: run-prev / run-next; implementation web/app.html: loadRuns / run-query / run-status / run-prev / run-next; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0477); states:blocked(CHK-0478); semantics_accessibility:blocked(CHK-0479); layout_content:blocked(CHK-0480); data_effects:blocked(CHK-0481); security_privacy:blocked(CHK-0482); performance_lifecycle:blocked(CHK-0483); maintainability_integration:passed(CHK-0484) |
| CMP-060 Page/query counts | DEF-010 / BP-010 | page | web/app.html: run-page / runs-meta; implementation web/app.html: loadRuns / run-query / run-status / run-prev / run-next; variants: route /runs#runs; conditional and repeated data templates listed in label/locator | investigate / TASK-004 | behavior:blocked(CHK-0485); states:blocked(CHK-0486); semantics_accessibility:blocked(CHK-0487); layout_content:blocked(CHK-0488); data_effects:blocked(CHK-0489); security_privacy:blocked(CHK-0490); performance_lifecycle:blocked(CHK-0491); maintainability_integration:passed(CHK-0492) |
| CMP-164 Capability frontier experiment launcher/dialog — Run catalogue | DEF-032 / BP-032 | page | web/app.html: frontier.js/frontier.css includes; /runs#runs #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1488); states:blocked(CHK-1489); semantics_accessibility:blocked(CHK-1490); layout_content:blocked(CHK-1491); data_effects:blocked(CHK-1492); security_privacy:blocked(CHK-1493); performance_lifecycle:blocked(CHK-1494); maintainability_integration:blocked(CHK-1495); maintainability_integration:passed(CHK-1496) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-004 Run catalogue browser journey and recovery | blocked | CMP-053, CMP-054, CMP-055, CMP-056, CMP-057, CMP-058, CMP-059, CMP-060; The user can complete Run catalogue without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-067 Final full frontier integration on /runs#runs | blocked | CMP-164; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-053 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /runs#runs and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-054 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /runs#runs and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-055 Query input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Query input is missing.

**Instance changes:** Keep route /runs#runs and locator run-query behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Query input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-056 Status filter

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Status filter is missing.

**Instance changes:** Keep route /runs#runs and locator run-status behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Status filter remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-057 Refresh action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Refresh action is missing.

**Instance changes:** Keep route /runs#runs and locator run-refresh behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Refresh action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-058 Loading/error/empty/list templates

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Loading/error/empty/list templates is missing.

**Instance changes:** Keep route /runs#runs and locator runs-body / loadRuns behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Loading/error/empty/list templates remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-059 Previous/next-page actions

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Previous/next-page actions is missing.

**Instance changes:** Keep route /runs#runs and locator run-prev / run-next behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Previous/next-page actions remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-060 Page/query counts

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page/query counts is missing.

**Instance changes:** Keep route /runs#runs and locator run-page / runs-meta behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page/query counts remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-004

### CMP-164 Capability frontier experiment launcher/dialog — Run catalogue

**Rationale:** Shared logic/source inspected; /runs#runs has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /runs#runs task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /runs#runs preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-067
