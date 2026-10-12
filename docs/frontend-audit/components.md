# Component contracts and disposition

Generated from audit.json: 33 actual implementation definitions, 221 logical component instances. Each instance has eight review dimensions, a blueprint, a disposition and verification tasks. Shared controlled logic evidence does not certify every native parent view.

## BP-001 Shared navigation/connection settings/toasts

Implementation: web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions

Current contract: Token validation commits only the current validated candidate; session cache is plain data. Native dialog focus remains a browser acceptance item.

**Change locations:** web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions

| Contract dimension | Target |
|---|---|
| responsibility | Token validation commits only the current validated candidate; session cache is plain data. Native dialog focus remains a browser acceptance item. |
| interface | Preserve the existing route, DOM IDs and public callbacks at UI.bootstrap / connection dialog / UI.json / UI.readSessions; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-002 Result/evidence/capability UI

Implementation: web/assets/product.js: Product.evidenceHTML / dagHTML / preview / delegated inspectors

Current contract: Product selection/evidence surfaces use graphURL/runURL to preserve encoded run/skill/domain/step. skillTraceHTML expands actual matched steps/registered artifacts/recorded checks; stepReviewHTML keeps version/scope explicit. No actual step means no invented execution button.

**Change locations:** web/assets/product.js: Product.evidenceHTML / dagHTML / preview / delegated inspectors, web/assets/product.js: graphURL/runURL/skillTraceHTML/stepReviewHTML/selectionHTML/capabilityReportHTML, web/assets/showcase.js: renderNetwork/inspectStep/renderOutput

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Product.graphURL({run,skill,domain,step}) and runURL({run,step}) produce fixed local paths with encoded strings and validated nonnegative safe-integer idx. selectionHTML/evidenceHTML/capabilityReportHTML call existing delegated inspectors; skillTraceHTML/run steps use original idx. |
| states | Recommended-only / adopted-unexecuted / actual steps / failed or unknown evidence remain distinct. Native details progressively reveal actual matched steps, not fabricated contribution; absent run uses /runs and no last_run inference. |
| data_effects | Historical run/staged.skill_versions and recorded artifacts/checks are authoritative for the trace. No fetch occurs when simply expanding native details; explicit report action rehashes evidence through existing read-only endpoint. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Actual selection render callers: homepage #show-routing, /chat result, /runs#mission latest-body, /dashboard#demo laboratory-live. Static experiment summaries do not gain an invented execution trace. graph/run links preserve context; direct /run step focus belongs to that document. |

## BP-003 Spherical catalogue renderer

Implementation: web/assets/sphere.js: SkillSphere.create

Current contract: Render every catalogue node on a unit sphere with depth picking, drag/click separation, pause and reduced motion; frame budget still requires measurement.

**Change locations:** web/assets/sphere.js: SkillSphere.create

| Contract dimension | Target |
|---|---|
| responsibility | Render every catalogue node on a unit sphere with depth picking, drag/click separation, pause and reduced motion; frame budget still requires measurement. |
| interface | Preserve the existing route, DOM IDs and public callbacks at SkillSphere.create; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-004 Seven-phase executive presentation

Implementation: web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep

Current contract: One reducer owns live and recorded phase state; duplicate events and stale preview/load results are ignored; state contracts are not rewards. Homepage sphere graph link retains current run; terminal step previews may append Product.stepReviewHTML. Seven existing stages/replay remain authoritative; unfinished replay does not expose terminal outcome checks as already executed.

**Change locations:** web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep

| Contract dimension | Target |
|---|---|
| responsibility | One reducer owns live and recorded phase state; duplicate events and stale preview/load results are ignored; state contracts are not rewards. |
| interface | Preserve the existing route, DOM IDs and public callbacks at createState / reduceEvent / phaseFacts / replay controls / inspectStep; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. Preserve Product graphURL/runURL and run-bound terminal step evidence; do not replace the original seven-stage play/pause/seek/presentation flow. |

## BP-005 Briefing layout, explanatory chapters and status

Implementation: web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6

Current contract: Continuous original background and chapters preserved. Actual scroll, zoom, contrast and responsive hierarchy not yet observed.

**Change locations:** web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6

| Contract dimension | Target |
|---|---|
| responsibility | Continuous original background and chapters preserved. Actual scroll, zoom, contrast and responsive hierarchy not yet observed. |
| interface | Preserve the existing route, DOM IDs and public callbacks at top / s1 / s2 / sproduct / s4 / s5 / s6; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-006 Briefing question/workspace/history

