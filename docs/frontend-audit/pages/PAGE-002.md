# PAGE-002 Conversation

Route `/chat`; source `web/chat.html`; entry evidence EV-003, EV-024, EV-030, EV-038, EV-050, EV-055.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-031 Page shell/navigation/status | DEF-008 / BP-008 | page | web/chat.html: header / nav / main; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0245); states:blocked(CHK-0246); semantics_accessibility:blocked(CHK-0247); layout_content:blocked(CHK-0248); data_effects:blocked(CHK-0249); security_privacy:blocked(CHK-0250); performance_lifecycle:blocked(CHK-0251); maintainability_integration:passed(CHK-0252) |
| CMP-032 Connection settings and toast | DEF-001 / BP-001 | page | web/chat.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002, TASK-017 | behavior:blocked(CHK-0253); states:blocked(CHK-0254); semantics_accessibility:blocked(CHK-0255); layout_content:blocked(CHK-0256); data_effects:blocked(CHK-0257); security_privacy:blocked(CHK-0258); performance_lifecycle:blocked(CHK-0259); maintainability_integration:passed(CHK-0260); security_privacy:passed(CHK-1282) |
| CMP-033 Mobile history toggle | DEF-008 / BP-008 | page | web/chat.html: sessions-toggle; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0261); states:blocked(CHK-0262); semantics_accessibility:blocked(CHK-0263); layout_content:blocked(CHK-0264); data_effects:blocked(CHK-0265); security_privacy:blocked(CHK-0266); performance_lifecycle:blocked(CHK-0267); maintainability_integration:passed(CHK-0268); behavior:passed(CHK-1446); semantics_accessibility:passed(CHK-1447) |
| CMP-034 New session action | DEF-008 / BP-008 | page | web/chat.html: newSession / .newbtn; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0269); states:blocked(CHK-0270); semantics_accessibility:blocked(CHK-0271); layout_content:blocked(CHK-0272); data_effects:blocked(CHK-0273); security_privacy:blocked(CHK-0274); performance_lifecycle:blocked(CHK-0275); maintainability_integration:passed(CHK-0276) |
| CMP-035 Session list template | DEF-008 / BP-008 | page | web/chat.html: slist / renderSidebar; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0277); states:blocked(CHK-0278); semantics_accessibility:blocked(CHK-0279); layout_content:blocked(CHK-0280); data_effects:blocked(CHK-0281); security_privacy:blocked(CHK-0282); performance_lifecycle:blocked(CHK-0283); maintainability_integration:passed(CHK-0284); behavior:passed(CHK-1448); semantics_accessibility:passed(CHK-1449) |
| CMP-036 Current session heading | DEF-008 / BP-008 | page | web/chat.html: sess-title / sess-hint; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0285); states:blocked(CHK-0286); semantics_accessibility:blocked(CHK-0287); layout_content:blocked(CHK-0288); data_effects:blocked(CHK-0289); security_privacy:blocked(CHK-0290); performance_lifecycle:blocked(CHK-0291); maintainability_integration:passed(CHK-0292) |
| CMP-037 Last-run navigation | DEF-008 / BP-008 | page | web/chat.html: last-run; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0293); states:blocked(CHK-0294); semantics_accessibility:blocked(CHK-0295); layout_content:blocked(CHK-0296); data_effects:blocked(CHK-0297); security_privacy:blocked(CHK-0298); performance_lifecycle:blocked(CHK-0299); maintainability_integration:passed(CHK-0300) |
| CMP-038 Message/turn template and hydration | DEF-008 / BP-008 | page | web/chat.html: msgs / renderMain / hydrateTurn; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002, TASK-021 | behavior:blocked(CHK-0301); states:blocked(CHK-0302); semantics_accessibility:blocked(CHK-0303); layout_content:blocked(CHK-0304); data_effects:blocked(CHK-0305); security_privacy:blocked(CHK-0306); performance_lifecycle:blocked(CHK-0307); maintainability_integration:passed(CHK-0308); security_privacy:passed(CHK-1301) |
| CMP-039 Per-turn phase indicators/live DAG | DEF-008 / BP-008 | page | web/chat.html: phaseBarHTML / onEvent; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0309); states:blocked(CHK-0310); semantics_accessibility:blocked(CHK-0311); layout_content:blocked(CHK-0312); data_effects:blocked(CHK-0313); security_privacy:blocked(CHK-0314); performance_lifecycle:blocked(CHK-0315); maintainability_integration:passed(CHK-0316) |
| CMP-040 Detail tabs and toggle | DEF-008 / BP-008 | page | web/chat.html: toggleDetail / dtab / resultHTML; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0317); states:blocked(CHK-0318); semantics_accessibility:blocked(CHK-0319); layout_content:blocked(CHK-0320); data_effects:blocked(CHK-0321); security_privacy:blocked(CHK-0322); performance_lifecycle:blocked(CHK-0323); maintainability_integration:passed(CHK-0324) |
| CMP-041 Step facts/checks/artifact links | DEF-008 / BP-008 | page | web/chat.html: stepCardHTML; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002, TASK-022 | behavior:blocked(CHK-0325); states:blocked(CHK-0326); semantics_accessibility:blocked(CHK-0327); layout_content:blocked(CHK-0328); data_effects:blocked(CHK-0329); security_privacy:blocked(CHK-0330); performance_lifecycle:blocked(CHK-0331); maintainability_integration:passed(CHK-0332); states:passed(CHK-1302) |
| CMP-042 Shared evidence, final reply and assets | DEF-002 / BP-002 | page | web/chat.html: Product.evidenceHTML / replyCardHTML / taskSummaryHTML; implementation web/assets/product.js: Product.evidenceHTML / dagHTML / preview / delegated inspectors; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0333); states:blocked(CHK-0334); semantics_accessibility:blocked(CHK-0335); layout_content:blocked(CHK-0336); data_effects:blocked(CHK-0337); security_privacy:blocked(CHK-0338); performance_lifecycle:blocked(CHK-0339); maintainability_integration:passed(CHK-0340) |
| CMP-043 Question input | DEF-008 / BP-008 | page | web/chat.html: q; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0341); states:blocked(CHK-0342); semantics_accessibility:blocked(CHK-0343); layout_content:blocked(CHK-0344); data_effects:blocked(CHK-0345); security_privacy:blocked(CHK-0346); performance_lifecycle:blocked(CHK-0347); maintainability_integration:passed(CHK-0348) |
| CMP-044 Send action | DEF-008 / BP-008 | page | web/chat.html: send / submitQ; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0349); states:blocked(CHK-0350); semantics_accessibility:blocked(CHK-0351); layout_content:blocked(CHK-0352); data_effects:blocked(CHK-0353); security_privacy:blocked(CHK-0354); performance_lifecycle:blocked(CHK-0355); maintainability_integration:passed(CHK-0356) |
| CMP-045 Active-run cancellation | DEF-008 / BP-008 | page | web/chat.html: cancel-active; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0357); states:blocked(CHK-0358); semantics_accessibility:blocked(CHK-0359); layout_content:blocked(CHK-0360); data_effects:blocked(CHK-0361); security_privacy:blocked(CHK-0362); performance_lifecycle:blocked(CHK-0363); maintainability_integration:passed(CHK-0364) |
| CMP-046 Prompt chips | DEF-008 / BP-008 | page | web/chat.html: chips / useChip; implementation web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; variants: route /chat; conditional and repeated data templates listed in label/locator | investigate / TASK-002 | behavior:blocked(CHK-0365); states:blocked(CHK-0366); semantics_accessibility:blocked(CHK-0367); layout_content:blocked(CHK-0368); data_effects:blocked(CHK-0369); security_privacy:blocked(CHK-0370); performance_lifecycle:blocked(CHK-0371); maintainability_integration:passed(CHK-0372) |
| CMP-162 Capability frontier experiment launcher/dialog — Conversation | DEF-032 / BP-032 | page | web/chat.html: frontier.js/frontier.css includes; /chat #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1470); states:blocked(CHK-1471); semantics_accessibility:blocked(CHK-1472); layout_content:blocked(CHK-1473); data_effects:blocked(CHK-1474); security_privacy:blocked(CHK-1475); performance_lifecycle:blocked(CHK-1476); maintainability_integration:blocked(CHK-1477); maintainability_integration:passed(CHK-1478) |
| CMP-207 Progressive skill selection to execution evidence | DEF-002 / BP-002 | CMP-042 | web/assets/product.js: selectionHTML/skillTraceHTML; resultHTML / Product.evidenceHTML .route-evidence > summary; variants: native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1884); states:blocked(CHK-1885); semantics_accessibility:blocked(CHK-1886); layout_content:blocked(CHK-1887); data_effects:blocked(CHK-1888); security_privacy:blocked(CHK-1889); performance_lifecycle:blocked(CHK-1890); maintainability_integration:passed(CHK-1891) |
| CMP-208 Associated-step execution and review action | DEF-030 / BP-030 | CMP-207 | web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent resultHTML / Product.evidenceHTML; variants: one original idx per actual matched skill step; no fabricated button for recommended-only skill | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1892); states:blocked(CHK-1893); semantics_accessibility:blocked(CHK-1894); layout_content:blocked(CHK-1895); data_effects:blocked(CHK-1896); security_privacy:blocked(CHK-1897); performance_lifecycle:blocked(CHK-1898); maintainability_integration:passed(CHK-1899) |
| CMP-209 Run-associated current skill passport | DEF-029 / BP-029 | CMP-207 | web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent resultHTML / Product.evidenceHTML; variants: parallel current/history read; partial failures, wrong run id and closed/stale responses | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1900); states:blocked(CHK-1901); semantics_accessibility:blocked(CHK-1902); layout_content:blocked(CHK-1903); data_effects:blocked(CHK-1904); security_privacy:blocked(CHK-1905); performance_lifecycle:blocked(CHK-1906); maintainability_integration:passed(CHK-1907) |
| CMP-210 Run/skill/step sphere location link | DEF-002 / BP-002 | CMP-207 | web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent resultHTML / Product.evidenceHTML; variants: safe encoded local path; preserved noncontiguous idx; no implicit last_run | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1908); states:blocked(CHK-1909); semantics_accessibility:blocked(CHK-1910); layout_content:blocked(CHK-1911); data_effects:blocked(CHK-1912); security_privacy:blocked(CHK-1913); performance_lifecycle:blocked(CHK-1914); maintainability_integration:passed(CHK-1915) |
| CMP-211 Explicit file/transition recheck action | DEF-028 / BP-028 | CMP-207 | web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent resultHTML / Product.evidenceHTML; variants: explicit read-only evidence rehash; no reward/write; stale dialog isolation | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1916); states:blocked(CHK-1917); semantics_accessibility:blocked(CHK-1918); layout_content:blocked(CHK-1919); data_effects:blocked(CHK-1920); security_privacy:blocked(CHK-1921); performance_lifecycle:blocked(CHK-1922); maintainability_integration:passed(CHK-1923) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-002 Conversation browser journey and recovery | blocked | CMP-031, CMP-032, CMP-033, CMP-034, CMP-035, CMP-036, CMP-037, CMP-038, CMP-039, CMP-040, CMP-041, CMP-042, CMP-043, CMP-044, CMP-045, CMP-046, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211; The user can complete Conversation without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-021 Stored sessions trust cached rendering and dynamic inline handlers — bounded Node regression | passed | CMP-019, CMP-038; Whitelist plain session/turn fields; reconstruct remote run content; escaped data attributes and native buttons replace interpolated onclick arguments., All assertions in tools/frontend_resilience_check.js: storedHistory pass. | EV-019, FND-005 | [] |
| SCN-022 Invalid model score and zero-attempt presentation — bounded Node regression | passed | CMP-041, CMP-122, CMP-143; Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts., All assertions in tools/frontend_resilience_check.js: honestScoreAndAttempts pass. | EV-019, FND-006 | [] |
| SCN-038 IAB initial viewport chat 1440×900 | passed | CMP-031; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-024 | [] |
| SCN-044 IAB initial viewport chat 390×844 | passed | CMP-031; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-030 | [] |
| SCN-052 IAB Mobile chat drawer Escape/focus | passed | CMP-033, CMP-035; The recorded interaction yields the focus/rotation/replay/layout result stated in the observation., No generalization to untested controls, zoom, OS settings or production. | EV-038 | [] |
| SCN-065 Final full frontier integration on /chat | blocked | CMP-162; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |
| SCN-086 Shared progressive skill trace and paired passport native integration (bounded) | blocked | CMP-202, CMP-203, CMP-204, CMP-205, CMP-206, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221, CMP-158, CMP-159; Actual matched steps and recorded artifacts/checks appear; unexecuted recommendations create no execution facts., Current declaration cannot replace historical SHA; partial failure is explicit and retains readable evidence; same idx in another run cannot focus the wrong current inspector., Parent route and selected skill/original idx survive navigation; no network/reward writes are implied. |  | [] |

