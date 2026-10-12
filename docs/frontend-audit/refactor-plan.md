# Implementation and verification plan

verified applies only to evidence and scenarios listed in that task. implemented records a source change awaiting recheck. blocked means the listed acceptance evidence is incomplete. Controlled logic, finite native subsets, complete parent journeys and production gates are tracked separately.

| Task | Phase | Status | Scope | Owner | Verification |
|---|---|---|---|---|---|
| TASK-001 Executive briefing runtime/visual acceptance | 2 | blocked | PAGE-001, CMP-001, CMP-002, CMP-003, CMP-004, CMP-005, CMP-006, CMP-007, CMP-008, CMP-009, CMP-010, CMP-011, CMP-012, CMP-013, CMP-014, CMP-015, CMP-016, CMP-017, CMP-018, CMP-019, CMP-020, CMP-021, CMP-022, CMP-023, CMP-024, CMP-025, CMP-026, CMP-027, CMP-028, CMP-029, CMP-030, CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160, CMP-177, CMP-178, CMP-179, CMP-180, CMP-181, CMP-182, CMP-183, CMP-184, CMP-185, CMP-186, CMP-187, CMP-188, CMP-189, CMP-190, CMP-202, CMP-203, CMP-204, CMP-205, CMP-206 | frontend QA with runtime/browser access | SCN-001 |
| TASK-002 Conversation runtime/visual acceptance | 2 | blocked | PAGE-002, CMP-031, CMP-032, CMP-033, CMP-034, CMP-035, CMP-036, CMP-037, CMP-038, CMP-039, CMP-040, CMP-041, CMP-042, CMP-043, CMP-044, CMP-045, CMP-046, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211 | frontend QA with runtime/browser access | SCN-002 |
| TASK-003 Mission centre runtime/visual acceptance | 2 | blocked | PAGE-003, CMP-047, CMP-048, CMP-049, CMP-050, CMP-051, CMP-052, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216 | frontend QA with runtime/browser access | SCN-003 |
| TASK-004 Run catalogue runtime/visual acceptance | 2 | blocked | PAGE-004, CMP-053, CMP-054, CMP-055, CMP-056, CMP-057, CMP-058, CMP-059, CMP-060 | frontend QA with runtime/browser access | SCN-004 |
| TASK-005 Skill catalogue runtime/visual acceptance | 2 | blocked | PAGE-005, CMP-061, CMP-062, CMP-063, CMP-064, CMP-065, CMP-066, CMP-067 | frontend QA with runtime/browser access | SCN-005 |
| TASK-006 Evaluation reports runtime/visual acceptance | 2 | blocked | PAGE-006, CMP-068, CMP-069, CMP-070 | frontend QA with runtime/browser access | SCN-006 |
| TASK-007 Deployment information runtime/visual acceptance | 2 | blocked | PAGE-007, CMP-071, CMP-072, CMP-073, CMP-074 | frontend QA with runtime/browser access | SCN-007 |
| TASK-008 Run detail runtime/visual acceptance | 2 | blocked | PAGE-008, CMP-075, CMP-076, CMP-077, CMP-078, CMP-079, CMP-080, CMP-081, CMP-082, CMP-083, CMP-084, CMP-085, CMP-086, CMP-087, CMP-088, CMP-089 | frontend QA with runtime/browser access | SCN-008 |
| TASK-009 Spherical skill network runtime/visual acceptance | 2 | blocked | PAGE-009, CMP-090, CMP-091, CMP-092, CMP-093, CMP-094, CMP-095, CMP-096, CMP-097, CMP-098, CMP-099, CMP-100, CMP-101, CMP-102, CMP-103, CMP-104, CMP-105, CMP-106, CMP-107, CMP-108, CMP-109, CMP-110, CMP-191, CMP-192, CMP-193, CMP-194, CMP-195, CMP-196, CMP-197, CMP-198, CMP-199, CMP-200, CMP-201 | frontend QA with runtime/browser access | SCN-009 |
| TASK-010 Developer overview runtime/visual acceptance | 2 | blocked | PAGE-010, CMP-111, CMP-112, CMP-113, CMP-114, CMP-115 | frontend QA with runtime/browser access | SCN-010 |
| TASK-011 Plan contrast runtime/visual acceptance | 2 | blocked | PAGE-011, CMP-116, CMP-117, CMP-118, CMP-119, CMP-120, CMP-121, CMP-122, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221 | frontend QA with runtime/browser access | SCN-011 |
| TASK-012 Developer skill inspector runtime/visual acceptance | 2 | blocked | PAGE-012, CMP-123, CMP-124, CMP-125, CMP-126, CMP-127, CMP-128, CMP-129 | frontend QA with runtime/browser access | SCN-012 |
| TASK-013 Retrieval/routing laboratory runtime/visual acceptance | 2 | blocked | PAGE-013, CMP-130, CMP-131, CMP-132, CMP-133, CMP-134, CMP-135, CMP-136 | frontend QA with runtime/browser access | SCN-013 |
| TASK-014 Execution laboratory runtime/visual acceptance | 2 | blocked | PAGE-014, CMP-137, CMP-138, CMP-139, CMP-140, CMP-141, CMP-142, CMP-143 | frontend QA with runtime/browser access | SCN-014 |
| TASK-015 Historical results runtime/visual acceptance | 2 | blocked | PAGE-015, CMP-144, CMP-145, CMP-146 | frontend QA with runtime/browser access | SCN-015 |
| TASK-016 S1/export laboratory runtime/visual acceptance | 2 | blocked | PAGE-016, CMP-147, CMP-148, CMP-149, CMP-150, CMP-151, CMP-152 | frontend QA with runtime/browser access | SCN-016 |
| TASK-017 Token clear/close race correction and bounded regression | 1 | verified | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148 | frontend implementation | SCN-017 |
| TASK-018 Chained skill metadata overwrites a newer query correction and bounded regression | 1 | verified | CMP-065 | frontend implementation | SCN-018 |
| TASK-019 Confirmed run creation misreported when storage is disabled correction and bounded regression | 1 | verified | CMP-052 | frontend implementation | SCN-019 |
| TASK-020 Run detail crashes before empty-state rendering with storage disabled correction and bounded regression | 1 | verified | CMP-089 | frontend implementation | SCN-020 |
| TASK-021 Stored sessions trust cached rendering and dynamic inline handlers correction and bounded regression | 1 | verified | CMP-019, CMP-038 | frontend implementation | SCN-021 |
| TASK-022 Invalid model score and zero-attempt presentation correction and bounded regression | 1 | verified | CMP-041, CMP-122, CMP-143 | frontend implementation | SCN-022 |
| TASK-023 State contract events need truthful separation from reward correction and bounded regression | 1 | verified | CMP-014 | frontend implementation | SCN-023 |
| TASK-024 Late mission/evaluation/system/health responses overwrite newer state correction and bounded regression | 1 | verified | CMP-051, CMP-070, CMP-073 | frontend implementation | SCN-024 |
| TASK-025 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs browser verification | 2 | implemented | CMP-024 | frontend QA with browser access | SCN-001 |
| TASK-026 Replay load/preview stale failures can overwrite current state browser verification | 2 | implemented | CMP-010, CMP-023 | frontend QA with browser access | SCN-001 |
| TASK-027 Native step controls receive duplicate keyboard activation browser verification | 2 | implemented | CMP-013 | frontend QA with browser access | SCN-001 |
| TASK-028 Sphere keyboard pause/focus state not reflected consistently browser verification | 2 | implemented | CMP-104, CMP-106, CMP-107 | frontend QA with browser access | SCN-009 |
| TASK-029 Global chip binding replaces injected scenario actions browser verification | 2 | implemented | CMP-018 | frontend QA with browser access | SCN-001 |
| TASK-030 Historical growth and S1 deployment labels overstate supported evidence browser verification | 2 | implemented | CMP-026, CMP-030, CMP-074, CMP-122, CMP-149 | frontend QA with browser access | SCN-001, SCN-007, SCN-011, SCN-016 |
| TASK-031 Verify shared Product controller fault corrections | 1 | verified | CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160 | parent frontend implementation and audit verification | SCN-025, SCN-026, SCN-027, SCN-028, SCN-029, SCN-030, SCN-031, SCN-032, SCN-033, SCN-034, SCN-035, SCN-036 |
| TASK-032 Graph search lacked keyboard selection actual browser correction | 1 | verified | CMP-093 | root frontend implementation / IAB QA | SCN-051 |
| TASK-033 Mobile uniqueness cards inherited three inline columns and overflowed actual browser correction | 1 | verified | CMP-026 | root frontend implementation / IAB QA | SCN-049 |
| TASK-034 Final local deliverable count correction | 1 | verified | CMP-156 | root frontend implementation and Node verification | SCN-053 |
| TASK-035 Verify shared frontier IIFE fault logic | 1 | verified | DEF-032 | root frontend implementation / IAB QA | SCN-054, SCN-055, SCN-056, SCN-057, SCN-058, SCN-059, SCN-060 |
| TASK-036 Repair and natively recheck v7 frontier modal/footer cascade | 1 | verified | DEF-032, CMP-161 | root frontend implementation / IAB QA | SCN-080, SCN-081 |
| TASK-037 Repair and natively recheck disabled-submit focus | 1 | verified | DEF-032, CMP-161 | root frontend implementation / IAB QA | SCN-060, SCN-082 |
| TASK-038 Complete frontier integration in all sixteen parent views | 2 | blocked | DEF-032, CMP-161, CMP-162, CMP-163, CMP-164, CMP-165, CMP-166, CMP-167, CMP-168, CMP-169, CMP-170, CMP-171, CMP-172, CMP-173, CMP-174, CMP-175, CMP-176 | frontend QA with target browser and S1 environment | SCN-064, SCN-065, SCN-066, SCN-067, SCN-068, SCN-069, SCN-070, SCN-071, SCN-072, SCN-073, SCN-074, SCN-075, SCN-076, SCN-077, SCN-078, SCN-079 |
| TASK-039 Verify bounded exploration/shared-context controller logic | 1 | verified | DEF-033, DEF-015, DEF-002, DEF-029, DEF-030, DEF-004 | frontend implementation and audit verifier | SCN-088, SCN-089, SCN-090, SCN-091, SCN-092, SCN-093, SCN-094, SCN-095 |
| TASK-040 Complete bounded native exploration and actual parent-context acceptance | 2 | blocked | CMP-177, CMP-178, CMP-179, CMP-180, CMP-181, CMP-182, CMP-183, CMP-184, CMP-185, CMP-186, CMP-187, CMP-188, CMP-189, CMP-190, CMP-191, CMP-192, CMP-193, CMP-194, CMP-195, CMP-196, CMP-197, CMP-198, CMP-199, CMP-200, CMP-201, CMP-202, CMP-203, CMP-204, CMP-205, CMP-206, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221, CMP-087, CMP-100, CMP-108, CMP-158, CMP-159 | root native IAB QA and frontend owners | SCN-084, SCN-085, SCN-086, SCN-087 |
| TASK-041 Repair and natively recheck graph task/filter overlap | 1 | verified | DEF-015, CMP-100, CMP-191, CMP-192 | graph frontend implementation / root IAB QA | SCN-096 |

