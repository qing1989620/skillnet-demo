# PAGE-009 Spherical skill network

Route `/graph?run=&skill=&domain=`; source `web/graph.html`; entry evidence EV-006, EV-027, EV-033, EV-037, EV-050, EV-055, EV-061.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-090 Page shell/navigation/status | DEF-015 / BP-015 | page | web/graph.html: header / nav / main; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0745); states:blocked(CHK-0746); semantics_accessibility:blocked(CHK-0747); layout_content:blocked(CHK-0748); data_effects:blocked(CHK-0749); security_privacy:blocked(CHK-0750); performance_lifecycle:blocked(CHK-0751); maintainability_integration:passed(CHK-0752) |
| CMP-091 Connection settings and toast | DEF-001 / BP-001 | page | web/graph.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009, TASK-017 | behavior:blocked(CHK-0753); states:blocked(CHK-0754); semantics_accessibility:blocked(CHK-0755); layout_content:blocked(CHK-0756); data_effects:blocked(CHK-0757); security_privacy:blocked(CHK-0758); performance_lifecycle:blocked(CHK-0759); maintainability_integration:passed(CHK-0760); security_privacy:passed(CHK-1289) |
| CMP-092 Full catalogue sphere | DEF-003 / BP-003 | page | web/graph.html: cv; implementation web/assets/sphere.js: SkillSphere.create; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0761); states:blocked(CHK-0762); semantics_accessibility:blocked(CHK-0763); layout_content:blocked(CHK-0764); data_effects:blocked(CHK-0765); security_privacy:blocked(CHK-0766); performance_lifecycle:blocked(CHK-0767); maintainability_integration:passed(CHK-0768) |
| CMP-093 Skill query input | DEF-015 / BP-015 | page | web/graph.html: graph-q; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009, TASK-032 | behavior:blocked(CHK-0769); states:blocked(CHK-0770); semantics_accessibility:blocked(CHK-0771); layout_content:blocked(CHK-0772); data_effects:blocked(CHK-0773); security_privacy:blocked(CHK-0774); performance_lifecycle:blocked(CHK-0775); maintainability_integration:passed(CHK-0776); behavior:passed(CHK-1440); semantics_accessibility:passed(CHK-1441) |
| CMP-094 Search result buttons/empty template | DEF-015 / BP-015 | page | web/graph.html: graph-results; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0777); states:blocked(CHK-0778); semantics_accessibility:blocked(CHK-0779); layout_content:blocked(CHK-0780); data_effects:blocked(CHK-0781); security_privacy:blocked(CHK-0782); performance_lifecycle:blocked(CHK-0783); maintainability_integration:passed(CHK-0784) |
| CMP-095 Domain filter | DEF-015 / BP-015 | page | web/graph.html: graph-domain; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0785); states:blocked(CHK-0786); semantics_accessibility:blocked(CHK-0787); layout_content:blocked(CHK-0788); data_effects:blocked(CHK-0789); security_privacy:blocked(CHK-0790); performance_lifecycle:blocked(CHK-0791); maintainability_integration:passed(CHK-0792) |
| CMP-096 Relation filters | DEF-015 / BP-015 | page | web/graph.html: [data-relation]; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0793); states:blocked(CHK-0794); semantics_accessibility:blocked(CHK-0795); layout_content:blocked(CHK-0796); data_effects:blocked(CHK-0797); security_privacy:blocked(CHK-0798); performance_lifecycle:blocked(CHK-0799); maintainability_integration:passed(CHK-0800) |
| CMP-097 Neighbours toggle | DEF-015 / BP-015 | page | web/graph.html: graph-neighbors; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0801); states:blocked(CHK-0802); semantics_accessibility:blocked(CHK-0803); layout_content:blocked(CHK-0804); data_effects:blocked(CHK-0805); security_privacy:blocked(CHK-0806); performance_lifecycle:blocked(CHK-0807); maintainability_integration:passed(CHK-0808) |
| CMP-098 Task-only toggle | DEF-015 / BP-015 | page | web/graph.html: graph-task-only / graph-task-label; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0809); states:blocked(CHK-0810); semantics_accessibility:blocked(CHK-0811); layout_content:blocked(CHK-0812); data_effects:blocked(CHK-0813); security_privacy:blocked(CHK-0814); performance_lifecycle:blocked(CHK-0815); maintainability_integration:passed(CHK-0816) |
| CMP-099 Visible/catalogue HUD | DEF-015 / BP-015 | page | web/graph.html: graph-visible / nN / nE / nD; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0817); states:blocked(CHK-0818); semantics_accessibility:blocked(CHK-0819); layout_content:blocked(CHK-0820); data_effects:blocked(CHK-0821); security_privacy:blocked(CHK-0822); performance_lifecycle:blocked(CHK-0823); maintainability_integration:passed(CHK-0824) |
| CMP-100 Recorded-task panel and run link | DEF-015 / BP-015 | page | web/graph.html: graph-task-panel / graph-run-link; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator; recorded all/one original idx; manual unbound/missing historical node; safe run step return link | investigate / TASK-009, TASK-040, TASK-041 | behavior:blocked(CHK-0825); states:blocked(CHK-0826); semantics_accessibility:blocked(CHK-0827); layout_content:blocked(CHK-0828); data_effects:blocked(CHK-0829); security_privacy:blocked(CHK-0830); performance_lifecycle:blocked(CHK-0831); maintainability_integration:passed(CHK-0832); layout_content:passed(CHK-2004); behavior:passed(CHK-2012) |
| CMP-101 Capability report action | DEF-002 / BP-002 | page | web/graph.html: graph-capabilities; implementation web/assets/product.js: Product.evidenceHTML / dagHTML / preview / delegated inspectors; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0833); states:blocked(CHK-0834); semantics_accessibility:blocked(CHK-0835); layout_content:blocked(CHK-0836); data_effects:blocked(CHK-0837); security_privacy:blocked(CHK-0838); performance_lifecycle:blocked(CHK-0839); maintainability_integration:passed(CHK-0840) |
| CMP-102 Zoom actions | DEF-015 / BP-015 | page | web/graph.html: btnZoomIn / btnZoomOut; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0841); states:blocked(CHK-0842); semantics_accessibility:blocked(CHK-0843); layout_content:blocked(CHK-0844); data_effects:blocked(CHK-0845); security_privacy:blocked(CHK-0846); performance_lifecycle:blocked(CHK-0847); maintainability_integration:passed(CHK-0848) |
| CMP-103 Reset action | DEF-015 / BP-015 | page | web/graph.html: btnReset; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0849); states:blocked(CHK-0850); semantics_accessibility:blocked(CHK-0851); layout_content:blocked(CHK-0852); data_effects:blocked(CHK-0853); security_privacy:blocked(CHK-0854); performance_lifecycle:blocked(CHK-0855); maintainability_integration:passed(CHK-0856) |
| CMP-104 Rotation pause action | DEF-015 / BP-015 | page | web/graph.html: btnPause; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009, TASK-028 | behavior:blocked(CHK-0857); states:blocked(CHK-0858); semantics_accessibility:blocked(CHK-0859); layout_content:blocked(CHK-0860); data_effects:blocked(CHK-0861); security_privacy:blocked(CHK-0862); performance_lifecycle:blocked(CHK-0863); maintainability_integration:passed(CHK-0864); behavior:passed(CHK-1444); semantics_accessibility:passed(CHK-1445) |
| CMP-105 Labels toggle | DEF-015 / BP-015 | page | web/graph.html: btnLabel; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0865); states:blocked(CHK-0866); semantics_accessibility:blocked(CHK-0867); layout_content:blocked(CHK-0868); data_effects:blocked(CHK-0869); security_privacy:blocked(CHK-0870); performance_lifecycle:blocked(CHK-0871); maintainability_integration:passed(CHK-0872) |
| CMP-106 Evolved-only toggle | DEF-015 / BP-015 | page | web/graph.html: btnEvolved; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009, TASK-028 | behavior:blocked(CHK-0873); states:blocked(CHK-0874); semantics_accessibility:blocked(CHK-0875); layout_content:blocked(CHK-0876); data_effects:blocked(CHK-0877); security_privacy:blocked(CHK-0878); performance_lifecycle:blocked(CHK-0879); maintainability_integration:passed(CHK-0880) |
| CMP-107 Selected node card and close | DEF-015 / BP-015 | page | web/graph.html: card / .close / cName; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009, TASK-028 | behavior:blocked(CHK-0881); states:blocked(CHK-0882); semantics_accessibility:blocked(CHK-0883); layout_content:blocked(CHK-0884); data_effects:blocked(CHK-0885); security_privacy:blocked(CHK-0886); performance_lifecycle:blocked(CHK-0887); maintainability_integration:passed(CHK-0888); behavior:passed(CHK-1442); semantics_accessibility:passed(CHK-1443); states:passed(CHK-1633) |
| CMP-108 Related skill controls | DEF-015 / BP-015 | page | web/graph.html: cRel / [data-related]; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator; outgoing requires / incoming required_by / compose / similar groups under active filters; all vs visible counts; no-visible and no-registered cases | investigate / TASK-009, TASK-040 | behavior:blocked(CHK-0889); states:blocked(CHK-0890); semantics_accessibility:blocked(CHK-0891); layout_content:blocked(CHK-0892); data_effects:blocked(CHK-0893); security_privacy:blocked(CHK-0894); performance_lifecycle:blocked(CHK-0895); maintainability_integration:passed(CHK-0896); behavior:passed(CHK-1623); behavior:passed(CHK-2013) |
| CMP-109 Capability/version/resources contract | DEF-015 / BP-015 | page | web/graph.html: cDom / cKv / cContract / cContractLink; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0897); states:blocked(CHK-0898); semantics_accessibility:blocked(CHK-0899); layout_content:blocked(CHK-0900); data_effects:blocked(CHK-0901); security_privacy:blocked(CHK-0902); performance_lifecycle:blocked(CHK-0903); maintainability_integration:passed(CHK-0904); states:passed(CHK-1634) |
| CMP-110 Loading/error overlay and tooltip | DEF-015 / BP-015 | page | web/graph.html: load / tip; implementation web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls; variants: route /graph?run=&skill=&domain=; conditional and repeated data templates listed in label/locator | investigate / TASK-009 | behavior:blocked(CHK-0905); states:blocked(CHK-0906); semantics_accessibility:blocked(CHK-0907); layout_content:blocked(CHK-0908); data_effects:blocked(CHK-0909); security_privacy:blocked(CHK-0910); performance_lifecycle:blocked(CHK-0911); maintainability_integration:passed(CHK-0912) |
| CMP-169 Capability frontier experiment launcher/dialog — Spherical skill network | DEF-032 / BP-032 | page | web/graph.html: frontier.js/frontier.css includes; /graph?run=&skill=&domain= #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038 | behavior:blocked(CHK-1533); states:blocked(CHK-1534); semantics_accessibility:blocked(CHK-1535); layout_content:blocked(CHK-1536); data_effects:blocked(CHK-1537); security_privacy:blocked(CHK-1538); performance_lifecycle:blocked(CHK-1539); maintainability_integration:blocked(CHK-1540); maintainability_integration:passed(CHK-1541) |
| CMP-191 Original-step selector | DEF-015 / BP-015 | CMP-100 | web/assets/graph-sphere.js: #graph-step / taskView/setStep; variants: all/step:<original noncontiguous idx>/manual/retired skill | investigate / TASK-039, TASK-040, TASK-041 | data_effects:passed(CHK-1626); states:passed(CHK-1635); behavior:blocked(CHK-1756); states:blocked(CHK-1757); semantics_accessibility:blocked(CHK-1758); layout_content:blocked(CHK-1759); data_effects:blocked(CHK-1760); security_privacy:blocked(CHK-1761); performance_lifecycle:blocked(CHK-1762); maintainability_integration:passed(CHK-1763); behavior:passed(CHK-2014) |
| CMP-192 Task evidence disclosure | DEF-015 / BP-015 | CMP-100 | web/assets/graph-sphere.js: #graph-task-panel .graph-task-details / #graph-task-detail; variants: closed/open; all-step navigation or selected input/effect/check detail | investigate / TASK-039, TASK-040, TASK-041 | data_effects:passed(CHK-1627); behavior:blocked(CHK-1764); states:blocked(CHK-1765); semantics_accessibility:blocked(CHK-1766); layout_content:blocked(CHK-1767); data_effects:blocked(CHK-1768); security_privacy:blocked(CHK-1769); performance_lifecycle:blocked(CHK-1770); maintainability_integration:passed(CHK-1771); behavior:passed(CHK-2015) |
| CMP-193 All-task step navigation template | DEF-015 / BP-015 | CMP-192 | web/assets/graph-sphere.js: [data-graph-step] / taskDetailHTML/setStep; variants: one native button per actually recorded idx, including manual and missing skill | investigate / TASK-039, TASK-040 | data_effects:passed(CHK-1628); behavior:blocked(CHK-1772); states:blocked(CHK-1773); semantics_accessibility:blocked(CHK-1774); layout_content:blocked(CHK-1775); data_effects:blocked(CHK-1776); security_privacy:blocked(CHK-1777); performance_lifecycle:blocked(CHK-1778); maintainability_integration:passed(CHK-1779) |
| CMP-194 Recorded input/output evidence region | DEF-015 / BP-015 | CMP-192 | web/assets/graph-sphere.js: .graph-step-files / taskDetailHTML; variants: declared file contract separate from recorded input SHA/source run and actual output | investigate / TASK-039, TASK-040 | data_effects:passed(CHK-1629); behavior:blocked(CHK-1780); states:blocked(CHK-1781); semantics_accessibility:blocked(CHK-1782); layout_content:blocked(CHK-1783); data_effects:blocked(CHK-1784); security_privacy:blocked(CHK-1785); performance_lifecycle:blocked(CHK-1786); maintainability_integration:passed(CHK-1787); behavior:passed(CHK-2016) |
| CMP-195 Step checks, state conditions and unknown boundaries | DEF-015 / BP-015 | CMP-192 | web/assets/graph-sphere.js: #graph-task-detail details / checksHTML / Product.stateKernelHTML; variants: passed/failed/unknown program and independent criteria; old history no policy | investigate / TASK-039, TASK-040 | data_effects:passed(CHK-1630); behavior:blocked(CHK-1788); states:blocked(CHK-1789); semantics_accessibility:blocked(CHK-1790); layout_content:blocked(CHK-1791); data_effects:blocked(CHK-1792); security_privacy:blocked(CHK-1793); performance_lifecycle:blocked(CHK-1794); maintainability_integration:passed(CHK-1795); behavior:passed(CHK-2017) |
| CMP-196 Back to previously explored skill | DEF-015 / BP-015 | CMP-107 | web/assets/graph-sphere.js: #graph-back / GraphExplorer.history; variants: first visit disabled/back history/current filter hidden peer; run/step retained | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1624); states:passed(CHK-1636); behavior:blocked(CHK-1796); states:blocked(CHK-1797); semantics_accessibility:blocked(CHK-1798); layout_content:blocked(CHK-1799); data_effects:blocked(CHK-1800); security_privacy:blocked(CHK-1801); performance_lifecycle:blocked(CHK-1802); maintainability_integration:passed(CHK-1803); behavior:passed(CHK-2018) |
| CMP-197 Selection and filter-hidden task context | DEF-015 / BP-015 | CMP-107 | web/assets/graph-sphere.js: #graph-card-context / #graph-selected-note / renderTaskNote; variants: current catalogue versus recorded adoption; hidden/missing/manual context | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1625); behavior:blocked(CHK-1804); states:blocked(CHK-1805); semantics_accessibility:blocked(CHK-1806); layout_content:blocked(CHK-1807); data_effects:blocked(CHK-1808); security_privacy:blocked(CHK-1809); performance_lifecycle:blocked(CHK-1810); maintainability_integration:passed(CHK-1811); behavior:passed(CHK-2019) |
| CMP-198 Selected-step code/contract/repair inspector action | DEF-030 / BP-030 | CMP-192 | web/assets/graph-sphere.js: #graph-task-detail [data-kernel-step] → Product.focusStep; variants: specific run/original idx; isolated dialog on graph; code/resources/artifacts preserved | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1812); states:blocked(CHK-1813); semantics_accessibility:blocked(CHK-1814); layout_content:blocked(CHK-1815); data_effects:blocked(CHK-1816); security_privacy:blocked(CHK-1817); performance_lifecycle:blocked(CHK-1818); maintainability_integration:passed(CHK-1819) |
| CMP-199 Graph nested step passport with historical context | DEF-029 / BP-029 | CMP-198 | web/assets/graph-sphere.js: #kernel-step-dialog [data-capability-skill] → inspectPassport; variants: current skill declaration plus actual graph run/step; manual has no skill passport | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1820); states:blocked(CHK-1821); semantics_accessibility:blocked(CHK-1822); layout_content:blocked(CHK-1823); data_effects:blocked(CHK-1824); security_privacy:blocked(CHK-1825); performance_lifecycle:blocked(CHK-1826); maintainability_integration:passed(CHK-1827) |
| CMP-200 Recorded input preview action template | DEF-031 / BP-031 | CMP-194 | web/assets/graph-sphere.js: .graph-step-files [data-artifact-preview] for input_artifacts → Product.preview; variants: original source_run_id/name/SHA; unavailable old input explicit; safe preview | investigate / TASK-039, TASK-040 | data_effects:passed(CHK-1631); behavior:blocked(CHK-1828); states:blocked(CHK-1829); semantics_accessibility:blocked(CHK-1830); layout_content:blocked(CHK-1831); data_effects:blocked(CHK-1832); security_privacy:blocked(CHK-1833); performance_lifecycle:blocked(CHK-1834); maintainability_integration:passed(CHK-1835) |
| CMP-201 Recorded output preview action template | DEF-031 / BP-031 | CMP-194 | web/assets/graph-sphere.js: .graph-step-files .product-files [data-artifact-preview] for step.artifacts; variants: actual generated file/name/SHA under current run; no expected artifact fabrication | investigate / TASK-039, TASK-040 | data_effects:passed(CHK-1632); behavior:blocked(CHK-1836); states:blocked(CHK-1837); semantics_accessibility:blocked(CHK-1838); layout_content:blocked(CHK-1839); data_effects:blocked(CHK-1840); security_privacy:blocked(CHK-1841); performance_lifecycle:blocked(CHK-1842); maintainability_integration:passed(CHK-1843) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-009 Spherical skill network browser journey and recovery | blocked | CMP-090, CMP-091, CMP-092, CMP-093, CMP-094, CMP-095, CMP-096, CMP-097, CMP-098, CMP-099, CMP-100, CMP-101, CMP-102, CMP-103, CMP-104, CMP-105, CMP-106, CMP-107, CMP-108, CMP-109, CMP-110, CMP-191, CMP-192, CMP-193, CMP-194, CMP-195, CMP-196, CMP-197, CMP-198, CMP-199, CMP-200, CMP-201; The user can complete Spherical skill network without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | FND-012 | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-041 IAB initial viewport graph 1440×900 | passed | CMP-090; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-027 | [] |
| SCN-047 IAB initial viewport graph 390×844 | passed | CMP-090; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-033 | [] |
| SCN-051 IAB Graph Enter/Escape/Space and selected-detail focus | passed | CMP-093, CMP-107, CMP-104; The recorded interaction yields the focus/rotation/replay/layout result stated in the observation., No generalization to untested controls, zoom, OS settings or production. | EV-037, FND-016 | [] |
| SCN-072 Final full frontier integration on /graph?run=&skill=&domain= | blocked | CMP-169; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |
| SCN-085 Graph native original-step and typed-relation exploration (bounded) | blocked | CMP-191, CMP-192, CMP-193, CMP-194, CMP-195, CMP-196, CMP-197, CMP-198, CMP-199, CMP-200, CMP-201, CMP-100, CMP-108; Manual step highlights no invented skill; missing historical skills stay missing; original idx and run are preserved., Inputs/outputs and checks come from recorded run; missing independent/state evidence stays unknown., Directed declaration relation and back history remain clear; task/filter surfaces must not overlap, and original globe remains operable. |  | [] |
| SCN-091 Graph directed relation groups, active filters and history (controlled logic only) | passed | CMP-108, CMP-196, CMP-197; Requires/required-by/compose/similar groups follow declared edge direction and visibility; exploration back retains explicit run/step context. | EV-057 | [] |
| SCN-092 Graph original indices, manual/missing skills and actual evidence (controlled logic only) | passed | CMP-191, CMP-192, CMP-193, CMP-194, CMP-195, CMP-200, CMP-201; Recorded idx, source input SHA/run, actual output and check records remain distinct from declared contract; manual has no fake skill; missing policy/check remains unknown. | EV-057 | [] |
| SCN-093 Graph stale declaration and retained globe controls (controlled logic only) | passed | CMP-107, CMP-109, CMP-191, CMP-196; Newer/closed selection cannot be overwritten by stale passport; zoom/pause/labels/reset and retained task overlay still operate in the controlled DOM. | EV-057 | [] |
| SCN-096 Current repair check for v10 graph task/filter panel overlap | passed | CMP-100, CMP-191, CMP-192; The reproduced task/filter collision is absent at 1440x900; opening filters hides the same task, and closing restores selection/expanded evidence., At390x844, filter/card coexistence uses explicit task hide/restore and no document horizontal overflow; original selected step/details are retained. | EV-061, EV-062, FND-022 | [{"baseline": "v20261012.10 / 1440x900", "status": "failed", "evidence_ids": ["EV-059", "EV-060"], "finding_ids": ["FND-022"], "actual": "task top371 overlaps filter362..401; screenshot conceals task heading"}] |
| SCN-098 Actual graph manual step, real evidence and typed relation subset | passed | CMP-100, CMP-108, CMP-191, CMP-192, CMP-194, CMP-195, CMP-196, CMP-197; Manual remains unbound, actual record evidence and unknown independent criteria remain distinct., Declared direction, reciprocal peer and filter counts are actual observed states; relationship is not proof of causal execution. | EV-061 | [] |