## Instance plans

### CMP-031 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /chat and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-032 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /chat and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-033 Mobile history toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Mobile history toggle is missing.

**Instance changes:** Keep route /chat and locator sessions-toggle behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Mobile history toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-034 New session action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for New session action is missing.

**Instance changes:** Keep route /chat and locator newSession / .newbtn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** New session action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-035 Session list template

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Session list template is missing.

**Instance changes:** Keep route /chat and locator slist / renderSidebar behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Session list template remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-036 Current session heading

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Current session heading is missing.

**Instance changes:** Keep route /chat and locator sess-title / sess-hint behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Current session heading remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-037 Last-run navigation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Last-run navigation is missing.

**Instance changes:** Keep route /chat and locator last-run behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Last-run navigation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-038 Message/turn template and hydration

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Message/turn template and hydration is missing.

**Instance changes:** Keep route /chat and locator msgs / renderMain / hydrateTurn behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Message/turn template and hydration remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-039 Per-turn phase indicators/live DAG

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Per-turn phase indicators/live DAG is missing.

**Instance changes:** Keep route /chat and locator phaseBarHTML / onEvent behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Per-turn phase indicators/live DAG remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-040 Detail tabs and toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Detail tabs and toggle is missing.

**Instance changes:** Keep route /chat and locator toggleDetail / dtab / resultHTML behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Detail tabs and toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-041 Step facts/checks/artifact links

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Step facts/checks/artifact links is missing.

