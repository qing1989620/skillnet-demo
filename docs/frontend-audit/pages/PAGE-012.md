# PAGE-012 Developer skill inspector

Route `/dashboard#skills?skill=`; source `web/index.html`; entry evidence EV-007, EV-050.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-123 Page shell/navigation/status | DEF-016 / BP-016 | page | web/index.html: header / nav / main; implementation web/index.html: tabs / metabar / show; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012 | behavior:blocked(CHK-1021); states:blocked(CHK-1022); semantics_accessibility:blocked(CHK-1023); layout_content:blocked(CHK-1024); data_effects:blocked(CHK-1025); security_privacy:blocked(CHK-1026); performance_lifecycle:blocked(CHK-1027); maintainability_integration:passed(CHK-1028) |
| CMP-124 Connection settings and toast | DEF-001 / BP-001 | page | web/index.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012, TASK-017 | behavior:blocked(CHK-1029); states:blocked(CHK-1030); semantics_accessibility:blocked(CHK-1031); layout_content:blocked(CHK-1032); data_effects:blocked(CHK-1033); security_privacy:blocked(CHK-1034); performance_lifecycle:blocked(CHK-1035); maintainability_integration:passed(CHK-1036); security_privacy:passed(CHK-1292) |
| CMP-125 Skill query input | DEF-019 / BP-019 | page | web/index.html: skillQ; implementation web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012 | behavior:blocked(CHK-1037); states:blocked(CHK-1038); semantics_accessibility:blocked(CHK-1039); layout_content:blocked(CHK-1040); data_effects:blocked(CHK-1041); security_privacy:blocked(CHK-1042); performance_lifecycle:blocked(CHK-1043); maintainability_integration:passed(CHK-1044) |
| CMP-126 Domain filter | DEF-019 / BP-019 | page | web/index.html: skillDomain; implementation web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012 | behavior:blocked(CHK-1045); states:blocked(CHK-1046); semantics_accessibility:blocked(CHK-1047); layout_content:blocked(CHK-1048); data_effects:blocked(CHK-1049); security_privacy:blocked(CHK-1050); performance_lifecycle:blocked(CHK-1051); maintainability_integration:passed(CHK-1052) |
| CMP-127 Skill list/count/empty/error templates | DEF-019 / BP-019 | page | web/index.html: skillList / skillCount; implementation web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012 | behavior:blocked(CHK-1053); states:blocked(CHK-1054); semantics_accessibility:blocked(CHK-1055); layout_content:blocked(CHK-1056); data_effects:blocked(CHK-1057); security_privacy:blocked(CHK-1058); performance_lifecycle:blocked(CHK-1059); maintainability_integration:passed(CHK-1060) |
| CMP-128 Skill contract/detail template | DEF-019 / BP-019 | page | web/index.html: skillDetail; implementation web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012 | behavior:blocked(CHK-1061); states:blocked(CHK-1062); semantics_accessibility:blocked(CHK-1063); layout_content:blocked(CHK-1064); data_effects:blocked(CHK-1065); security_privacy:blocked(CHK-1066); performance_lifecycle:blocked(CHK-1067); maintainability_integration:passed(CHK-1068) |
| CMP-129 Catalogue pagination controls | DEF-019 / BP-019 | page | web/index.html: catalog-prev / catalog-next; implementation web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next; variants: route /dashboard#skills?skill=; conditional and repeated data templates listed in label/locator | investigate / TASK-012 | behavior:blocked(CHK-1069); states:blocked(CHK-1070); semantics_accessibility:blocked(CHK-1071); layout_content:blocked(CHK-1072); data_effects:blocked(CHK-1073); security_privacy:blocked(CHK-1074); performance_lifecycle:blocked(CHK-1075); maintainability_integration:passed(CHK-1076) |
| CMP-172 Capability frontier experiment launcher/dialog — Developer skill inspector | DEF-032 / BP-032 | page | web/index.html: frontier.js/frontier.css includes; /dashboard#skills?skill= #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1560); states:blocked(CHK-1561); semantics_accessibility:blocked(CHK-1562); layout_content:blocked(CHK-1563); data_effects:blocked(CHK-1564); security_privacy:blocked(CHK-1565); performance_lifecycle:blocked(CHK-1566); maintainability_integration:blocked(CHK-1567); maintainability_integration:passed(CHK-1568) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-012 Developer skill inspector browser journey and recovery | blocked | CMP-123, CMP-124, CMP-125, CMP-126, CMP-127, CMP-128, CMP-129; The user can complete Developer skill inspector without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. |  | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-075 Final full frontier integration on /dashboard#skills?skill= | blocked | CMP-172; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |

## Instance plans

### CMP-123 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-124 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-125 Skill query input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Skill query input is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator skillQ behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Skill query input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-126 Domain filter

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Domain filter is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator skillDomain behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Domain filter remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-127 Skill list/count/empty/error templates

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Skill list/count/empty/error templates is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator skillList / skillCount behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Skill list/count/empty/error templates remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-128 Skill contract/detail template

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Skill contract/detail template is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator skillDetail behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Skill contract/detail template remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-129 Catalogue pagination controls

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Catalogue pagination controls is missing.

**Instance changes:** Keep route /dashboard#skills?skill= and locator catalog-prev / catalog-next behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Catalogue pagination controls remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-012

### CMP-172 Capability frontier experiment launcher/dialog — Developer skill inspector

**Rationale:** Shared logic/source inspected; /dashboard#skills?skill= has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /dashboard#skills?skill= task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /dashboard#skills?skill= preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-075