Implementation: web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent

Current contract: One question creates a run; histories retain run IDs and plain questions; demo and injected scenario chips retain separate handler ownership.

**Change locations:** web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent

| Contract dimension | Target |
|---|---|
| responsibility | One question creates a run; histories retain run IDs and plain questions; demo and injected scenario chips retain separate handler ownership. |
| interface | Preserve the existing route, DOM IDs and public callbacks at task / run / wsRenderList / wsLoad / handleRunEvent; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-007 Legacy skill/artifact dialog

Implementation: web/briefing.html: openLayer / closeLayer / previewArtifact / viewSkillRaw / renderArtifacts

Current contract: Native modal owns focus. Opening or closing a new preview invalidates old requests; dynamic names use escaped data attributes, not inline JavaScript.

**Change locations:** web/briefing.html: openLayer / closeLayer / previewArtifact / viewSkillRaw / renderArtifacts

| Contract dimension | Target |
|---|---|
| responsibility | Native modal owns focus. Opening or closing a new preview invalidates old requests; dynamic names use escaped data attributes, not inline JavaScript. |
| interface | Preserve the existing route, DOM IDs and public callbacks at openLayer / closeLayer / previewArtifact / viewSkillRaw / renderArtifacts; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-008 Conversation workspace

Implementation: web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML

Current contract: Session/turn ownership guards history hydration; SSE interruption falls back to run records; live models reset per run and admission blocks retain zero attempts.

**Change locations:** web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML

| Contract dimension | Target |
|---|---|
| responsibility | Session/turn ownership guards history hydration; SSE interruption falls back to run records; live models reset per run and admission blocks retain zero attempts. |
| interface | Preserve the existing route, DOM IDs and public callbacks at renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-009 Run-centre navigation, health and mission

Implementation: web/app.html: show / startRun / loadLatest / health / v-intro

Current contract: Hash navigation and confirmed run creation survive unavailable local storage. Current deployment is distinguished from production acceptance.

**Change locations:** web/app.html: show / startRun / loadLatest / health / v-intro

| Contract dimension | Target |
|---|---|
| responsibility | Hash navigation and confirmed run creation survive unavailable local storage. Current deployment is distinguished from production acceptance. |
| interface | Preserve the existing route, DOM IDs and public callbacks at show / startRun / loadLatest / health / v-intro; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-010 Paginated run catalogue

Implementation: web/app.html: loadRuns / run-query / run-status / run-prev / run-next

Current contract: Latest-generation query owns the displayed page; errors and pagination preserve coherent query state.

**Change locations:** web/app.html: loadRuns / run-query / run-status / run-prev / run-next

| Contract dimension | Target |
|---|---|
| responsibility | Latest-generation query owns the displayed page; errors and pagination preserve coherent query state. |
| interface | Preserve the existing route, DOM IDs and public callbacks at loadRuns / run-query / run-status / run-prev / run-next; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-011 Paginated skill catalogue

Implementation: web/app.html: loadSkills / q / skill-domain / skill-source / skills-body

Current contract: Result and metadata awaits both respect query generation; optional metadata errors do not erase a valid result page.

**Change locations:** web/app.html: loadSkills / q / skill-domain / skill-source / skills-body

| Contract dimension | Target |
|---|---|
| responsibility | Result and metadata awaits both respect query generation; optional metadata errors do not erase a valid result page. |
| interface | Preserve the existing route, DOM IDs and public callbacks at loadSkills / q / skill-domain / skill-source / skills-body; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-012 Experiment reports

Implementation: web/app.html: loadEval / v-eval

Current contract: Read real recorded comparison evidence, not assumed skill superiority.

**Change locations:** web/app.html: loadEval / v-eval

| Contract dimension | Target |
|---|---|
| responsibility | Read real recorded comparison evidence, not assumed skill superiority. |
| interface | Preserve the existing route, DOM IDs and public callbacks at loadEval / v-eval; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-013 Runtime/S1 deployment information

Implementation: web/app.html: loadSystem / v-system

Current contract: State actual thread/queue and host/Docker configuration, separating available implementation from production/S1 acceptance.

**Change locations:** web/app.html: loadSystem / v-system

| Contract dimension | Target |
|---|---|
| responsibility | State actual thread/queue and host/Docker configuration, separating available implementation from production/S1 acceptance. |
| interface | Preserve the existing route, DOM IDs and public callbacks at loadSystem / v-system; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-014 Run timeline and inspector