## TASK-001 Executive briefing runtime/visual acceptance

**Change locations:** web/briefing.html, web/assets/showcase.js, web/assets/sphere.js, web/assets/ui.js, web/briefing.html

**Implementation steps:** Execute SCN-001 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on / are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-002

## TASK-002 Conversation runtime/visual acceptance

**Change locations:** web/chat.html, web/chat.html, web/assets/ui.js, web/assets/product.js

**Implementation steps:** Execute SCN-002 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /chat are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-003

## TASK-003 Mission centre runtime/visual acceptance

**Change locations:** web/app.html, web/app.html, web/assets/ui.js, web/assets/product.js

**Implementation steps:** Execute SCN-003 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /runs#mission are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-004

## TASK-004 Run catalogue runtime/visual acceptance

**Change locations:** web/app.html, web/app.html, web/assets/ui.js

**Implementation steps:** Execute SCN-004 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /runs#runs are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-004

## TASK-005 Skill catalogue runtime/visual acceptance

**Change locations:** web/app.html, web/app.html, web/assets/ui.js

**Implementation steps:** Execute SCN-005 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /runs#skills are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-004

## TASK-006 Evaluation reports runtime/visual acceptance

**Change locations:** web/app.html, web/app.html, web/assets/ui.js

**Implementation steps:** Execute SCN-006 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /runs#eval are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-004

