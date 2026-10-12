# PAGE-010 Developer overview

Route `/dashboard#overview`; source `web/index.html`; entry evidence EV-007, EV-026, EV-032, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-111 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#overview; conditional and repeated data templates listed in label/locator | investigate / TASK-010 | behavior:blocked(CHK-0917); states:blocked(CHK-0918); semantics_accessibility:blocked(CHK-0919); layout_content:blocked(CHK-0920); data_effects:blocked(CHK-0921); security_privacy:blocked(CHK-0922); performance_lifecycle:blocked(CHK-0923); maintainability_integration:passed(CHK-0924) |
| CMP-112 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#overview; conditional and repeated data templates listed in label/locator | investigate / TASK-010, TASK-017 | behavior:blocked(CHK-0925); states:blocked(CHK-0926); semantics_accessibility:blocked(CHK-0927); layout_content:blocked(CHK-0928); data_effects:blocked(CHK-0929); security_privacy:blocked(CHK-0930); performance_lifecycle:blocked(CHK-0931); maintainability_integration:passed(CHK-0932); security_privacy:passed(CHK-1290) |
| CMP-113 Overview graph | DEF-017 / BP-017 | page | web/index.html: graph; implementation web/index.html: renderOverview / graph / domains / quality / pipeline / refs; variants: route /dashboard#overview; conditional and repeated data templates listed in label/locator | investigate / TASK-010 | behavior:blocked(CHK-0933); states:blocked(CHK-0934); semantics_accessibility:blocked(CHK-0935); layout_content:blocked(CHK-0936); data_effects:blocked(CHK-0937); security_privacy:blocked(CHK-0938); performance_lifecycle:blocked(CHK-0939); maintainability_integration:passed(CHK-0940) |
| CMP-114 Domain/quality summaries | DEF-017 / BP-017 | page | web/index.html: domains / quality; implementation web/index.html: renderOverview / graph / domains / quality / pipeline / refs; variants: route /dashboard#overview; conditional and repeated data templates listed in label/locator | investigate / TASK-010 | behavior:blocked(CHK-0941); states:blocked(CHK-0942); semantics_accessibility:blocked(CHK-0943); layout_content:blocked(CHK-0944); data_effects:blocked(CHK-0945); security_privacy:blocked(CHK-0946); performance_lifecycle:blocked(CHK-0947); maintainability_integration:passed(CHK-0948) |
| CMP-115 Pipeline/reference explanation | DEF-017 / BP-017 | page | web/index.html: pipeline / refs; implementation web/index.html: renderOverview / graph / domains / quality / pipeline / refs; variants: route /dashboard#overview; conditional and repeated data templates listed in label/locator | investigate / TASK-010 | behavior:blocked(CHK-0949); states:blocked(CHK-0950); semantics_accessibility:blocked(CHK-0951); layout_content:blocked(CHK-0952); data_effects:blocked(CHK-0953); security_privacy:blocked(CHK-0954); performance_lifecycle:blocked(CHK-0955); maintainability_integration:passed(CHK-0956) |
| CMP-170 Capability frontier experiment launcher/dialog — Developer overview | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#overview #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1542); states:blocked(CHK-1543); semantics_accessibility:blocked(CHK-1544); layout_content:blocked(CHK-1545); data_effects:blocked(CHK-1546); security_privacy:blocked(CHK-1547); performance_lifecycle:blocked(CHK-1548); maintainability_integration:blocked(CHK-1549); maintainability_integration:passed(CHK-1550) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-010 Developer overview browser journey and recovery | blocked | CMP-111, CMP-112, CMP-113, CMP-114, CMP-115; The user can complete Developer overview without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-040 IAB initial viewport dashboard 1440×900 | passed | CMP-111; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-026 | [] |
| SCN-046 IAB initial viewport dashboard 390×844 | passed | CMP-111; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-032 | [] |
| SCN-073 Final full frontier integration on /dashboard#overview | blocked | CMP-170; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-111 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#overview and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-010

### CMP-112 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#overview and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-010

### CMP-113 Overview graph

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Overview graph is missing.

**Instance changes:** Keep route /dashboard#overview and locator graph behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Overview graph remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-010

### CMP-114 Domain/quality summaries

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Domain/quality summaries is missing.

**Instance changes:** Keep route /dashboard#overview and locator domains / quality behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Domain/quality summaries remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-010

### CMP-115 Pipeline/reference explanation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Pipeline/reference explanation is missing.

**Instance changes:** Keep route /dashboard#overview and locator pipeline / refs behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Pipeline/reference explanation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-010

### CMP-170 Capability frontier experiment launcher/dialog — Developer overview

**Rationale:** Shared logic/source inspected; /dashboard#overview has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#overview task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#overview preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-073