**Instance changes:** Keep route /chat and locator stepCardHTML behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Step facts/checks/artifact links remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-042 Shared evidence, final reply and assets

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Shared evidence, final reply and assets is missing.

**Instance changes:** Keep route /chat and locator Product.evidenceHTML / replyCardHTML / taskSummaryHTML behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Shared evidence, final reply and assets remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-043 Question input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Question input is missing.

**Instance changes:** Keep route /chat and locator q behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Question input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-044 Send action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Send action is missing.

**Instance changes:** Keep route /chat and locator send / submitQ behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Send action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-045 Active-run cancellation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Active-run cancellation is missing.

**Instance changes:** Keep route /chat and locator cancel-active behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Active-run cancellation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-046 Prompt chips

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Prompt chips is missing.

**Instance changes:** Keep route /chat and locator chips / useChip behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Prompt chips remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-002

### CMP-162 Capability frontier experiment launcher/dialog — Conversation

**Rationale:** Shared logic/source inspected; /chat has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /chat task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /chat preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-065

### CMP-207 Progressive skill selection to execution evidence

**Rationale:** Actual source and shared logic were reviewed; native Progressive skill selection to execution evidence acceptance in PAGE-002 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML/skillTraceHTML; resultHTML / Product.evidenceHTML .route-evidence > summary with variants native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Progressive skill selection to execution evidence is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-002