## TASK-007 Deployment information runtime/visual acceptance

**Change locations:** web/app.html, web/app.html, web/assets/ui.js

**Implementation steps:** Execute SCN-007 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /runs#system are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-004

## TASK-008 Run detail runtime/visual acceptance

**Change locations:** web/run.html, web/assets/ui.js, web/run.html

**Implementation steps:** Execute SCN-008 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /run?id=<run-id> are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-005

## TASK-009 Spherical skill network runtime/visual acceptance

**Change locations:** web/graph.html, web/assets/graph-sphere.js, web/assets/sphere.js, web/assets/ui.js, web/assets/product.js

**Implementation steps:** Execute SCN-009 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /graph?run=&skill=&domain= are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-006

## TASK-010 Developer overview runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-010 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#overview are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-011 Plan contrast runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-011 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#demo are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-012 Developer skill inspector runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-012 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#skills?skill= are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-013 Retrieval/routing laboratory runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-013 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#search are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-014 Execution laboratory runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-014 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#run are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-015 Historical results runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-015 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#results are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-016 S1/export laboratory runtime/visual acceptance

**Change locations:** web/index.html, web/index.html, web/assets/ui.js

**Implementation steps:** Execute SCN-016 against the final commit; do not substitute Node/source checks for interaction evidence., Fix any reproduced failure at its owning implementation, preserving the original visual/background and core flow., Capture sanitized runtime evidence; update per-instance checks, scenario, source manifest and gates.