## Instance plans

### CMP-090 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-091 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-092 Full catalogue sphere

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Full catalogue sphere is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator cv behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Full catalogue sphere remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-093 Skill query input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Skill query input is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-q behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Skill query input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009, SCN-051

### CMP-094 Search result buttons/empty template

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Search result buttons/empty template is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-results behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Search result buttons/empty template remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-095 Domain filter

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Domain filter is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-domain behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Domain filter remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-096 Relation filters

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Relation filters is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator [data-relation] behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Relation filters remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-097 Neighbours toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Neighbours toggle is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-neighbors behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Neighbours toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-098 Task-only toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Task-only toggle is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-task-only / graph-task-label behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Task-only toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-099 Visible/catalogue HUD

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Visible/catalogue HUD is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-visible / nN / nE / nD behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Visible/catalogue HUD remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-100 Recorded-task panel and run link

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Recorded-task panel and run link is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-task-panel / graph-run-link behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Recorded-task panel and run link remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009, SCN-085, SCN-096, SCN-098

### CMP-101 Capability report action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Capability report action is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator graph-capabilities behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Capability report action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-102 Zoom actions

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Zoom actions is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator btnZoomIn / btnZoomOut behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Zoom actions remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-103 Reset action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Reset action is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator btnReset behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Reset action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-104 Rotation pause action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Rotation pause action is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator btnPause behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Rotation pause action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-105 Labels toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Labels toggle is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator btnLabel behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Labels toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-106 Evolved-only toggle

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Evolved-only toggle is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator btnEvolved behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Evolved-only toggle remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-107 Selected node card and close

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Selected node card and close is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator card / .close / cName behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Selected node card and close remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-108 Related skill controls

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Related skill controls is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator cRel / [data-related] behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Related skill controls remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009, SCN-085, SCN-098

