# PAGE-016 S1/export laboratory

Route `/dashboard#adapters`; source `web/index.html`; entry evidence EV-007, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-147 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#adapters; conditional and repeated data templates listed in label/locator | investigate / TASK-016 | behavior:blocked(CHK-1229); states:blocked(CHK-1230); semantics_accessibility:blocked(CHK-1231); layout_content:blocked(CHK-1232); data_effects:blocked(CHK-1233); security_privacy:blocked(CHK-1234); performance_lifecycle:blocked(CHK-1235); maintainability_integration:passed(CHK-1236) |
| CMP-148 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#adapters; conditional and repeated data templates listed in label/locator | investigate / TASK-016, TASK-017 | behavior:blocked(CHK-1237); states:blocked(CHK-1238); semantics_accessibility:blocked(CHK-1239); layout_content:blocked(CHK-1240); data_effects:blocked(CHK-1241); security_privacy:blocked(CHK-1242); performance_lifecycle:blocked(CHK-1243); maintainability_integration:passed(CHK-1244); security_privacy:passed(CHK-1296) |
| CMP-149 S1 service contract | DEF-023 / BP-023 | page | web/index.html: s1-contract; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live; variants: route /dashboard#adapters; conditional and repeated data templates listed in label/locator | investigate / TASK-016, TASK-030 | behavior:blocked(CHK-1245); states:blocked(CHK-1246); semantics_accessibility:blocked(CHK-1247); layout_content:blocked(CHK-1248); data_effects:blocked(CHK-1249); security_privacy:blocked(CHK-1250); performance_lifecycle:blocked(CHK-1251); maintainability_integration:passed(CHK-1252) |
| CMP-150 Export action | DEF-023 / BP-023 | page | web/index.html: adapterBtn; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live; variants: route /dashboard#adapters; conditional and repeated data templates listed in label/locator | investigate / TASK-016 | behavior:blocked(CHK-1253); states:blocked(CHK-1254); semantics_accessibility:blocked(CHK-1255); layout_content:blocked(CHK-1256); data_effects:blocked(CHK-1257); security_privacy:blocked(CHK-1258); performance_lifecycle:blocked(CHK-1259); maintainability_integration:passed(CHK-1260) |
| CMP-151 Export result/error template | DEF-023 / BP-023 | page | web/index.html: adapterOut; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live; variants: route /dashboard#adapters; conditional and repeated data templates listed in label/locator | investigate / TASK-016 | behavior:blocked(CHK-1261); states:blocked(CHK-1262); semantics_accessibility:blocked(CHK-1263); layout_content:blocked(CHK-1264); data_effects:blocked(CHK-1265); security_privacy:blocked(CHK-1266); performance_lifecycle:blocked(CHK-1267); maintainability_integration:passed(CHK-1268) |
| CMP-152 Live laboratory status | DEF-023 / BP-023 | page | web/index.html: lab-status / laboratory-live; implementation web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live; variants: route /dashboard#adapters; conditional and repeated data templates listed in label/locator | investigate / TASK-016 | behavior:blocked(CHK-1269); states:blocked(CHK-1270); semantics_accessibility:blocked(CHK-1271); layout_content:blocked(CHK-1272); data_effects:blocked(CHK-1273); security_privacy:blocked(CHK-1274); performance_lifecycle:blocked(CHK-1275); maintainability_integration:passed(CHK-1276) |
| CMP-176 Capability frontier experiment launcher/dialog — S1/export laboratory | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#adapters #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1596); states:blocked(CHK-1597); semantics_accessibility:blocked(CHK-1598); layout_content:blocked(CHK-1599); data_effects:blocked(CHK-1600); security_privacy:blocked(CHK-1601); performance_lifecycle:blocked(CHK-1602); maintainability_integration:blocked(CHK-1603); maintainability_integration:passed(CHK-1604) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-016 S1/export laboratory browser journey and recovery | blocked | CMP-147, CMP-148, CMP-149, CMP-150, CMP-151, CMP-152; The user can complete S1/export laboratory without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | FND-014 | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-079 Final full frontier integration on /dashboard#adapters | blocked | CMP-176; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-147 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#adapters and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-016

### CMP-148 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#adapters and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-016

### CMP-149 S1 service contract

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for S1 service contract is missing.

**Instance changes:** Keep route /dashboard#adapters and locator s1-contract behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** S1 service contract remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-016

### CMP-150 Export action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Export action is missing.

**Instance changes:** Keep route /dashboard#adapters and locator adapterBtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Export action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-016

### CMP-151 Export result/error template

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Export result/error template is missing.

**Instance changes:** Keep route /dashboard#adapters and locator adapterOut behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Export result/error template remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-016

### CMP-152 Live laboratory status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Live laboratory status is missing.

**Instance changes:** Keep route /dashboard#adapters and locator lab-status / laboratory-live behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Live laboratory status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-016

### CMP-176 Capability frontier experiment launcher/dialog — S1/export laboratory

**Rationale:** Shared logic/source inspected; /dashboard#adapters has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#adapters task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#adapters preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-079