**Acceptance criteria:** All controls/conditional templates on /dashboard#adapters are covered with actual browser evidence., No stale data, missing focus, broken scroll/zoom or misleading result labels in the tested conditions.

**Rollback:** Revert only the reproduced UI change; preserve backend data and existing assets. Revalidate the same route and shared call sites.

**Risk:** Runtime/visual/accessibility/performance conclusions are pending until actual execution.

**Evidence ids:** EV-007

## TASK-017 Token clear/close race correction and bounded regression

**Finding ids:** FND-001

**Change locations:** web/assets/ui.js, tools/frontend_resilience_check.js

**Implementation steps:** Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., Run tools/frontend_resilience_check.js: tokenRace and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Token clear/close race passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-018 Chained skill metadata overwrites a newer query correction and bounded regression

**Finding ids:** FND-002

**Change locations:** web/app.html, tools/frontend_resilience_check.js

**Implementation steps:** Guard after each await/catch/finally and keep a successfully loaded page if optional metadata fails., Run tools/frontend_resilience_check.js: skillsRace and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Chained skill metadata overwrites a newer query passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-019 Confirmed run creation misreported when storage is disabled correction and bounded regression

**Finding ids:** FND-003

**Change locations:** web/app.html, tools/frontend_resilience_check.js

**Implementation steps:** Persistence failure cannot change confirmed run identity; redirect using returned ID., Run tools/frontend_resilience_check.js: blockedStorage and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Confirmed run creation misreported when storage is disabled passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-020 Run detail crashes before empty-state rendering with storage disabled correction and bounded regression