### CMP-109 Capability/version/resources contract

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Capability/version/resources contract is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator cDom / cKv / cContract / cContractLink behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Capability/version/resources contract remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-110 Loading/error overlay and tooltip

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Loading/error overlay and tooltip is missing.

**Instance changes:** Keep route /graph?run=&skill=&domain= and locator load / tip behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Loading/error overlay and tooltip remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-009

### CMP-169 Capability frontier experiment launcher/dialog — Spherical skill network

**Rationale:** Shared logic/source inspected; /graph?run=&skill=&domain= has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original /graph?run=&skill=&domain= task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** /graph?run=&skill=&domain= preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-072

### CMP-191 Original-step selector

**Rationale:** Actual source and shared logic were reviewed; native Original-step selector acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #graph-step / taskView/setStep with variants all/step:<original noncontiguous idx>/manual/retired skill., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Original-step selector is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009, SCN-096, SCN-098

### CMP-192 Task evidence disclosure

**Rationale:** Actual source and shared logic were reviewed; native Task evidence disclosure acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #graph-task-panel .graph-task-details / #graph-task-detail with variants closed/open; all-step navigation or selected input/effect/check detail., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Task evidence disclosure is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009, SCN-096, SCN-098

### CMP-193 All-task step navigation template

