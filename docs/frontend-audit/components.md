# 组件契约与处置

每个 DEF 对应实际实现，所有 CMP 的处置、独有路由条件、验收和关联任务位于 audit.json/component_plans 与逐页报告。investigate 表示该实例运行证据待补，不能当作实现不合格。

## BP-001 Shared navigation/connection settings/toasts

web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions

Token validation commits only the current validated candidate; session cache is plain data. Native dialog focus remains a browser acceptance item.

| 维度 | 目标契约 |
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

web/assets/product.js: Product.evidenceHTML / dagHTML / preview / delegated inspectors

Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task.

| 维度 | 目标契约 |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Preserve the existing route, DOM IDs and public callbacks at Product.evidenceHTML / dagHTML / preview / delegated inspectors; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-003 Spherical catalogue renderer

web/assets/sphere.js: SkillSphere.create

Render every catalogue node on a unit sphere with depth picking, drag/click separation, pause and reduced motion; frame budget still requires measurement.

| 维度 | 目标契约 |
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

web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep

One reducer owns live and recorded phase state; duplicate events and stale preview/load results are ignored; state contracts are not rewards.

| 维度 | 目标契约 |
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
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-005 Briefing layout, explanatory chapters and status

web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6

Continuous original background and chapters preserved. Actual scroll, zoom, contrast and responsive hierarchy not yet observed.

| 维度 | 目标契约 |
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

web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent

One question creates a run; histories retain run IDs and plain questions; demo and injected scenario chips retain separate handler ownership.

| 维度 | 目标契约 |
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

web/briefing.html: openLayer / closeLayer / previewArtifact / viewSkillRaw / renderArtifacts

Native modal owns focus. Opening or closing a new preview invalidates old requests; dynamic names use escaped data attributes, not inline JavaScript.

| 维度 | 目标契约 |
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

web/chat.html: renderSidebar / renderMain / submitQ / stream / hydrateTurn / resultHTML

Session/turn ownership guards history hydration; SSE interruption falls back to run records; live models reset per run and admission blocks retain zero attempts.

| 维度 | 目标契约 |
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

web/app.html: show / startRun / loadLatest / health / v-intro

Hash navigation and confirmed run creation survive unavailable local storage. Current deployment is distinguished from production acceptance.

| 维度 | 目标契约 |
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

web/app.html: loadRuns / run-query / run-status / run-prev / run-next

Latest-generation query owns the displayed page; errors and pagination preserve coherent query state.

| 维度 | 目标契约 |
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

web/app.html: loadSkills / q / skill-domain / skill-source / skills-body

Result and metadata awaits both respect query generation; optional metadata errors do not erase a valid result page.

| 维度 | 目标契约 |
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

web/app.html: loadEval / v-eval

Read real recorded comparison evidence, not assumed skill superiority.

| 维度 | 目标契约 |
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

web/app.html: loadSystem / v-system

State actual thread/queue and host/Docker configuration, separating available implementation from production/S1 acceptance.

| 维度 | 目标契约 |
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

web/run.html: RUN_ID / subscribe / DAG / inspector / timeline / run-proof

Run identity is explicit, including unavailable-storage empty state; proof/error text escaped; aborted admission is not a generated-code success.

| 维度 | 目标契约 |
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
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-015 Spherical catalogue explorer

web/assets/graph-sphere.js: selectNode / closeCard / refresh / applyTask / graph controls

Search and related nodes expose the full sphere; selected detail requests are generation-owned; pause and focus status synchronize with keyboard behavior.

| 维度 | 目标契约 |
|---|---|
| responsibility | Search and related nodes expose the full sphere; selected detail requests are generation-owned; pause and focus status synchronize with keyboard behavior. |
| interface | Preserve the existing route, DOM IDs and public callbacks at selectNode / closeCard / refresh / applyTask / graph controls; verify the actual integration at each registered instance. |
| states | Retain normal, empty, loading, error, interrupted and unknown branches where supported; no unobserved branch is marked passing. |
| data_effects | Use authoritative run/catalogue APIs; identify request/session ownership; cancel or ignore stale completions. Pure explanatory text has no request side effects. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape untrusted names, filenames, errors and markdown. Credentials remain per-session; front-end controls do not replace server authorization. S1 tenant boundaries require backend acceptance. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-016 Developer dashboard navigation/meta

