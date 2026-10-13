# PAGE-008 Run detail

Route `/run?id=<run-id>`; source `web/run.html`; entry evidence EV-005, EV-028, EV-034, EV-050, EV-055, EV-061.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-075 Page shell/navigation/status | DEF-014 / BP-014 | page | web/run.html: header / nav / main; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0621); states:blocked(CHK-0622); semantics_accessibility:blocked(CHK-0623); layout_content:blocked(CHK-0624); data_effects:blocked(CHK-0625); security_privacy:blocked(CHK-0626); performance_lifecycle:blocked(CHK-0627); maintainability_integration:passed(CHK-0628) |
| CMP-076 Connection settings and toast | DEF-001 / BP-001 | page | web/run.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008, TASK-017 | behavior:blocked(CHK-0629); states:blocked(CHK-0630); semantics_accessibility:blocked(CHK-0631); layout_content:blocked(CHK-0632); data_effects:blocked(CHK-0633); security_privacy:blocked(CHK-0634); performance_lifecycle:blocked(CHK-0635); maintainability_integration:passed(CHK-0636); security_privacy:passed(CHK-1288) |
| CMP-077 Run status/task/identity header | DEF-014 / BP-014 | page | web/run.html: status / task / rid; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0637); states:blocked(CHK-0638); semantics_accessibility:blocked(CHK-0639); layout_content:blocked(CHK-0640); data_effects:blocked(CHK-0641); security_privacy:blocked(CHK-0642); performance_lifecycle:blocked(CHK-0643); maintainability_integration:passed(CHK-0644) |
| CMP-078 Cost/duration/budget metrics | DEF-014 / BP-014 | page | web/run.html: elapsed / cost / budget / costbar / stepstat; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0645); states:blocked(CHK-0646); semantics_accessibility:blocked(CHK-0647); layout_content:blocked(CHK-0648); data_effects:blocked(CHK-0649); security_privacy:blocked(CHK-0650); performance_lifecycle:blocked(CHK-0651); maintainability_integration:passed(CHK-0652) |
| CMP-079 Stream/connection state | DEF-014 / BP-014 | page | web/run.html: stream-state; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0653); states:blocked(CHK-0654); semantics_accessibility:blocked(CHK-0655); layout_content:blocked(CHK-0656); data_effects:blocked(CHK-0657); security_privacy:blocked(CHK-0658); performance_lifecycle:blocked(CHK-0659); maintainability_integration:passed(CHK-0660) |
| CMP-080 Focus view control | DEF-014 / BP-014 | page | web/run.html: focus-view; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0661); states:blocked(CHK-0662); semantics_accessibility:blocked(CHK-0663); layout_content:blocked(CHK-0664); data_effects:blocked(CHK-0665); security_privacy:blocked(CHK-0666); performance_lifecycle:blocked(CHK-0667); maintainability_integration:passed(CHK-0668) |
| CMP-081 Cancel action | DEF-014 / BP-014 | page | web/run.html: cancel; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0669); states:blocked(CHK-0670); semantics_accessibility:blocked(CHK-0671); layout_content:blocked(CHK-0672); data_effects:blocked(CHK-0673); security_privacy:blocked(CHK-0674); performance_lifecycle:blocked(CHK-0675); maintainability_integration:passed(CHK-0676) |
| CMP-082 Mobile tab controls | DEF-014 / BP-014 | page | web/run.html: tabs; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0677); states:blocked(CHK-0678); semantics_accessibility:blocked(CHK-0679); layout_content:blocked(CHK-0680); data_effects:blocked(CHK-0681); security_privacy:blocked(CHK-0682); performance_lifecycle:blocked(CHK-0683); maintainability_integration:passed(CHK-0684) |
| CMP-083 Execution DAG node/edge templates | DEF-014 / BP-014 | page | web/run.html: graph / gcount; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0685); states:blocked(CHK-0686); semantics_accessibility:blocked(CHK-0687); layout_content:blocked(CHK-0688); data_effects:blocked(CHK-0689); security_privacy:blocked(CHK-0690); performance_lifecycle:blocked(CHK-0691); maintainability_integration:passed(CHK-0692) |
| CMP-084 Event type filter | DEF-014 / BP-014 | page | web/run.html: event-filter; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0693); states:blocked(CHK-0694); semantics_accessibility:blocked(CHK-0695); layout_content:blocked(CHK-0696); data_effects:blocked(CHK-0697); security_privacy:blocked(CHK-0698); performance_lifecycle:blocked(CHK-0699); maintainability_integration:passed(CHK-0700) |
| CMP-085 Follow events toggle | DEF-014 / BP-014 | page | web/run.html: event-follow; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0701); states:blocked(CHK-0702); semantics_accessibility:blocked(CHK-0703); layout_content:blocked(CHK-0704); data_effects:blocked(CHK-0705); security_privacy:blocked(CHK-0706); performance_lifecycle:blocked(CHK-0707); maintainability_integration:passed(CHK-0708) |
| CMP-086 Timeline event/check group templates | DEF-014 / BP-014 | page | web/run.html: timeline / evcount; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0709); states:blocked(CHK-0710); semantics_accessibility:blocked(CHK-0711); layout_content:blocked(CHK-0712); data_effects:blocked(CHK-0713); security_privacy:blocked(CHK-0714); performance_lifecycle:blocked(CHK-0715); maintainability_integration:passed(CHK-0716) |
| CMP-087 Step/event/attempt inspector | DEF-014 / BP-014 | page | web/run.html: inspector / inswhat; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator; first-load step deep-link by original idx; invalid/missing falls back explicitly; later refresh preserves user selection | investigate / TASK-008, TASK-040 | behavior:blocked(CHK-0717); states:blocked(CHK-0718); semantics_accessibility:blocked(CHK-0719); layout_content:blocked(CHK-0720); data_effects:blocked(CHK-0721); security_privacy:blocked(CHK-0722); performance_lifecycle:blocked(CHK-0723); maintainability_integration:passed(CHK-0724); behavior:passed(CHK-2025) |
| CMP-088 Proof and final result | DEF-014 / BP-014 | page | web/run.html: run-proof; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008 | behavior:blocked(CHK-0725); states:blocked(CHK-0726); semantics_accessibility:blocked(CHK-0727); layout_content:blocked(CHK-0728); data_effects:blocked(CHK-0729); security_privacy:blocked(CHK-0730); performance_lifecycle:blocked(CHK-0731); maintainability_integration:passed(CHK-0732) |
| CMP-089 Missing-ID/error/static variant | DEF-014 / BP-014 | page | web/run.html: RUN_ID / QS / render; implementation web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof; variants: route /run?id=<run-id>; conditional and repeated data templates listed in label/locator | investigate / TASK-008, TASK-020 | behavior:blocked(CHK-0733); states:blocked(CHK-0734); semantics_accessibility:blocked(CHK-0735); layout_content:blocked(CHK-0736); data_effects:blocked(CHK-0737); security_privacy:blocked(CHK-0738); performance_lifecycle:blocked(CHK-0739); maintainability_integration:passed(CHK-0740); states:passed(CHK-1299) |
| CMP-168 Capability frontier experiment launcher/dialog — Run detail | DEF-032 / BP-032 | page | web/run.html: frontier.js/frontier.css includes; /run?id=<run-id> #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1524); states:blocked(CHK-1525); semantics_accessibility:blocked(CHK-1526); layout_content:blocked(CHK-1527); data_effects:blocked(CHK-1528); security_privacy:blocked(CHK-1529); performance_lifecycle:blocked(CHK-1530); maintainability_integration:blocked(CHK-1531); maintainability_integration:passed(CHK-1532) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-008 Run detail browser journey and recovery | blocked | CMP-075, CMP-076, CMP-077, CMP-078, CMP-079, CMP-080, CMP-081, CMP-082, CMP-083, CMP-084, CMP-085, CMP-086, CMP-087, CMP-088, CMP-089; The user can complete Run detail without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-020 Run detail crashes before empty-state rendering with storage disabled — bounded Node regression | passed | CMP-089; Guard fallback storage and render the missing-run state normally., All assertions in tools/frontend_resilience_check.js: blockedStorage pass. | EV-019, FND-004 | [] |
| SCN-042 IAB initial viewport run 1440×900 | passed | CMP-075; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-028 | [] |
| SCN-048 IAB initial viewport run 390×844 | passed | CMP-075; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-034 | [] |
| SCN-071 Final full frontier integration on /run?id=<run-id> | blocked | CMP-168; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |
| SCN-087 Run initial-step deep-link and later-selection ownership native check (bounded) | blocked | CMP-087; Only recorded original idx can be selected; invalid/missing request is reported instead of selecting unrelated row/last run., Initial query selection applies once; later refresh preserves user-owned inspector selection. |  | [] |
| SCN-100 Actual run valid-step navigation and invalid999 fallback subset | passed | CMP-087; Valid original idx2 and missing idx999 choose only actual steps of that explicit run., Later-refresh user selection ownership, other invalid formats and all responsive inspector states remain unverified by this subset. | EV-061 | [] |