**Rationale:** Actual source and shared logic were reviewed; native All-task step navigation template acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: [data-graph-step] / taskDetailHTML/setStep with variants one native button per actually recorded idx, including manual and missing skill., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** All-task step navigation template is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009

### CMP-194 Recorded input/output evidence region

**Rationale:** Actual source and shared logic were reviewed; native Recorded input/output evidence region acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: .graph-step-files / taskDetailHTML with variants declared file contract separate from recorded input SHA/source run and actual output., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Recorded input/output evidence region is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009, SCN-098

### CMP-195 Step checks, state conditions and unknown boundaries

**Rationale:** Actual source and shared logic were reviewed; native Step checks, state conditions and unknown boundaries acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #graph-task-detail details / checksHTML / Product.stateKernelHTML with variants passed/failed/unknown program and independent criteria; old history no policy., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Step checks, state conditions and unknown boundaries is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009, SCN-098

### CMP-196 Back to previously explored skill

**Rationale:** Actual source and shared logic were reviewed; native Back to previously explored skill acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #graph-back / GraphExplorer.history with variants first visit disabled/back history/current filter hidden peer; run/step retained., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Back to previously explored skill is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009, SCN-098

### CMP-197 Selection and filter-hidden task context

**Rationale:** Actual source and shared logic were reviewed; native Selection and filter-hidden task context acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #graph-card-context / #graph-selected-note / renderTaskNote with variants current catalogue versus recorded adoption; hidden/missing/manual context., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selection and filter-hidden task context is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009, SCN-098

