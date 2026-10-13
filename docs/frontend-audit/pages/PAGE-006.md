# PAGE-006 Evaluation reports

Route `/runs#eval`; source `web/app.html`; entry evidence EV-004, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-068 Page shell/navigation/status | DEF-009 / BP-009 | page | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#eval; conditional and repeated data templates listed in label/locator | investigate / TASK-006 | behavior:blocked(CHK-0557); states:blocked(CHK-0558); semantics_accessibility:blocked(CHK-0559); layout_content:blocked(CHK-0560); data_effects:blocked(CHK-0561); security_privacy:blocked(CHK-0562); performance_lifecycle:blocked(CHK-0563); maintainability_integration:passed(CHK-0564) |
| CMP-069 Connection settings and toast | DEF-001 / BP-001 | page | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /runs#eval; conditional and repeated data templates listed in label/locator | investigate / TASK-006, TASK-017 | behavior:blocked(CHK-0565); states:blocked(CHK-0566); semantics_accessibility:blocked(CHK-0567); layout_content:blocked(CHK-0568); data_effects:blocked(CHK-0569); security_privacy:blocked(CHK-0570); performance_lifecycle:blocked(CHK-0571); maintainability_integration:passed(CHK-0572); security_privacy:passed(CHK-1286) |
| CMP-070 Actual experiment/empty/error template | DEF-012 / BP-012 | page | web/app.html: eval-body / loadEval; implementation web/app.html: loadEval / v-eval; variants: route /runs#eval; conditional and repeated data templates listed in label/locator | investigate / TASK-006, TASK-024 | behavior:blocked(CHK-0573); states:blocked(CHK-0574); semantics_accessibility:blocked(CHK-0575); layout_content:blocked(CHK-0576); data_effects:blocked(CHK-0577); security_privacy:blocked(CHK-0578); performance_lifecycle:blocked(CHK-0579); maintainability_integration:passed(CHK-0580); data_effects:passed(CHK-1307) |
| CMP-166 Capability frontier experiment launcher/dialog — Evaluation reports | DEF-032 / BP-032 | page | web/app.html: frontier.js/frontier.css includes; /runs#eval #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1506); states:blocked(CHK-1507); semantics_accessibility:blocked(CHK-1508); layout_content:blocked(CHK-1509); data_effects:blocked(CHK-1510); security_privacy:blocked(CHK-1511); performance_lifecycle:blocked(CHK-1512); maintainability_integration:blocked(CHK-1513); maintainability_integration:passed(CHK-1514) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-006 Evaluation reports browser journey and recovery | blocked | CMP-068, CMP-069, CMP-070; The user can complete Evaluation reports without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-024 Late mission/evaluation/system/health responses overwrite newer state — bounded Node regression | passed | CMP-051, CMP-070, CMP-073; Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result., All assertions in tools/frontend_resilience_check.js: centreRequestOwnership pass. | EV-019, FND-008 | [] |
| SCN-069 Final full frontier integration on /runs#eval | blocked | CMP-166; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-068 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /runs#eval and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-006

### CMP-069 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /runs#eval and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-006

### CMP-070 Actual experiment/empty/error template

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Actual experiment/empty/error template is missing.

**Instance changes:** Keep route /runs#eval and locator eval-body / loadEval behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Actual experiment/empty/error template remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-006

### CMP-166 Capability frontier experiment launcher/dialog — Evaluation reports

**Rationale:** Shared logic/source inspected; /runs#eval has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /runs#eval task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /runs#eval preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-069
