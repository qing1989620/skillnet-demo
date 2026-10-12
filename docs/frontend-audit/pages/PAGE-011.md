# PAGE-011 Plan contrast

Route `/dashboard#demo`; source `web/index.html`; entry evidence EV-007, EV-050, EV-055.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-116 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011 | behavior:blocked(CHK-0961); states:blocked(CHK-0962); semantics_accessibility:blocked(CHK-0963); layout_content:blocked(CHK-0964); data_effects:blocked(CHK-0965); security_privacy:blocked(CHK-0966); performance_lifecycle:blocked(CHK-0967); maintainability_integration:passed(CHK-0968) |
| CMP-117 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011, TASK-017 | behavior:blocked(CHK-0969); states:blocked(CHK-0970); semantics_accessibility:blocked(CHK-0971); layout_content:blocked(CHK-0972); data_effects:blocked(CHK-0973); security_privacy:blocked(CHK-0974); performance_lifecycle:blocked(CHK-0975); maintainability_integration:passed(CHK-0976); security_privacy:passed(CHK-1291) |
| CMP-118 Scenario selector | DEF-018 / BP-018 | page | web/index.html: demoTask; implementation web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011 | behavior:blocked(CHK-0977); states:blocked(CHK-0978); semantics_accessibility:blocked(CHK-0979); layout_content:blocked(CHK-0980); data_effects:blocked(CHK-0981); security_privacy:blocked(CHK-0982); performance_lifecycle:blocked(CHK-0983); maintainability_integration:passed(CHK-0984) |
| CMP-119 Custom task input | DEF-018 / BP-018 | page | web/index.html: demoTaskText; implementation web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011 | behavior:blocked(CHK-0985); states:blocked(CHK-0986); semantics_accessibility:blocked(CHK-0987); layout_content:blocked(CHK-0988); data_effects:blocked(CHK-0989); security_privacy:blocked(CHK-0990); performance_lifecycle:blocked(CHK-0991); maintainability_integration:passed(CHK-0992) |
| CMP-120 Plan contrast action | DEF-018 / BP-018 | page | web/index.html: demoBtn; implementation web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011 | behavior:blocked(CHK-0993); states:blocked(CHK-0994); semantics_accessibility:blocked(CHK-0995); layout_content:blocked(CHK-0996); data_effects:blocked(CHK-0997); security_privacy:blocked(CHK-0998); performance_lifecycle:blocked(CHK-0999); maintainability_integration:passed(CHK-1000) |
| CMP-121 Legacy demonstration action | DEF-018 / BP-018 | page | web/index.html: legacyDemoBtn; implementation web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011 | behavior:blocked(CHK-1001); states:blocked(CHK-1002); semantics_accessibility:blocked(CHK-1003); layout_content:blocked(CHK-1004); data_effects:blocked(CHK-1005); security_privacy:blocked(CHK-1006); performance_lifecycle:blocked(CHK-1007); maintainability_integration:passed(CHK-1008) |
| CMP-122 Model-reference/plan result states | DEF-018 / BP-018 | page | web/index.html: demoOut / judgeScore / judgeDimensions; implementation web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions; variants: route /dashboard#demo; conditional and repeated data templates listed in label/locator | investigate / TASK-011, TASK-022, TASK-030 | behavior:blocked(CHK-1009); states:blocked(CHK-1010); semantics_accessibility:blocked(CHK-1011); layout_content:blocked(CHK-1012); data_effects:blocked(CHK-1013); security_privacy:blocked(CHK-1014); performance_lifecycle:blocked(CHK-1015); maintainability_integration:passed(CHK-1016); states:passed(CHK-1303) |
| CMP-171 Capability frontier experiment launcher/dialog — Plan contrast | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#demo #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1551); states:blocked(CHK-1552); semantics_accessibility:blocked(CHK-1553); layout_content:blocked(CHK-1554); data_effects:blocked(CHK-1555); security_privacy:blocked(CHK-1556); performance_lifecycle:blocked(CHK-1557); maintainability_integration:blocked(CHK-1558); maintainability_integration:passed(CHK-1559) |
| CMP-217 Progressive skill selection to execution evidence | DEF-002 / BP-002 | CMP-122 | web/assets/product.js: selectionHTML/skillTraceHTML; #laboratory-live / Product.evidenceHTML .route-evidence > summary; variants: native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1964); states:blocked(CHK-1965); semantics_accessibility:blocked(CHK-1966); layout_content:blocked(CHK-1967); data_effects:blocked(CHK-1968); security_privacy:blocked(CHK-1969); performance_lifecycle:blocked(CHK-1970); maintainability_integration:passed(CHK-1971) |
| CMP-218 Associated-step execution and review action | DEF-030 / BP-030 | CMP-217 | web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent #laboratory-live / Product.evidenceHTML; variants: one original idx per actual matched skill step; no fabricated button for recommended-only skill | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1972); states:blocked(CHK-1973); semantics_accessibility:blocked(CHK-1974); layout_content:blocked(CHK-1975); data_effects:blocked(CHK-1976); security_privacy:blocked(CHK-1977); performance_lifecycle:blocked(CHK-1978); maintainability_integration:passed(CHK-1979) |
| CMP-219 Run-associated current skill passport | DEF-029 / BP-029 | CMP-217 | web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent #laboratory-live / Product.evidenceHTML; variants: parallel current/history read; partial failures, wrong run id and closed/stale responses | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1980); states:blocked(CHK-1981); semantics_accessibility:blocked(CHK-1982); layout_content:blocked(CHK-1983); data_effects:blocked(CHK-1984); security_privacy:blocked(CHK-1985); performance_lifecycle:blocked(CHK-1986); maintainability_integration:passed(CHK-1987) |
| CMP-220 Run/skill/step sphere location link | DEF-002 / BP-002 | CMP-217 | web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent #laboratory-live / Product.evidenceHTML; variants: safe encoded local path; preserved noncontiguous idx; no implicit last_run | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1988); states:blocked(CHK-1989); semantics_accessibility:blocked(CHK-1990); layout_content:blocked(CHK-1991); data_effects:blocked(CHK-1992); security_privacy:blocked(CHK-1993); performance_lifecycle:blocked(CHK-1994); maintainability_integration:passed(CHK-1995) |
| CMP-221 Explicit file/transition recheck action | DEF-028 / BP-028 | CMP-217 | web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent #laboratory-live / Product.evidenceHTML; variants: explicit read-only evidence rehash; no reward/write; stale dialog isolation | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1996); states:blocked(CHK-1997); semantics_accessibility:blocked(CHK-1998); layout_content:blocked(CHK-1999); data_effects:blocked(CHK-2000); security_privacy:blocked(CHK-2001); performance_lifecycle:blocked(CHK-2002); maintainability_integration:passed(CHK-2003) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-011 Plan contrast browser journey and recovery | blocked | CMP-116, CMP-117, CMP-118, CMP-119, CMP-120, CMP-121, CMP-122, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221; The user can complete Plan contrast without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | FND-014 | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-022 Invalid model score and zero-attempt presentation — bounded Node regression | passed | CMP-041, CMP-122, CMP-143; Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts., All assertions in tools/frontend_resilience_check.js: honestScoreAndAttempts pass. | EV-019, FND-006 | [] |
| SCN-074 Final full frontier integration on /dashboard#demo | blocked | CMP-171; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |
| SCN-086 Shared progressive skill trace and paired passport native integration (bounded) | blocked | CMP-202, CMP-203, CMP-204, CMP-205, CMP-206, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221, CMP-158, CMP-159; Actual matched steps and recorded artifacts/checks appear; unexecuted recommendations create no execution facts., Current declaration cannot replace historical SHA; partial failure is explicit and retains readable evidence; same idx in another run cannot focus the wrong current inspector., Parent route and selected skill/original idx survive navigation; no network/reward writes are implied. |  | [] |