**Finding ids:** FND-004

**Change locations:** web/run.html, tools/frontend_resilience_check.js

**Implementation steps:** Guard fallback storage and render the missing-run state normally., Run tools/frontend_resilience_check.js: blockedStorage and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Run detail crashes before empty-state rendering with storage disabled passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-021 Stored sessions trust cached rendering and dynamic inline handlers correction and bounded regression

**Finding ids:** FND-005

**Change locations:** web/assets/ui.js, tools/frontend_resilience_check.js

**Implementation steps:** Whitelist plain session/turn fields; reconstruct remote run content; escaped data attributes and native buttons replace interpolated onclick arguments., Run tools/frontend_resilience_check.js: storedHistory and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Stored sessions trust cached rendering and dynamic inline handlers passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-022 Invalid model score and zero-attempt presentation correction and bounded regression

**Finding ids:** FND-006

**Change locations:** web/index.html, tools/frontend_resilience_check.js

**Implementation steps:** Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts., Run tools/frontend_resilience_check.js: honestScoreAndAttempts and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Invalid model score and zero-attempt presentation passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-023 State contract events need truthful separation from reward correction and bounded regression

**Finding ids:** FND-007

**Change locations:** web/assets/showcase.js, tools/showcase_check.js

**Implementation steps:** Show declaration compatibility separately from observed checks; unknown blocks remain unknown; no judge/evolution is synthesized., Run tools/showcase_check.js: contracts and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence State contract events need truthful separation from reward passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-024 Late mission/evaluation/system/health responses overwrite newer state correction and bounded regression

**Finding ids:** FND-008

**Change locations:** web/app.html, tools/frontend_resilience_check.js

**Implementation steps:** Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result., Run tools/frontend_resilience_check.js: centreRequestOwnership and all shared frontend checks; retain independent browser acceptance tasks.

**Acceptance criteria:** Bounded sequence Late mission/evaluation/system/health responses overwrite newer state passes its assertions; no whole-page runtime claim.

**Rollback:** Revert this isolated frontend mechanism only if needed; never roll back user run/library data.

**Risk:** Full-browser interaction/visual implications remain covered by blocked page acceptance tasks.

**Evidence ids:** EV-019

## TASK-025 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs browser verification

**Finding ids:** FND-009

**Change locations:** web/briefing.html

**Implementation steps:** Native dialog, escaped data attributes/delegated clicks and per-open generation ownership now replace those paths., Execute all linked route scenarios; add sanitized actual evidence and resolve only after assertions.

**Acceptance criteria:** Affected control/state satisfies Native dialog, escaped data attributes/delegated clicks and per-open generation ownership now replace those paths.

**Rollback:** Revert only the isolated UI change after verifying the old defect is not reintroduced; preserve run/library data.

**Risk:** Implemented source correction still requires browser/focus/visual evidence.

**Evidence ids:** EV-019

## TASK-026 Replay load/preview stale failures can overwrite current state browser verification

**Finding ids:** FND-010

**Change locations:** web/assets/showcase.js

**Implementation steps:** Guard catch/finally and dialog updates with their request generation and open state., Execute all linked route scenarios; add sanitized actual evidence and resolve only after assertions.

**Acceptance criteria:** Affected control/state satisfies Guard catch/finally and dialog updates with their request generation and open state.

**Rollback:** Revert only the isolated UI change after verifying the old defect is not reintroduced; preserve run/library data.

**Risk:** Implemented source correction still requires browser/focus/visual evidence.

**Evidence ids:** EV-019

## TASK-027 Native step controls receive duplicate keyboard activation browser verification

**Finding ids:** FND-011

**Change locations:** web/assets/showcase.js

**Implementation steps:** Only non-native step targets use manual key activation; buttons keep their native behavior., Execute all linked route scenarios; add sanitized actual evidence and resolve only after assertions.

**Acceptance criteria:** Affected control/state satisfies Only non-native step targets use manual key activation; buttons keep their native behavior.