Implementation: web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof

Current contract: Run identity is explicit, including unavailable-storage empty state; proof/error text escaped; aborted admission is not a generated-code success. Initial /run?id=&step= selection validates an original RUN.steps idx, reports invalid/missing step and falls back to the first actual step; subsequent refresh preserves user selection.

**Change locations:** web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof

| Contract dimension | Target |
|---|---|
| responsibility | Run identity is explicit, including unavailable-storage empty state; proof/error text escaped; aborted admission is not a generated-code success. |
| interface | Preserve the existing route, DOM IDs and public callbacks at RUN_ID / subscribe / DAG / inspector / timeline / run-proof; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. Verify direct step=2 and invalid/missing idx links; zero-based idx is never treated as a row offset, and refresh does not reset later user selection. |

## BP-015 Spherical catalogue explorer

Implementation: web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls

Current contract: GraphExplorer separates current typed catalogue relationships from historical run adoption. It renders directed relation groups under active filters, maintains a back stack, and uses original step idx for a task overlay with real inputs/artifacts/checks and explicit manual/missing-skill cases.

**Change locations:** web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls, web/assets/graph-sphere.js: relationRows/history/taskView/taskDetailHTML/renderRelations/setStep, web/graph.html: graph-step / graph-task-detail / graph-back / graph-card-context, tools/graph_explorer_check.js

| Contract dimension | Target |
|---|---|
| responsibility | Search and related nodes expose the full sphere; selected detail requests are generation-owned; pause and focus status synchronize with keyboard behavior. |
| interface | GraphExplorer.relationRows/nodeVisible/history/taskView/taskDetailHTML pure helpers support graph-sphere controller. #graph-step and data-graph-step choose all or step:<original idx>; #graph-back returns prior selected skill; cRel groups depend_on outgoing/incoming, compose_with and similar_to. |
| states | All/one real step, manual unbound step, absent historical node, filter-hidden selected node, visible/no-visible/no-registered relations, first/back navigation, declaration loading/failed/stale/closed are separate; missing history does not fabricate current nodes. |
| data_effects | Current /api/graph supplies nodes and typed edges; /api/runs/:id supplies recorded adoption/input/outputs/checks. Task key changes only step query, retaining run; declaration requests have AbortController plus selection generation, close/pagehide invalidates replies. |
| semantics_accessibility | Use labelled native select/details, typed relation buttons, named back/close, selected title focus and retained input fallback. Controlled-DOM tests verify handlers; native focus/scroll/zoom/screen-reader checks remain separately blocked. |
| styling_layout | Keep sphere scale/rotation/zoom/labels/reset and coherent dark panels. Step detail and relation groups wrap long names and scroll internally within desktop/mobile available area; current v10 native proof must be recorded separately. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape current declarations and historical file/check strings. Artifact requests bind recorded name/source run/SHA; current graph relationship declarations never prove historical runtime dependencies, behavioral equivalence or causal effects. |
| observability | Show manual/unbound, absent historical skill and filter-hidden counts honestly; missing checks/conditions say unknown. Current relationship groups and historical adoption overlay have explicit provenance/boundaries. |
| integration | graph?run=&skill=&domain=&step= retains original run/step across relation/back operations. Product artifact/step/report reads remain explicit; returning /run uses runURL step context. One native graph scene owns renderer lifecycle, existing controls preserved. |

## BP-016 Developer dashboard navigation/meta

Implementation: web/index.html: tabs / metabar / show

Current contract: Seven hash views preserve their data and entry routes; browser history remains a runtime check.

**Change locations:** web/index.html: tabs / metabar / show

| Contract dimension | Target |
|---|---|
| responsibility | Seven hash views preserve their data and entry routes; browser history remains a runtime check. |
| interface | Preserve the existing route, DOM IDs and public callbacks at tabs / metabar / show; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-017 Developer overview

Implementation: web/index.html: renderOverview / graph / domains / quality / pipeline / refs

Current contract: Render real fixture inventory and reference metadata with escaped text; shape and compact layouts still need browser checks.

**Change locations:** web/index.html: renderOverview / graph / domains / quality / pipeline / refs

| Contract dimension | Target |
|---|---|
| responsibility | Render real fixture inventory and reference metadata with escaped text; shape and compact layouts still need browser checks. |
| interface | Preserve the existing route, DOM IDs and public callbacks at renderOverview / graph / domains / quality / pipeline / refs; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-018 Plan contrast demonstration