### CMP-198 Selected-step code/contract/repair inspector action

**Rationale:** Actual source and shared logic were reviewed; native Selected-step code/contract/repair inspector action acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #graph-task-detail [data-kernel-step] → Product.focusStep with variants specific run/original idx; isolated dialog on graph; code/resources/artifacts preserved., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected-step code/contract/repair inspector action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009

### CMP-199 Graph nested step passport with historical context

**Rationale:** Actual source and shared logic were reviewed; native Graph nested step passport with historical context acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: #kernel-step-dialog [data-capability-skill] → inspectPassport with variants current skill declaration plus actual graph run/step; manual has no skill passport., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Graph nested step passport with historical context is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009

### CMP-200 Recorded input preview action template

**Rationale:** Actual source and shared logic were reviewed; native Recorded input preview action template acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: .graph-step-files [data-artifact-preview] for input_artifacts → Product.preview with variants original source_run_id/name/SHA; unavailable old input explicit; safe preview., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Recorded input preview action template is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009

### CMP-201 Recorded output preview action template

**Rationale:** Actual source and shared logic were reviewed; native Recorded output preview action template acceptance in PAGE-009 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/graph-sphere.js: .graph-step-files .product-files [data-artifact-preview] for step.artifacts with variants actual generated file/name/SHA under current run; no expected artifact fabrication., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Recorded output preview action template is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-085, SCN-009