## Instance plans

### CMP-075 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-076 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-077 Run status/task/identity header

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Run status/task/identity header is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator status / task / rid behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Run status/task/identity header remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-078 Cost/duration/budget metrics

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Cost/duration/budget metrics is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator elapsed / cost / budget / costbar / stepstat behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Cost/duration/budget metrics remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-079 Stream/connection state

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Stream/connection state is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator stream-state behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Stream/connection state remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-080 Focus view control

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Focus view control is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator focus-view behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Focus view control remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-081 Cancel action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Cancel action is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator cancel behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Cancel action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-082 Mobile tab controls

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Mobile tab controls is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator tabs behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Mobile tab controls remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-083 Execution DAG node/edge templates

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Execution DAG node/edge templates is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator graph / gcount behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Execution DAG node/edge templates remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-084 Event type filter

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Event type filter is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator event-filter behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Event type filter remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-085 Follow events toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Follow events toggle is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator event-follow behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Follow events toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-086 Timeline event/check group templates

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Timeline event/check group templates is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator timeline / evcount behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Timeline event/check group templates remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-087 Step/event/attempt inspector

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Step/event/attempt inspector is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator inspector / inswhat behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Step/event/attempt inspector remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008, SCN-087, SCN-100

### CMP-088 Proof and final result

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Proof and final result is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator run-proof behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Proof and final result remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-089 Missing-ID/error/static variant

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Missing-ID/error/static variant is missing.

**Instance changes:** Keep route /run?id=<run-id> and locator RUN_ID / QS / render behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Missing-ID/error/static variant remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-008

### CMP-168 Capability frontier experiment launcher/dialog — Run detail

**Rationale:** Shared logic/source inspected; /run?id=<run-id> has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /run?id=<run-id> task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /run?id=<run-id> preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-071