Implementation: web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions

Current contract: Model reference scores are finite/valid or unavailable. A displayed plan is not a real execution or causal proof.

**Change locations:** web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions

| Contract dimension | Target |
|---|---|
| responsibility | Model reference scores are finite/valid or unavailable. A displayed plan is not a real execution or causal proof. |
| interface | Preserve the existing route, DOM IDs and public callbacks at doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-019 Developer skill inspector

Implementation: web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next

Current contract: Inspect catalogue contracts, source, versions and boundaries; raw remote instructions remain untrusted data.

**Change locations:** web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next

| Contract dimension | Target |
|---|---|
| responsibility | Inspect catalogue contracts, source, versions and boundaries; raw remote instructions remain untrusted data. |
| interface | Preserve the existing route, DOM IDs and public callbacks at loadCatalog / skillList / skillDetail / catalog-prev / catalog-next; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-020 Retrieval/routing laboratory

Implementation: web/index.html: doSearch / doRoute / searchOut / routeOut

Current contract: Query/routing methods expose candidates and metadata; relevance and ordering values are not success probabilities.

**Change locations:** web/index.html: doSearch / doRoute / searchOut / routeOut

| Contract dimension | Target |
|---|---|
| responsibility | Query/routing methods expose candidates and metadata; relevance and ordering values are not success probabilities. |
| interface | Preserve the existing route, DOM IDs and public callbacks at doSearch / doRoute / searchOut / routeOut; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-021 Execution and real-run controls

Implementation: web/index.html: doRun / runMode / realRunBtn / runOut

Current contract: Distinguish planned comparison and created real execution; reference scores unavailable rather than zero when invalid.

**Change locations:** web/index.html: doRun / runMode / realRunBtn / runOut

| Contract dimension | Target |
|---|---|
| responsibility | Distinguish planned comparison and created real execution; reference scores unavailable rather than zero when invalid. |
| interface | Preserve the existing route, DOM IDs and public callbacks at doRun / runMode / realRunBtn / runOut; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-022 Developer result archive

Implementation: web/index.html: resultsOut / renderResults

Current contract: Historical reports retain their recorded scope and cannot retroactively prove improvement.

**Change locations:** web/index.html: resultsOut / renderResults

| Contract dimension | Target |
|---|---|
| responsibility | Historical reports retain their recorded scope and cannot retroactively prove improvement. |
| interface | Preserve the existing route, DOM IDs and public callbacks at resultsOut / renderResults; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-023 S1/export laboratory

Implementation: web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live

Current contract: Current service contracts are visible; real S1 attachment and production acceptance require independent integration evidence.

**Change locations:** web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live

| Contract dimension | Target |
|---|---|
| responsibility | Current service contracts are visible; real S1 attachment and production acceptance require independent integration evidence. |
| interface | Preserve the existing route, DOM IDs and public callbacks at adapterBtn / adapterOut / s1-contract / laboratory-live; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-024 Product resource manifest controller

Implementation: web/assets/product.js: inspectResources / beginPanel / #resources-dialog

Current contract: Shared resource manifest owned by inspectResources and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

**Change locations:** web/assets/product.js: inspectResources / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-skill-resources] → inspectResources → dialog #resources-dialog; keep current run/skill/file identity. |
| states | manifest loading/ready/error/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-025 Product verified resource file controller

Implementation: web/assets/product.js: readResource / beginPanel / #resource-file-dialog

Current contract: Shared verified resource file owned by readResource and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

**Change locations:** web/assets/product.js: readResource / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-resource-read] → readResource → dialog #resource-file-dialog; keep current run/skill/file identity. |
| states | digest verifying/mismatch/oversized/text/binary/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-026 Product evidence export controller

Implementation: web/assets/product.js: handoff / beginPanel / #evidence-dialog

Current contract: Shared evidence export owned by handoff and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

**Change locations:** web/assets/product.js: handoff / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-evidence-export] → handoff → dialog #evidence-dialog; keep current run/skill/file identity. |
| states | evidence loading/ready/download/error/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-027 Product run value controller

Implementation: web/assets/product.js: inspectValue / beginPanel / #value-dialog

Current contract: Shared run value owned by inspectValue and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

**Change locations:** web/assets/product.js: inspectValue / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-run-value] → inspectValue → dialog #value-dialog; keep current run/skill/file identity. |
| states | run loading/value ready/error/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-028 Product capability report controller

Implementation: web/assets/product.js: inspectCapabilities / beginPanel / #capabilities-dialog

