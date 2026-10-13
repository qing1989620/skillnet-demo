# PAGE-007 Deployment information

Route `/runs#system`; source `web/app.html`; entry evidence EV-004, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-071 Page shell/navigation/status | DEF-009 / BP-009 | page | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#system; conditional and repeated data templates listed in label/locator | investigate / TASK-007 | behavior:blocked(CHK-0585); states:blocked(CHK-0586); semantics_accessibility:blocked(CHK-0587); layout_content:blocked(CHK-0588); data_effects:blocked(CHK-0589); security_privacy:blocked(CHK-0590); performance_lifecycle:blocked(CHK-0591); maintainability_integration:passed(CHK-0592) |
| CMP-072 Connection settings and toast | DEF-001 / BP-001 | page | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /runs#system; conditional and repeated data templates listed in label/locator | investigate / TASK-007, TASK-017 | behavior:blocked(CHK-0593); states:blocked(CHK-0594); semantics_accessibility:blocked(CHK-0595); layout_content:blocked(CHK-0596); data_effects:blocked(CHK-0597); security_privacy:blocked(CHK-0598); performance_lifecycle:blocked(CHK-0599); maintainability_integration:passed(CHK-0600); security_privacy:passed(CHK-1287) |
| CMP-073 Current runtime/API/worker details | DEF-013 / BP-013 | page | web/app.html: sys-meta / sys-body / loadSystem; implementation web/app.html: loadSystem / v-system; variants: route /runs#system; conditional and repeated data templates listed in label/locator | investigate / TASK-007, TASK-024 | behavior:blocked(CHK-0601); states:blocked(CHK-0602); semantics_accessibility:blocked(CHK-0603); layout_content:blocked(CHK-0604); data_effects:blocked(CHK-0605); security_privacy:blocked(CHK-0606); performance_lifecycle:blocked(CHK-0607); maintainability_integration:passed(CHK-0608); data_effects:passed(CHK-1308) |
| CMP-074 S1 implementation/production boundary | DEF-013 / BP-013 | page | web/app.html: v-system; implementation web/app.html: loadSystem / v-system; variants: route /runs#system; conditional and repeated data templates listed in label/locator | investigate / TASK-007, TASK-030 | behavior:blocked(CHK-0609); states:blocked(CHK-0610); semantics_accessibility:blocked(CHK-0611); layout_content:blocked(CHK-0612); data_effects:blocked(CHK-0613); security_privacy:blocked(CHK-0614); performance_lifecycle:blocked(CHK-0615); maintainability_integration:passed(CHK-0616) |
| CMP-167 Capability frontier experiment launcher/dialog — Deployment information | DEF-032 / BP-032 | page | web/app.html: frontier.js/frontier.css includes; /runs#system #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1515); states:blocked(CHK-1516); semantics_accessibility:blocked(CHK-1517); layout_content:blocked(CHK-1518); data_effects:blocked(CHK-1519); security_privacy:blocked(CHK-1520); performance_lifecycle:blocked(CHK-1521); maintainability_integration:blocked(CHK-1522); maintainability_integration:passed(CHK-1523) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-007 Deployment information browser journey and recovery | blocked | CMP-071, CMP-072, CMP-073, CMP-074; The user can complete Deployment information without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | FND-014 | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-024 Late mission/evaluation/system/health responses overwrite newer state — bounded Node regression | passed | CMP-051, CMP-070, CMP-073; Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result., All assertions in tools/frontend_resilience_check.js: centreRequestOwnership pass. | EV-019, FND-008 | [] |
| SCN-070 Final full frontier integration on /runs#system | blocked | CMP-167; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-071 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /runs#system and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-007

### CMP-072 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /runs#system and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-007

### CMP-073 Current runtime/API/worker details

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Current runtime/API/worker details is missing.

**Instance changes:** Keep route /runs#system and locator sys-meta / sys-body / loadSystem behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Current runtime/API/worker details remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-007

### CMP-074 S1 implementation/production boundary

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for S1 implementation/production boundary is missing.

**Instance changes:** Keep route /runs#system and locator v-system behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** S1 implementation/production boundary remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-007

### CMP-167 Capability frontier experiment launcher/dialog — Deployment information

**Rationale:** Shared logic/source inspected; /runs#system has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /runs#system task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /runs#system preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-070
