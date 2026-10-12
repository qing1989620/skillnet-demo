# PAGE-005 Skill catalogue

Route `/runs#skills`; source `web/app.html`; entry evidence EV-004, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-061 Page shell/navigation/status | DEF-009 / BP-009 | page | web/app.html: header / nav / main; implementation web/app.html: show / startRun / loadLatest / health / v-intro; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005 | behavior:blocked(CHK-0497); states:blocked(CHK-0498); semantics_accessibility:blocked(CHK-0499); layout_content:blocked(CHK-0500); data_effects:blocked(CHK-0501); security_privacy:blocked(CHK-0502); performance_lifecycle:blocked(CHK-0503); maintainability_integration:passed(CHK-0504) |
| CMP-062 Connection settings and toast | DEF-001 / BP-001 | page | web/app.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005, TASK-017 | behavior:blocked(CHK-0505); states:blocked(CHK-0506); semantics_accessibility:blocked(CHK-0507); layout_content:blocked(CHK-0508); data_effects:blocked(CHK-0509); security_privacy:blocked(CHK-0510); performance_lifecycle:blocked(CHK-0511); maintainability_integration:passed(CHK-0512); security_privacy:passed(CHK-1285) |
| CMP-063 Query input | DEF-011 / BP-011 | page | web/app.html: q; implementation web/app.html: loadSkills / q / skill-domain / skill-source / skills-body; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005 | behavior:blocked(CHK-0513); states:blocked(CHK-0514); semantics_accessibility:blocked(CHK-0515); layout_content:blocked(CHK-0516); data_effects:blocked(CHK-0517); security_privacy:blocked(CHK-0518); performance_lifecycle:blocked(CHK-0519); maintainability_integration:passed(CHK-0520) |
| CMP-064 Domain/source filters | DEF-011 / BP-011 | page | web/app.html: skill-domain / skill-source; implementation web/app.html: loadSkills / q / skill-domain / skill-source / skills-body; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005 | behavior:blocked(CHK-0521); states:blocked(CHK-0522); semantics_accessibility:blocked(CHK-0523); layout_content:blocked(CHK-0524); data_effects:blocked(CHK-0525); security_privacy:blocked(CHK-0526); performance_lifecycle:blocked(CHK-0527); maintainability_integration:passed(CHK-0528) |
| CMP-065 Result row and empty/error templates | DEF-011 / BP-011 | page | web/app.html: skills-body / loadSkills; implementation web/app.html: loadSkills / q / skill-domain / skill-source / skills-body; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005, TASK-018 | behavior:blocked(CHK-0529); states:blocked(CHK-0530); semantics_accessibility:blocked(CHK-0531); layout_content:blocked(CHK-0532); data_effects:blocked(CHK-0533); security_privacy:blocked(CHK-0534); performance_lifecycle:blocked(CHK-0535); maintainability_integration:passed(CHK-0536); data_effects:passed(CHK-1297) |
| CMP-066 Catalogue count | DEF-011 / BP-011 | page | web/app.html: skills-meta; implementation web/app.html: loadSkills / q / skill-domain / skill-source / skills-body; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005 | behavior:blocked(CHK-0537); states:blocked(CHK-0538); semantics_accessibility:blocked(CHK-0539); layout_content:blocked(CHK-0540); data_effects:blocked(CHK-0541); security_privacy:blocked(CHK-0542); performance_lifecycle:blocked(CHK-0543); maintainability_integration:passed(CHK-0544) |
| CMP-067 Pagination actions | DEF-011 / BP-011 | page | web/app.html: skill-prev / skill-next; implementation web/app.html: loadSkills / q / skill-domain / skill-source / skills-body; variants: route /runs#skills; conditional and repeated data templates listed in label/locator | investigate / TASK-005 | behavior:blocked(CHK-0545); states:blocked(CHK-0546); semantics_accessibility:blocked(CHK-0547); layout_content:blocked(CHK-0548); data_effects:blocked(CHK-0549); security_privacy:blocked(CHK-0550); performance_lifecycle:blocked(CHK-0551); maintainability_integration:passed(CHK-0552) |
| CMP-165 Capability frontier experiment launcher/dialog — Skill catalogue | DEF-032 / BP-032 | page | web/app.html: frontier.js/frontier.css includes; /runs#skills #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1497); states:blocked(CHK-1498); semantics_accessibility:blocked(CHK-1499); layout_content:blocked(CHK-1500); data_effects:blocked(CHK-1501); security_privacy:blocked(CHK-1502); performance_lifecycle:blocked(CHK-1503); maintainability_integration:blocked(CHK-1504); maintainability_integration:passed(CHK-1505) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-005 Skill catalogue browser journey and recovery | blocked | CMP-061, CMP-062, CMP-063, CMP-064, CMP-065, CMP-066, CMP-067; The user can complete Skill catalogue without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-018 Chained skill metadata overwrites a newer query — bounded Node regression | passed | CMP-065; Guard after each await/catch/finally and keep a successfully loaded page if optional metadata fails., All assertions in tools/frontend_resilience_check.js: skillsRace pass. | EV-019, FND-002 | [] |
| SCN-068 Final full frontier integration on /runs#skills | blocked | CMP-165; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-061 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /runs#skills and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-062 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /runs#skills and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-063 Query input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Query input is missing.

**Instance changes:** Keep route /runs#skills and locator q behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Query input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-064 Domain/source filters

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Domain/source filters is missing.

**Instance changes:** Keep route /runs#skills and locator skill-domain / skill-source behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Domain/source filters remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-065 Result row and empty/error templates

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Result row and empty/error templates is missing.

**Instance changes:** Keep route /runs#skills and locator skills-body / loadSkills behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Result row and empty/error templates remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-066 Catalogue count

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Catalogue count is missing.

**Instance changes:** Keep route /runs#skills and locator skills-meta behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Catalogue count remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-067 Pagination actions

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Pagination actions is missing.

**Instance changes:** Keep route /runs#skills and locator skill-prev / skill-next behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Pagination actions remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-005

### CMP-165 Capability frontier experiment launcher/dialog — Skill catalogue

**Rationale:** Shared logic/source inspected; /runs#skills has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /runs#skills task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /runs#skills preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-068