Current contract: Shared capability report owned by inspectCapabilities and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

**Change locations:** web/assets/product.js: inspectCapabilities / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-capability-report] → inspectCapabilities → dialog #capabilities-dialog; keep current run/skill/file identity. |
| states | report loading/unknown/failed/ready/download/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-029 Product skill passport controller

Implementation: web/assets/product.js: inspectPassport / beginPanel / #passport-dialog

Current contract: inspectPassport concurrently reads current skill declaration and optional explicitly associated historical run with Promise.allSettled. One epoch owns both replies; partial failures remain visible, returned run id must match requested id, and current declaration SHA cannot replace staged historical SHA.

**Change locations:** web/assets/product.js: inspectPassport / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated data-capability-skill plus optional data-run/data-step/data-domain opens #passport-dialog. skillTraceHTML lists matched actual steps; graphURL/runURL preserve original run/step/domain. |
| states | Current declaration only; declaration+history; current declaration unavailable but history retained; history unavailable/mismatched but declaration retained; both failed; closed/stale/pagehide. Partial data never certifies the unavailable side. |
| data_effects | Read-only skill and run APIs run concurrently. Render only when latest dialog epoch is still open. Strict returned run identity prevents merging wrong historical evidence; opening current declaration without context has no fabricated steps. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Separate current SHA, historical SHA/unrecorded, actual artifacts and missing independent checks; error messages identify which evidence could not be read. |
| integration | Instances in hero/selection/graph step contexts retain their own parent/focus constraints. On same /run id, step action dismisses covering passport/capabilities before native inspector focus; on another id, independent dialog fetch remains run-scoped. |

## BP-030 Product step details controller

Implementation: web/assets/product.js: focusStep / beginPanel / #kernel-step-dialog

Current contract: focusStep validates original idx/run. Matching explicit /run?id context dispatches existing kernel-step-focus; another run fetches its own isolated step dialog. stepReviewHTML shows recorded checks, historical version, contract/code/repairs/artifacts and scope boundary.

**Change locations:** web/assets/product.js: focusStep / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | data-kernel-step stores original nonnegative safe-integer idx and data-run exact run identity; matching /run dispatches CustomEvent kernel-step-focus({idx}); other pages use #kernel-step-dialog. runURL step deep-link is consumed by run.html refresh once. |
| states | Valid step, absent/missing idx, invalid idx rejected before request, same-run inspector focus, other-run independent dialog, stale/closed/error; manual action does not acquire a fake skill passport. |
| data_effects | Use actual run.steps matching original idx; do not locate by array offset or same idx in unrelated run. Request epoch continues to guard success/failure; details expansion is local/read-only. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Reuse run.html inspector and existing Product dialog flow. Close covering passport/capabilities only before same-run local focus; keep contract/code/repair/resources/artifact behavior intact. Initial deep-link applies once, later refresh cannot override user selection. |

## BP-031 Product artifact preview controller

Implementation: web/assets/product.js: preview / beginPanel / #product-preview

Current contract: Shared artifact preview owned by preview and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

**Change locations:** web/assets/product.js: preview / beginPanel

| Contract dimension | Target |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-artifact-preview] → preview → dialog #product-preview; keep current run/skill/file identity. |
| states | run/file loading/text/image/pdf/unknown/large/error/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-032 Finite capability frontier experiment surface

Implementation: web/assets/frontier.js: boot/open/request/runScenario/renderLab/renderRun/close; web/assets/frontier.css

Current contract: frontier.js owns one modal/trigger, per-request generation and AbortControllers, public named scenario POST, scoped report renderers and evidence read. frontier.css supplies the independent visual surface; Product snapshot opens through data-frontier-open.

**Change locations:** web/assets/frontier.js, web/assets/frontier.css, tools/frontier_ui_check.js, six HTML shared asset inclusions

