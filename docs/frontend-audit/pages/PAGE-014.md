# PAGE-014 Execution laboratory

Route `/dashboard#run`; source `web/index.html`; entry evidence EV-007, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-137 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014 | behavior:blocked(CHK-1141); states:blocked(CHK-1142); semantics_accessibility:blocked(CHK-1143); layout_content:blocked(CHK-1144); data_effects:blocked(CHK-1145); security_privacy:blocked(CHK-1146); performance_lifecycle:blocked(CHK-1147); maintainability_integration:passed(CHK-1148) |
| CMP-138 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014, TASK-017 | behavior:blocked(CHK-1149); states:blocked(CHK-1150); semantics_accessibility:blocked(CHK-1151); layout_content:blocked(CHK-1152); data_effects:blocked(CHK-1153); security_privacy:blocked(CHK-1154); performance_lifecycle:blocked(CHK-1155); maintainability_integration:passed(CHK-1156); security_privacy:passed(CHK-1294) |
| CMP-139 Task selector/input | DEF-021 / BP-021 | page | web/index.html: runTask / runTaskText; implementation web/index.html: doRun / runMode / realRunBtn / runOut; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014 | behavior:blocked(CHK-1157); states:blocked(CHK-1158); semantics_accessibility:blocked(CHK-1159); layout_content:blocked(CHK-1160); data_effects:blocked(CHK-1161); security_privacy:blocked(CHK-1162); performance_lifecycle:blocked(CHK-1163); maintainability_integration:passed(CHK-1164) |
| CMP-140 Execution mode selector | DEF-021 / BP-021 | page | web/index.html: runMode; implementation web/index.html: doRun / runMode / realRunBtn / runOut; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014 | behavior:blocked(CHK-1165); states:blocked(CHK-1166); semantics_accessibility:blocked(CHK-1167); layout_content:blocked(CHK-1168); data_effects:blocked(CHK-1169); security_privacy:blocked(CHK-1170); performance_lifecycle:blocked(CHK-1171); maintainability_integration:passed(CHK-1172) |
| CMP-141 Plan comparison action | DEF-021 / BP-021 | page | web/index.html: runBtn; implementation web/index.html: doRun / runMode / realRunBtn / runOut; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014 | behavior:blocked(CHK-1173); states:blocked(CHK-1174); semantics_accessibility:blocked(CHK-1175); layout_content:blocked(CHK-1176); data_effects:blocked(CHK-1177); security_privacy:blocked(CHK-1178); performance_lifecycle:blocked(CHK-1179); maintainability_integration:passed(CHK-1180) |
| CMP-142 Create real-run action | DEF-021 / BP-021 | page | web/index.html: realRunBtn; implementation web/index.html: doRun / runMode / realRunBtn / runOut; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014 | behavior:blocked(CHK-1181); states:blocked(CHK-1182); semantics_accessibility:blocked(CHK-1183); layout_content:blocked(CHK-1184); data_effects:blocked(CHK-1185); security_privacy:blocked(CHK-1186); performance_lifecycle:blocked(CHK-1187); maintainability_integration:passed(CHK-1188) |
| CMP-143 Status/result/model-reference states | DEF-021 / BP-021 | page | web/index.html: runStatus / runOut; implementation web/index.html: doRun / runMode / realRunBtn / runOut; variants: route /dashboard#run; conditional and repeated data templates listed in label/locator | investigate / TASK-014, TASK-022 | behavior:blocked(CHK-1189); states:blocked(CHK-1190); semantics_accessibility:blocked(CHK-1191); layout_content:blocked(CHK-1192); data_effects:blocked(CHK-1193); security_privacy:blocked(CHK-1194); performance_lifecycle:blocked(CHK-1195); maintainability_integration:passed(CHK-1196); states:passed(CHK-1304) |
| CMP-174 Capability frontier experiment launcher/dialog — Execution laboratory | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#run #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1578); states:blocked(CHK-1579); semantics_accessibility:blocked(CHK-1580); layout_content:blocked(CHK-1581); data_effects:blocked(CHK-1582); security_privacy:blocked(CHK-1583); performance_lifecycle:blocked(CHK-1584); maintainability_integration:blocked(CHK-1585); maintainability_integration:passed(CHK-1586) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-014 Execution laboratory browser journey and recovery | blocked | CMP-137, CMP-138, CMP-139, CMP-140, CMP-141, CMP-142, CMP-143; The user can complete Execution laboratory without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-022 Invalid model score and zero-attempt presentation — bounded Node regression | passed | CMP-041, CMP-122, CMP-143; Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts., All assertions in tools/frontend_resilience_check.js: honestScoreAndAttempts pass. | EV-019, FND-006 | [] |
| SCN-077 Final full frontier integration on /dashboard#run | blocked | CMP-174; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-137 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#run and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-138 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#run and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-139 Task selector/input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Task selector/input is missing.

**Instance changes:** Keep route /dashboard#run and locator runTask / runTaskText behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Task selector/input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-140 Execution mode selector

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Execution mode selector is missing.

**Instance changes:** Keep route /dashboard#run and locator runMode behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Execution mode selector remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-141 Plan comparison action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Plan comparison action is missing.

**Instance changes:** Keep route /dashboard#run and locator runBtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Plan comparison action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-142 Create real-run action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Create real-run action is missing.

**Instance changes:** Keep route /dashboard#run and locator realRunBtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Create real-run action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-143 Status/result/model-reference states

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Status/result/model-reference states is missing.

**Instance changes:** Keep route /dashboard#run and locator runStatus / runOut behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Status/result/model-reference states remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-014

### CMP-174 Capability frontier experiment launcher/dialog — Execution laboratory

**Rationale:** Shared logic/source inspected; /dashboard#run has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#run task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#run preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-077