**Rollback:** Revert only the isolated UI change after verifying the old defect is not reintroduced; preserve run/library data.

**Risk:** Implemented source correction still requires browser/focus/visual evidence.

**Evidence ids:** EV-019

## TASK-028 Sphere keyboard pause/focus state not reflected consistently browser verification

**Finding ids:** FND-012

**Change locations:** web/assets/graph-sphere.js

**Implementation steps:** Central onPause synchronizes button text/aria; selected heading receives focus and close restores origin; filter reset synchronizes aria-pressed., Execute all linked route scenarios; add sanitized actual evidence and resolve only after assertions.

**Acceptance criteria:** Affected control/state satisfies Central onPause synchronizes button text/aria; selected heading receives focus and close restores origin; filter reset synchronizes aria-pressed.

**Rollback:** Revert only the isolated UI change after verifying the old defect is not reintroduced; preserve run/library data.

**Risk:** Implemented source correction still requires browser/focus/visual evidence.

**Evidence ids:** EV-019

## TASK-029 Global chip binding replaces injected scenario actions browser verification

**Finding ids:** FND-013

**Change locations:** web/briefing.html

**Implementation steps:** Scope legacy handlers to #chips [data-i] so each component retains ownership., Execute all linked route scenarios; add sanitized actual evidence and resolve only after assertions.

**Acceptance criteria:** Affected control/state satisfies Scope legacy handlers to #chips [data-i] so each component retains ownership.

**Rollback:** Revert only the isolated UI change after verifying the old defect is not reintroduced; preserve run/library data.

**Risk:** Implemented source correction still requires browser/focus/visual evidence.

**Evidence ids:** EV-019

## TASK-030 Historical growth and S1 deployment labels overstate supported evidence browser verification

**Finding ids:** FND-014

**Change locations:** web/briefing.html, web/app.html, web/index.html

**Implementation steps:** State asset growth separately from quality; model scores only reference; current queue/isolation mode separate from unverified S1/production acceptance., Execute all linked route scenarios; add sanitized actual evidence and resolve only after assertions.

**Acceptance criteria:** Affected control/state satisfies State asset growth separately from quality; model scores only reference; current queue/isolation mode separate from unverified S1/production acceptance.

**Rollback:** Revert only the isolated UI change after verifying the old defect is not reintroduced; preserve run/library data.

**Risk:** Implemented source correction still requires browser/focus/visual evidence.

**Evidence ids:** EV-019

## TASK-031 Verify shared Product controller fault corrections

**Finding ids:** FND-015

**Change locations:** web/assets/product.js, tools/product_dialog_check.js

**Implementation steps:** Use current Product controller with beginPanel request epochs and the actual delegated event handler., Run all twelve controlled DOM assertion groups; keep browser tasks independent.

**Acceptance criteria:** All actual fault-injection assertions pass with no network/model calls., No claim of native dialog/visual/accessibility verification from the harness.

**Rollback:** Revert only the individual Product fix if a regression is reproduced; preserve run/library data and rerun all controller identity/security scenarios.

**Risk:** Controlled DOM cannot prove native focus, browser rendering, tenant authorization or production deployment.

**Evidence ids:** EV-022

## TASK-032 Graph search lacked keyboard selection actual browser correction

**Finding ids:** FND-016

**Change locations:** web/assets/graph-sphere.js

**Implementation steps:** Root added Enter selection and ArrowDown focus to query results; actual Enter→heading→Escape and Space synchronization were rechecked., Capture actual root browser result and retain before/final distinctions.

**Acceptance criteria:** Specific recorded Graph search lacked keyboard selection sequence passes.

**Rollback:** Revert only this UI correction if a new regression is reproduced; preserve user run/library data and repeat the named browser assertion.

**Risk:** Only the recorded dimensions/interaction are verified; whole-page and production coverage stay blocked.

**Evidence ids:** EV-037

