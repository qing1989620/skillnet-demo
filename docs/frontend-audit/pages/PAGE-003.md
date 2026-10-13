# PAGE-003 Mission centre

Route `/runs#mission`; source `web/app.html`; entry evidence EV-004, EV-025, EV-031, EV-050, EV-055.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-047 Page shell/navigation/status | DEF-009 / BP-009 | page | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#mission; conditional and repeated data templates listed in label/locator | investigate / TASK-003 | behavior:blocked(CHK-0377); states:blocked(CHK-0378); semantics_accessibility:blocked(CHK-0379); layout_content:blocked(CHK-0380); data_effects:blocked(CHK-0381); security_privacy:blocked(CHK-0382); performance_lifecycle:blocked(CHK-0383); maintainability_integration:passed(CHK-0384) |
| CMP-048 Connection settings and toast | DEF-001 / BP-001 | page | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /runs#mission; conditional and repeated data templates listed in label/locator | investigate / TASK-003, TASK-017 | behavior:blocked(CHK-0385); states:blocked(CHK-0386); semantics_accessibility:blocked(CHK-0387); layout_content:blocked(CHK-0388); data_effects:blocked(CHK-0389); security_privacy:blocked(CHK-0390); performance_lifecycle:blocked(CHK-0391); maintainability_integration:passed(CHK-0392); security_privacy:passed(CHK-1283) |
| CMP-049 Centre KPI figures | DEF-009 / BP-009 | page | web/app.html: center-kpis; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#mission; conditional and repeated data templates listed in label/locator | investigate / TASK-003 | behavior:blocked(CHK-0393); states:blocked(CHK-0394); semantics_accessibility:blocked(CHK-0395); layout_content:blocked(CHK-0396); data_effects:blocked(CHK-0397); security_privacy:blocked(CHK-0398); performance_lifecycle:blocked(CHK-0399); maintainability_integration:passed(CHK-0400) |
| CMP-050 Latest run header/navigation | DEF-009 / BP-009 | page | web/app.html: latest-title / latest-meta; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#mission; conditional and repeated data templates listed in label/locator | investigate / TASK-003 | behavior:blocked(CHK-0401); states:blocked(CHK-0402); semantics_accessibility:blocked(CHK-0403); layout_content:blocked(CHK-0404); data_effects:blocked(CHK-0405); security_privacy:blocked(CHK-0406); performance_lifecycle:blocked(CHK-0407); maintainability_integration:passed(CHK-0408) |
| CMP-051 Latest result and evidence | DEF-002 / BP-002 | page | web/app.html: latest-body; implementation web/assets/product.js: Product.evidenceHTML / dagHTML / preview / delegated inspectors; variants: route /runs#mission; conditional and repeated data templates listed in label/locator | investigate / TASK-003, TASK-024 | behavior:blocked(CHK-0409); states:blocked(CHK-0410); semantics_accessibility:blocked(CHK-0411); layout_content:blocked(CHK-0412); data_effects:blocked(CHK-0413); security_privacy:blocked(CHK-0414); performance_lifecycle:blocked(CHK-0415); maintainability_integration:passed(CHK-0416); data_effects:passed(CHK-1306) |
| CMP-052 Start-run form/dialog | DEF-009 / BP-009 | page | web/app.html: startRun / task / run; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#mission; conditional and repeated data templates listed in label/locator | investigate / TASK-003, TASK-019 | behavior:blocked(CHK-0417); states:blocked(CHK-0418); semantics_accessibility:blocked(CHK-0419); layout_content:blocked(CHK-0420); data_effects:blocked(CHK-0421); security_privacy:blocked(CHK-0422); performance_lifecycle:blocked(CHK-0423); maintainability_integration:passed(CHK-0424); behavior:passed(CHK-1298) |
| CMP-163 Capability frontier experiment launcher/dialog — Mission centre | DEF-032 / BP-032 | page | web/app.html: frontier.js/frontier.css includes; /runs#mission #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1479); states:blocked(CHK-1480); semantics_accessibility:blocked(CHK-1481); layout_content:blocked(CHK-1482); data_effects:blocked(CHK-1483); security_privacy:blocked(CHK-1484); performance_lifecycle:blocked(CHK-1485); maintainability_integration:blocked(CHK-1486); maintainability_integration:passed(CHK-1487) |
| CMP-212 Progressive skill selection to execution evidence | DEF-002 / BP-002 | CMP-051 | web/assets/product.js: selectionHTML/skillTraceHTML; #latest-body / Product.evidenceHTML .route-evidence > summary; variants: native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1924); states:blocked(CHK-1925); semantics_accessibility:blocked(CHK-1926); layout_content:blocked(CHK-1927); data_effects:blocked(CHK-1928); security_privacy:blocked(CHK-1929); performance_lifecycle:blocked(CHK-1930); maintainability_integration:passed(CHK-1931) |
| CMP-213 Associated-step execution and review action | DEF-030 / BP-030 | CMP-212 | web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent #latest-body / Product.evidenceHTML; variants: one original idx per actual matched skill step; no fabricated button for recommended-only skill | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1932); states:blocked(CHK-1933); semantics_accessibility:blocked(CHK-1934); layout_content:blocked(CHK-1935); data_effects:blocked(CHK-1936); security_privacy:blocked(CHK-1937); performance_lifecycle:blocked(CHK-1938); maintainability_integration:passed(CHK-1939) |
| CMP-214 Run-associated current skill passport | DEF-029 / BP-029 | CMP-212 | web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent #latest-body / Product.evidenceHTML; variants: parallel current/history read; partial failures, wrong run id and closed/stale responses | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1940); states:blocked(CHK-1941); semantics_accessibility:blocked(CHK-1942); layout_content:blocked(CHK-1943); data_effects:blocked(CHK-1944); security_privacy:blocked(CHK-1945); performance_lifecycle:blocked(CHK-1946); maintainability_integration:passed(CHK-1947) |
| CMP-215 Run/skill/step sphere location link | DEF-002 / BP-002 | CMP-212 | web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent #latest-body / Product.evidenceHTML; variants: safe encoded local path; preserved noncontiguous idx; no implicit last_run | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1948); states:blocked(CHK-1949); semantics_accessibility:blocked(CHK-1950); layout_content:blocked(CHK-1951); data_effects:blocked(CHK-1952); security_privacy:blocked(CHK-1953); performance_lifecycle:blocked(CHK-1954); maintainability_integration:passed(CHK-1955) |
| CMP-216 Explicit file/transition recheck action | DEF-028 / BP-028 | CMP-212 | web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent #latest-body / Product.evidenceHTML; variants: explicit read-only evidence rehash; no reward/write; stale dialog isolation | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1956); states:blocked(CHK-1957); semantics_accessibility:blocked(CHK-1958); layout_content:blocked(CHK-1959); data_effects:blocked(CHK-1960); security_privacy:blocked(CHK-1961); performance_lifecycle:blocked(CHK-1962); maintainability_integration:passed(CHK-1963) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-003 Mission centre browser journey and recovery | blocked | CMP-047, CMP-048, CMP-049, CMP-050, CMP-051, CMP-052, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216; The user can complete Mission centre without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-019 Confirmed run creation misreported when storage is disabled — bounded Node regression | passed | CMP-052; Persistence failure cannot change confirmed run identity; redirect using returned ID., All assertions in tools/frontend_resilience_check.js: blockedStorage pass. | EV-019, FND-003 | [] |
| SCN-024 Late mission/evaluation/system/health responses overwrite newer state — bounded Node regression | passed | CMP-051, CMP-070, CMP-073; Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result., All assertions in tools/frontend_resilience_check.js: centreRequestOwnership pass. | EV-019, FND-008 | [] |
| SCN-039 IAB initial viewport runs 1440×900 | passed | CMP-047; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-025 | [] |
| SCN-045 IAB initial viewport runs 390×844 | passed | CMP-047; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-031 | [] |
| SCN-066 Final full frontier integration on /runs#mission | blocked | CMP-163; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |
| SCN-086 Shared progressive skill trace and paired passport native integration (bounded) | blocked | CMP-202, CMP-203, CMP-204, CMP-205, CMP-206, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221, CMP-158, CMP-159; Actual matched steps and recorded artifacts/checks appear; unexecuted recommendations create no execution facts., Current declaration cannot replace historical SHA; partial failure is explicit and retains readable evidence; same idx in another run cannot focus the wrong current inspector., Parent route and selected skill/original idx survive navigation; no network/reward writes are implied. |  | [] |