### CMP-208 Associated-step execution and review action

**Rationale:** Actual source and shared logic were reviewed; native Associated-step execution and review action acceptance in PAGE-002 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent resultHTML / Product.evidenceHTML with variants one original idx per actual matched skill step; no fabricated button for recommended-only skill., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Associated-step execution and review action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-002

### CMP-209 Run-associated current skill passport

**Rationale:** Actual source and shared logic were reviewed; native Run-associated current skill passport acceptance in PAGE-002 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent resultHTML / Product.evidenceHTML with variants parallel current/history read; partial failures, wrong run id and closed/stale responses., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run-associated current skill passport is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-002

### CMP-210 Run/skill/step sphere location link

**Rationale:** Actual source and shared logic were reviewed; native Run/skill/step sphere location link acceptance in PAGE-002 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent resultHTML / Product.evidenceHTML with variants safe encoded local path; preserved noncontiguous idx; no implicit last_run., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run/skill/step sphere location link is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-002

### CMP-211 Explicit file/transition recheck action

**Rationale:** Actual source and shared logic were reviewed; native Explicit file/transition recheck action acceptance in PAGE-002 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent resultHTML / Product.evidenceHTML with variants explicit read-only evidence rehash; no reward/write; stale dialog isolation., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Explicit file/transition recheck action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-002