## Instance plans

### CMP-116 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#demo and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-117 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#demo and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-118 Scenario selector

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Scenario selector is missing.

**Instance changes:** Keep route /dashboard#demo and locator demoTask behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Scenario selector remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-119 Custom task input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Custom task input is missing.

**Instance changes:** Keep route /dashboard#demo and locator demoTaskText behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Custom task input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-120 Plan contrast action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Plan contrast action is missing.

**Instance changes:** Keep route /dashboard#demo and locator demoBtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Plan contrast action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-121 Legacy demonstration action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Legacy demonstration action is missing.

**Instance changes:** Keep route /dashboard#demo and locator legacyDemoBtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Legacy demonstration action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-122 Model-reference/plan result states

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Model-reference/plan result states is missing.

**Instance changes:** Keep route /dashboard#demo and locator demoOut / judgeScore / judgeDimensions behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Model-reference/plan result states remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-011

### CMP-171 Capability frontier experiment launcher/dialog — Plan contrast

**Rationale:** Shared logic/source inspected; /dashboard#demo has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#demo task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#demo preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-074

### CMP-217 Progressive skill selection to execution evidence

**Rationale:** Actual source and shared logic were reviewed; native Progressive skill selection to execution evidence acceptance in PAGE-011 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML/skillTraceHTML; #laboratory-live / Product.evidenceHTML .route-evidence > summary with variants native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Progressive skill selection to execution evidence is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-011

### CMP-218 Associated-step execution and review action

**Rationale:** Actual source and shared logic were reviewed; native Associated-step execution and review action acceptance in PAGE-011 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent #laboratory-live / Product.evidenceHTML with variants one original idx per actual matched skill step; no fabricated button for recommended-only skill., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Associated-step execution and review action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-011

### CMP-219 Run-associated current skill passport

**Rationale:** Actual source and shared logic were reviewed; native Run-associated current skill passport acceptance in PAGE-011 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent #laboratory-live / Product.evidenceHTML with variants parallel current/history read; partial failures, wrong run id and closed/stale responses., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run-associated current skill passport is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-011

### CMP-220 Run/skill/step sphere location link

**Rationale:** Actual source and shared logic were reviewed; native Run/skill/step sphere location link acceptance in PAGE-011 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent #laboratory-live / Product.evidenceHTML with variants safe encoded local path; preserved noncontiguous idx; no implicit last_run., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run/skill/step sphere location link is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-011

### CMP-221 Explicit file/transition recheck action

**Rationale:** Actual source and shared logic were reviewed; native Explicit file/transition recheck action acceptance in PAGE-011 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent #laboratory-live / Product.evidenceHTML with variants explicit read-only evidence rehash; no reward/write; stale dialog isolation., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Explicit file/transition recheck action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-011