## TASK-033 Mobile uniqueness cards inherited three inline columns and overflowed actual browser correction

**Finding ids:** FND-017

**Change locations:** web/briefing.html, web/assets/presentation.css

**Implementation steps:** Root removed inline columns and added mobile one-column presentation.css rule; final observed grid width 340 px and document scrollWidth 380 ≤ viewport 390., Capture actual root browser result and retain before/final distinctions.

**Acceptance criteria:** Specific recorded Mobile uniqueness cards inherited three inline columns and overflowed sequence passes.

**Rollback:** Revert only this UI correction if a new regression is reproduced; preserve user run/library data and repeat the named browser assertion.

**Risk:** Only the recorded dimensions/interaction are verified; whole-page and production coverage stay blocked.

**Evidence ids:** EV-035

## TASK-034 Final local deliverable count correction

**Finding ids:** FND-018

**Change locations:** web/assets/product.js: valueHTML, web/assets/showcase.js: renderOutput, tools/product_check.js

**Implementation steps:** Use the same input-kind exclusion in new-deliverable summaries., Retain input artifacts separately; run added renderer assertion., Record historical v4 screenshot separately from final source v5.

**Acceptance criteria:** Mixed task/cross-turn input and CSV fixture displays one new deliverable.

**Rollback:** Revert only the local presentation correction if a regression is reproduced; preserve input/artifact records and rerun the mixed-provenance assertion.

**Risk:** Pure renderer test and historical screenshot do not revalidate every page or bind final deployment bytes.

**Evidence ids:** EV-046

## TASK-035 Verify shared frontier IIFE fault logic

**Change locations:** web/assets/frontier.js, web/assets/frontier.css, tools/frontier_ui_check.js

**Implementation steps:** Execute actual IIFE controlled DOM tests for ownership, errors, POST dedupe, unsafe data, download and focus recovery; preserve browser-versus-logic scope.

**Acceptance criteria:** Listed scenario expectations have explicit matching evidence; partial local logic or viewport evidence is not promoted to all-view release acceptance.

**Rollback:** Revert only reproduced frontier UI changes and rerun named scenarios; retain original sphere/background/history/seven-stage workflow and experimental source reports.

**Risk:** Shared imports affect six documents and sixteen parent views; CSS cascade and native focus differ from controlled DOM. Production S1, assistive technology and performance remain unverified.

**Evidence ids:** EV-051

## TASK-036 Repair and natively recheck v7 frontier modal/footer cascade

**Finding ids:** FND-019, FND-020

**Change locations:** web/assets/frontier.js, web/assets/frontier.css, tools/frontier_ui_check.js

**Implementation steps:** Apply explicit auto dialog margin and direct-child scoped footer layout., Recheck desktop/mobile geometry and footer padding in final actual IAB; retain v7 failure evidence.

**Acceptance criteria:** Listed scenario expectations have explicit matching evidence; partial local logic or viewport evidence is not promoted to all-view release acceptance.

**Rollback:** Revert only reproduced frontier UI changes and rerun named scenarios; retain original sphere/background/history/seven-stage workflow and experimental source reports.

**Risk:** Shared imports affect six documents and sixteen parent views; CSS cascade and native focus differ from controlled DOM. Production S1, assistive technology and performance remain unverified.

**Evidence ids:** EV-050, EV-054

## TASK-037 Repair and natively recheck disabled-submit focus

**Finding ids:** FND-021

**Change locations:** web/assets/frontier.js, web/assets/frontier.css, tools/frontier_ui_check.js

**Implementation steps:** On current POST success/error recover only lost BODY/outside focus; preserve deliberate inside-dialog focus., Run actual IIFE focus fault assertions and actual IAB final response/escape/return-focus sequence.

**Acceptance criteria:** Listed scenario expectations have explicit matching evidence; partial local logic or viewport evidence is not promoted to all-view release acceptance.

**Rollback:** Revert only reproduced frontier UI changes and rerun named scenarios; retain original sphere/background/history/seven-stage workflow and experimental source reports.