| Contract dimension | Target |
|---|---|
| responsibility | Explain finite experimental diagnosis, actual operator transitions and independent oracle; never certify all skills or change production policies. |
| interface | boot creates #frontier-launch/#frontier-dialog; delegated [data-frontier-open] opens read-only; UI.json calls only fixed /api/frontier endpoints; POST body only scenario_id. |
| states | Closed → independent lab/scenario loading → readable or retryable read errors; POST disables controls then restores result/error; close/pagehide invalidates request ownership; no automatic POST retry. |
| data_effects | Server public reports are authoritative. Generation plus per-kind sequence suppresses stale success/errors; 45s client timeout aborts waiting, not server execution. Evidence read uses fixed same-origin path and Blob URL cleanup. |
| semantics_accessibility | Native dialog with labelled title/description, labelled select, named buttons, details/summary, role=status and role=alert; initial/trapped/return focus and conditional lost-focus recovery need native and assistive revalidation. |
| styling_layout | Scope all styles to frontier classes; important auto dialog margin resists global reset; direct-child footer specificity resists page footer rules; 390px single-column controls/cards preserve background and internal scroll. |
| performance_lifecycle | Use lightweight verified /lab projection; full trace read only on explicit evidence action; bounded display arrays/raw preview and 45s timers; clear pending requests/timers on close/pagehide. Measure real long-session memory/layout performance separately. |
| security_privacy | No arbitrary code, paths or model keys submitted; unsafe content uses textContent, evidence_url fixed; UI.json supplies configured access token. Backend scenario whitelist, concurrency and S1 signature/nonce enforce trust; production tenant acceptance remains separate. |
| observability | Show read/execution failures without claiming success; distinguish source report digest from projection digest, declare scope and unknowns, retain actual process calls and independent result counts. |
| integration | Six HTML imports yield sixteen registered parent contexts; hash navigation must not duplicate triggers or remove original pages. Actual user research bridge stays read-only and opens this separate experimental surface explicitly. |

## BP-033 Hero catalogue exploration below the sphere

Implementation: web/assets/hero-explorer.js: catalogue/mount/select/setDomain/loadDetails/search/suspend/destroy; web/assets/hero-explorer.css; web/briefing.html hero-explorer integration

Current contract: HeroExplorer mounts below the existing hero sphere; one controller owns domain legend, searchable catalogue results, selected declaration card, retries and safe graph links. The same host is suspended during DAG presentation; sphere/background/seven-phase ownership stays with the original controllers.

**Change locations:** web/assets/hero-explorer.js, web/assets/hero-explorer.css, web/briefing.html: hero-explorer / HeroExplorer.mount / showNetDag / resetHeroNetwork, tools/hero_explorer_check.js

| Contract dimension | Target |
|---|---|
| responsibility | Let a viewer locate a real catalogue skill and inspect its declared purpose/source/typed relation counts; no execution certification, invented nodes or new reward. |
| interface | HeroExplorer.mount({host,sphere,canvas,graphLink,reload,request?}) returns select/setData/failed/suspend/destroy/snapshot. Domain chips and #hero-skill-search select existing id; passport delegates data-capability-skill; graph links encode skill/domain. |
| states | Catalogue loading/ready/empty/failed/retrying; domain/all scope; collapsed/expanded search with empty/matches/no-match; selected purpose loading/ready/error/timeout/retry/closed; DAG suspension prevents hidden selection and later resumes current filter. |
| data_effects | Catalogue response is the authority for exact ids/domains/edges. One selected skill owns generation, AbortController and 12-second timer; close/change/pagehide/destroy invalidates stale completions; reply skill/passport identity must match. Purpose requests are read-only. |
| semantics_accessibility | Native details/summary, labelled search, buttons and links; status messages show catalogue/result/purpose state; ArrowDown/Enter/Escape paths, close fallback and title focus are controlled-DOM checked. Native keyboard/focus and assistive technologies still require explicit browser evidence. |
| styling_layout | Scoped html[data-product=briefing] .hero-explorer rules preserve dark sea/hero style, wrap long names, collapse cards/controls at 390px and leave the original globe visible. Decorative wrappers/domain dots belong to responsible parent layout; do not claim measured contrast/zoom or actual OS reduced-motion. |
| performance_lifecycle | Search returns at most 8 visible rows while reporting full matches; top 4 nonempty domain chips plus all scope do not restrict search coverage. Clear timers/listeners and abort on teardown; suspend around DAG without creating another sphere. Real frame/memory budgets remain unmeasured. |
| security_privacy | Dynamic names/purpose/errors use textContent; fixed same-origin skill endpoint and URLSearchParams keep untrusted ids inside query/path segments. UI.json supplies existing session access policy; source popularity/relationships never certify imported code. |
| observability | Expose exact catalogue count/current domain/result count and actionable read/retry states, distinguish current declaration from executable evidence; never expose credentials in a card or URL. |
| integration | Register each meaningful control child under the hero explorer. Preserve hero rotation, original full-graph link, graph detail routes and Product passport; suspend/resume follows existing sphere-to-DAG lifecycle, not a replacement seven-stage flow. |