## Instance plans

### CMP-047 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /runs#mission and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-003

### CMP-048 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /runs#mission and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-003

### CMP-049 Centre KPI figures

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Centre KPI figures is missing.

**Instance changes:** Keep route /runs#mission and locator center-kpis behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Centre KPI figures remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-003

### CMP-050 Latest run header/navigation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Latest run header/navigation is missing.

**Instance changes:** Keep route /runs#mission and locator latest-title / latest-meta behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Latest run header/navigation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-003

### CMP-051 Latest result and evidence

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Latest result and evidence is missing.

**Instance changes:** Keep route /runs#mission and locator latest-body behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Latest result and evidence remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-003

### CMP-052 Start-run form/dialog

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Start-run form/dialog is missing.

**Instance changes:** Keep route /runs#mission and locator startRun / task / run behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Start-run form/dialog remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-003

### CMP-163 Capability frontier experiment launcher/dialog — Mission centre

**Rationale:** Shared logic/source inspected; /runs#mission has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /runs#mission task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /runs#mission preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-066

### CMP-212 Progressive skill selection to execution evidence

**Rationale:** Actual source and shared logic were reviewed; native Progressive skill selection to execution evidence acceptance in PAGE-003 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML/skillTraceHTML; #latest-body / Product.evidenceHTML .route-evidence > summary with variants native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Progressive skill selection to execution evidence is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-003

### CMP-213 Associated-step execution and review action

**Rationale:** Actual source and shared logic were reviewed; native Associated-step execution and review action acceptance in PAGE-003 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent #latest-body / Product.evidenceHTML with variants one original idx per actual matched skill step; no fabricated button for recommended-only skill., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Associated-step execution and review action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-003

### CMP-214 Run-associated current skill passport

**Rationale:** Actual source and shared logic were reviewed; native Run-associated current skill passport acceptance in PAGE-003 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent #latest-body / Product.evidenceHTML with variants parallel current/history read; partial failures, wrong run id and closed/stale responses., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run-associated current skill passport is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-003

### CMP-215 Run/skill/step sphere location link

**Rationale:** Actual source and shared logic were reviewed; native Run/skill/step sphere location link acceptance in PAGE-003 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent #latest-body / Product.evidenceHTML with variants safe encoded local path; preserved noncontiguous idx; no implicit last_run., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run/skill/step sphere location link is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-003

### CMP-216 Explicit file/transition recheck action

**Rationale:** Actual source and shared logic were reviewed; native Explicit file/transition recheck action acceptance in PAGE-003 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent #latest-body / Product.evidenceHTML with variants explicit read-only evidence rehash; no reward/write; stale dialog isolation., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Explicit file/transition recheck action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-003