**Risk:** Shared imports affect six documents and sixteen parent views; CSS cascade and native focus differ from controlled DOM. Production S1, assistive technology and performance remain unverified.

**Evidence ids:** EV-051, EV-054

## TASK-038 Complete frontier integration in all sixteen parent views

**Change locations:** web/assets/frontier.js, web/assets/frontier.css, tools/frontier_ui_check.js

**Implementation steps:** Execute each registered parent-view scenario separately., Add real browser faults, content pressure, zoom/accessibility and production S1 evidence without inheriting shared module passes.

**Acceptance criteria:** Listed scenario expectations have explicit matching evidence; partial local logic or viewport evidence is not promoted to all-view release acceptance.

**Rollback:** Revert only reproduced frontier UI changes and rerun named scenarios; retain original sphere/background/history/seven-stage workflow and experimental source reports.

**Risk:** Shared imports affect six documents and sixteen parent views; CSS cascade and native focus differ from controlled DOM. Production S1, assistive technology and performance remain unverified.

## TASK-039 Verify bounded exploration/shared-context controller logic

**Change locations:** tools/hero_explorer_check.js, tools/graph_explorer_check.js, tools/product_check.js, tools/product_dialog_check.js, tools/showcase_check.js

**Implementation steps:** Read actual handlers/helpers and execute five named commands, all exiting 0., Record exact source hashes and narrow assertions separately from native layout/focus and deployment identity; preserve prior framework behavior.

**Acceptance criteria:** All listed controlled-logic scenarios have actual test evidence; no native/tenant/performance conclusion inferred.

**Rollback:** Revert only a reproduced explorer/context source change and rerun its original risk assertions; preserve run/library data and prior sphere/seven-stage assets.

**Risk:** Controlled DOM has no native geometry/assistive/production model; source changes after EV hashes need fresh checks.

**Evidence ids:** EV-056, EV-057, EV-058

## TASK-040 Complete bounded native exploration and actual parent-context acceptance

**Depends on:** TASK-039

**Change locations:** web/briefing.html, web/graph.html, web/run.html, web/assets/hero-explorer.js, web/assets/graph-sphere.js, web/assets/product.js, docs/frontend-audit/exploration-ui-observations.json (root-owned future observation)

**Implementation steps:** Execute SCN-084..087 at the final actual source/runtime baseline; record only assertions truly observed., Keep v10 graph overlap failure and verify later CSS repair separately; do not overwrite historical evidence., Follow all original per-view scenarios and zoom/assistive/browser-fault/performance gaps without inheriting shared logic passes.

**Acceptance criteria:** Each explicitly named native action/layout/focus observation matches its exact source/runtime baseline and parent., Original sixteen full views and eight production gates remain blocked until their own evidence exists.

**Rollback:** Revert only a reproduced UI delta; keep existing original controls/background/seven-stage flow and immutable research/run evidence.

**Risk:** Native CSS cascade and focus differ from controlled DOM; historical/production identities cannot be inferred from catalogue names.

## TASK-041 Repair and natively recheck graph task/filter overlap

**Finding ids:** FND-022

**Change locations:** web/graph.html: graph-filters/sphere-task responsive positioning, docs/frontend-audit/exploration-ui-observations.json (root-owned)

**Implementation steps:** Preserve actual v10 failure screenshot/geometry before repair., Change only graph layout constraints; verify closed/open filter and task combinations at final desktop/mobile build., Update current atomic check/scenario only from actual native geometry; keep historical failure in history and evidence.

**Acceptance criteria:** Task/filter surfaces do not intersect; heading/selector/evidence scroll remain usable in explicitly tested native viewports.

**Rollback:** Revert only graph positioning change if it breaks original sphere controls, retain v10 failure/evidence and public run assets.

**Risk:** CSS repair can change layering/scroll at other sizes; native v11 measurements required before resolved.

**Evidence ids:** EV-059, EV-060, EV-061, EV-062