web/index.html: tabs / metabar / show

Seven hash views preserve their data and entry routes; browser history remains a runtime check.

| 维度 | 目标契约 |
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

web/index.html: renderOverview / graph / domains / quality / pipeline / refs

Render real fixture inventory and reference metadata with escaped text; shape and compact layouts still need browser checks.

| 维度 | 目标契约 |
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

web/index.html: doDemo / doLegacyDemo / demoOut / judgeScore / judgeDimensions

Model reference scores are finite/valid or unavailable. A displayed plan is not a real execution or causal proof.

| 维度 | 目标契约 |
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

web/index.html: loadCatalog / skillList / skillDetail / catalog-prev / catalog-next

Inspect catalogue contracts, source, versions and boundaries; raw remote instructions remain untrusted data.

| 维度 | 目标契约 |
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

web/index.html: doSearch / doRoute / searchOut / routeOut

Query/routing methods expose candidates and metadata; relevance and ordering values are not success probabilities.

| 维度 | 目标契约 |
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

web/index.html: doRun / runMode / realRunBtn / runOut

Distinguish planned comparison and created real execution; reference scores unavailable rather than zero when invalid.

| 维度 | 目标契约 |
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

web/index.html: resultsOut / renderResults

Historical reports retain their recorded scope and cannot retroactively prove improvement.

| 维度 | 目标契约 |
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

web/index.html: adapterBtn / adapterOut / s1-contract / laboratory-live

Current service contracts are visible; real S1 attachment and production acceptance require independent integration evidence.

| 维度 | 目标契约 |
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

web/assets/product.js: inspectResources / beginPanel / #resources-dialog

Shared resource manifest owned by inspectResources and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
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

web/assets/product.js: readResource / beginPanel / #resource-file-dialog

Shared verified resource file owned by readResource and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
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

web/assets/product.js: handoff / beginPanel / #evidence-dialog

Shared evidence export owned by handoff and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
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

web/assets/product.js: inspectValue / beginPanel / #value-dialog

Shared run value owned by inspectValue and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
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

web/assets/product.js: inspectCapabilities / beginPanel / #capabilities-dialog

Shared capability report owned by inspectCapabilities and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
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

web/assets/product.js: inspectPassport / beginPanel / #passport-dialog

Shared skill passport owned by inspectPassport and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-capability-skill] → inspectPassport → dialog #passport-dialog; keep current run/skill/file identity. |
| states | declaration loading/ready/unknown/error/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-030 Product step details controller

web/assets/product.js: focusStep / beginPanel / #kernel-step-dialog

Shared step details owned by focusStep and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
|---|---|
| responsibility | Run-scoped results distinguish declared, observed, unknown and rewarded. Core evidence and dialog generation are maintained by the parent task. |
| interface | Delegated [data-kernel-step] → focusStep → dialog #kernel-step-dialog; keep current run/skill/file identity. |
| states | step loading/missing/ready/error/closed; latest request alone can render success/failure; closing never resurrects an old response. |
| data_effects | Controlled DOM tests verify ownership and bounded reads. Do not equate a simulated handler call with native browser focus/layout; actual browser scenario remains blocked. |
| semantics_accessibility | Native controls have names and keyboard activation; focus returns predictably after dialogs/panels. Canvas has equivalent searchable catalogue access. Browser/screen-reader verification pending. |
| styling_layout | Preserve existing background, typography, sphere and seven phases. Verify 390×844, 1440×900, 200% zoom and long names/content before visual acceptance. |
| performance_lifecycle | Sphere logic checks hidden/offscreen cleanup. Measure frame time, memory, requests and layout shifts in an actual browser before adopting a performance budget. |
| security_privacy | Escape hostile markup/numeric fields. Resource content is reference data; digest mismatch/409/size limits prevent a verified download. Authorization stays server-side. |
| observability | Show actionable errors and unknown states, distinguish declaration/observation/reward, retain run links without exposing token values. |
| integration | Preserve six-document navigation, real run IDs, shared Product renderers and parent-owned state/evidence APIs; final commit regression still required. |

## BP-031 Product artifact preview controller

web/assets/product.js: preview / beginPanel / #product-preview

Shared artifact preview owned by preview and beginPanel; each open has a request epoch invalidated on close/cancel/pagehide.

| 维度 | 目标契约 |
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
