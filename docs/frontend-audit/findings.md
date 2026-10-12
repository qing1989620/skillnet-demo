# 问题与修复

## FND-001 Token clear/close race

级别 P1；置信度 confirmed；状态 resolved。

定位：PAGE-001, PAGE-002, PAGE-003, PAGE-004, PAGE-005, PAGE-006, PAGE-007, PAGE-008, PAGE-009, PAGE-010, PAGE-011, PAGE-012, PAGE-013, PAGE-014, PAGE-015, PAGE-016, CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148, DEF-001。

实际与根因：Clear token while validation is pending; a late failure previously restored the old credential. Closing could allow a late save.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.

复验：tools/frontend_resilience_check.js: tokenRace；SCN-017。

证据：EV-021, EV-019；修复验证：EV-019, EV-008。

## FND-002 Chained skill metadata overwrites a newer query

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-005, CMP-065, DEF-011。

实际与根因：Old skills request could finish optional metadata after a newer query and overwrite its results; metadata outage erased a valid page.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Guard after each await/catch/finally and keep a successfully loaded page if optional metadata fails.

复验：tools/frontend_resilience_check.js: skillsRace；SCN-018。

证据：EV-021, EV-019；修复验证：EV-019, EV-004。

## FND-003 Confirmed run creation misreported when storage is disabled

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-003, CMP-052, DEF-009。

实际与根因：localStorage.setItem threw after successful POST and blocked navigation, inviting a repeated paid run.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Persistence failure cannot change confirmed run identity; redirect using returned ID.

复验：tools/frontend_resilience_check.js: blockedStorage；SCN-019。

证据：EV-021, EV-019；修复验证：EV-019, EV-004。

## FND-004 Run detail crashes before empty-state rendering with storage disabled

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-008, CMP-089, DEF-014。

实际与根因：RUN_ID read localStorage without a guard when the URL had no ID.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Guard fallback storage and render the missing-run state normally.

复验：tools/frontend_resilience_check.js: blockedStorage；SCN-020。

证据：EV-021, EV-019；修复验证：EV-019, EV-005。

## FND-005 Stored sessions trust cached rendering and dynamic inline handlers

级别 P1；置信度 confirmed；状态 resolved。

定位：PAGE-001, PAGE-002, CMP-019, CMP-038, DEF-006, DEF-008。

实际与根因：Parsed history retained cached HTML/final snapshots; session IDs entered inline JavaScript handlers. This is a source-confirmed trust boundary, not a demonstrated remote exploit.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Whitelist plain session/turn fields; reconstruct remote run content; escaped data attributes and native buttons replace interpolated onclick arguments.

复验：tools/frontend_resilience_check.js: storedHistory；SCN-021。

证据：EV-021, EV-019；修复验证：EV-019, EV-008。

## FND-006 Invalid model score and zero-attempt presentation

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-002, PAGE-011, PAGE-014, CMP-041, CMP-122, CMP-143, DEF-008, DEF-018, DEF-021。

实际与根因：Legacy renderers could format missing/invalid scores as numeric values and show blocked zero-attempt steps as one attempt.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts.

复验：tools/frontend_resilience_check.js: honestScoreAndAttempts；SCN-022。

证据：EV-021, EV-019；修复验证：EV-019, EV-007。

## FND-007 State contract events need truthful separation from reward

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-001, CMP-014, DEF-004。

实际与根因：New state.planned/admission/effects require a frontend branch; otherwise pre-execution block and evidence gap are invisible in executive replay.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Show declaration compatibility separately from observed checks; unknown blocks remain unknown; no judge/evolution is synthesized.

复验：tools/showcase_check.js: contracts；SCN-023。

证据：EV-021, EV-019；修复验证：EV-019, EV-010。

## FND-008 Late mission/evaluation/system/health responses overwrite newer state

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-003, PAGE-006, PAGE-007, CMP-051, CMP-070, CMP-073, DEF-002, DEF-012, DEF-013。

实际与根因：Re-entered or connection-changed centre requests had no generation ownership, including two-stage latest detail and stale failure branches.

影响：Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

修复：Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result.

复验：tools/frontend_resilience_check.js: centreRequestOwnership；SCN-024。

证据：EV-021, EV-019；修复验证：EV-019, EV-004。

## FND-009 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs

级别 P1；置信度 confirmed；状态 fixed_unverified。

定位：PAGE-001, CMP-024, DEF-007。

实际与根因：Escaping HTML is insufficient inside an inline JavaScript argument; delayed preview completion lacked owner/close invalidation.

影响：Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

修复：Native dialog, escaped data attributes/delegated clicks and per-open generation ownership now replace those paths.

复验：Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.；SCN-001。

证据：EV-021, EV-002；修复验证：浏览器待核验。

## FND-010 Replay load/preview stale failures can overwrite current state

级别 P2；置信度 confirmed；状态 fixed_unverified。

定位：PAGE-001, CMP-010, CMP-023, DEF-004。

实际与根因：Stale catch/finally branches were outside request generation guards; old failed requests could mutate a newer load.

影响：Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

修复：Guard catch/finally and dialog updates with their request generation and open state.

复验：Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.；SCN-001。

证据：EV-021, EV-010；修复验证：浏览器待核验。

## FND-011 Native step controls used a manual keyboard override

级别 P3；置信度 probable；状态 fixed_unverified。

定位：PAGE-001, CMP-013, DEF-004。

实际与根因：The shared fallback key handler also intercepted native step buttons and prevented their browser default. Source proves the override; duplicate native activation was not reproduced and is not asserted.

影响：Manual override broadens keyboard handling; the actual user-visible difference requires browser comparison.

修复：Only non-native step targets use manual key activation; buttons keep their native behavior.

复验：Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.；SCN-001。

证据：EV-021, EV-010；修复验证：浏览器待核验。

## FND-012 Sphere keyboard pause/focus state not reflected consistently

级别 P2；置信度 confirmed；状态 fixed_unverified。

定位：PAGE-009, CMP-104, CMP-106, CMP-107, DEF-015。

实际与根因：Canvas Space/focus/reduced-motion changes could leave pause labels stale; detail selection did not focus the detail heading.

影响：Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

修复：Central onPause synchronizes button text/aria; selected heading receives focus and close restores origin; filter reset synchronizes aria-pressed.

复验：Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.；SCN-009。

证据：EV-021, EV-012；修复验证：浏览器待核验。

## FND-013 Global chip binding replaces injected scenario actions

级别 P2；置信度 confirmed；状态 fixed_unverified。

定位：PAGE-001, CMP-018, DEF-006。

实际与根因：Binding all .chip elements assigned legacy data-i handler to unrelated injected scenario chips.

影响：Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

修复：Scope legacy handlers to #chips [data-i] so each component retains ownership.

复验：Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.；SCN-001。

证据：EV-021, EV-002；修复验证：浏览器待核验。

## FND-014 Historical growth and S1 deployment labels overstate supported evidence

级别 P2；置信度 confirmed；状态 fixed_unverified。

定位：PAGE-001, PAGE-007, PAGE-011, PAGE-016, CMP-026, CMP-030, CMP-074, CMP-122, CMP-149, DEF-005, DEF-013, DEF-018, DEF-023。

实际与根因：Some legacy text equated new asset counts with ability improvement or available deploy code with accepted production integration.

影响：Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

修复：State asset growth separately from quality; model scores only reference; current queue/isolation mode separate from unverified S1/production acceptance.

复验：Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.；SCN-001, SCN-007, SCN-011, SCN-016。

证据：EV-021, EV-002, EV-004, EV-007；修复验证：浏览器待核验。

## FND-015 Shared Product dialog async ownership, unsafe field boundaries and missing-step recovery

级别 P1；置信度 confirmed；状态 resolved。

定位：PAGE-001, CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160, DEF-024, DEF-025, DEF-026, DEF-027, DEF-028, DEF-029, DEF-030, DEF-031。

实际与根因：The reviewed original Product inspectors could open on late completion or overwrite another view, including stale catch; previews relied on filename rather than run/file identity, some count/attempt fields interpreted API strings, and missing-step lookup did not settle explicitly.

影响：Stale cross-context output, misleading/unsafe rendered fields and stuck loading can affect the demo. The actual correction is verified by controlled DOM fault injection; native browser acceptance remains separate.

修复：Parent implemented beginPanel/requestEpoch with close/cancel/pagehide invalidation, run/file-owned callbacks, escaped fields, bounded/cancelled artifact reads and explicit missing-step handling.

复验：node tools/product_dialog_check.js; twelve independently named assertion groups；SCN-025, SCN-026, SCN-027, SCN-028, SCN-029, SCN-030, SCN-031, SCN-032, SCN-033, SCN-034, SCN-035, SCN-036。

证据：EV-009, EV-022；修复验证：EV-009, EV-022。

## FND-016 Graph search lacked keyboard selection

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-009, CMP-093, DEF-015。

实际与根因：Root actual IAB check found Enter did not activate the first search result; the keyboard journey stopped before detail focus.

影响：The recorded mobile/keyboard journey is impaired in the specific observed conditions; no broader scope inferred.

修复：Root added Enter selection and ArrowDown focus to query results; actual Enter→heading→Escape and Space synchronization were rechecked.

复验：SCN-051 in actual Codex IAB；SCN-051。

证据：EV-042, EV-037, EV-012；修复验证：EV-037, EV-012。

## FND-017 Mobile uniqueness cards inherited three inline columns and overflowed

级别 P2；置信度 confirmed；状态 resolved。

定位：PAGE-001, CMP-026, DEF-005。

实际与根因：Root actual phone view found inline three-column uniq-three cards extending 6 px beyond the intended width.

影响：The recorded mobile/keyboard journey is impaired in the specific observed conditions; no broader scope inferred.

修复：Root removed inline columns and added mobile one-column presentation.css rule; final observed grid width 340 px and document scrollWidth 380 ≤ viewport 390.

复验：SCN-049 in actual Codex IAB；SCN-049。

证据：EV-043, EV-035, EV-002, EV-044；修复验证：EV-035, EV-002, EV-044。


## FND-018 Task input was incorrectly included in newly delivered file count

级别 P2；confirmed；resolved。定位 CMP-156 / DEF-027。任务和跨轮输入不计作本轮新交付；Product 与 Showcase 使用相同过滤口径。实际新增断言 SCN-053（EV-046）通过；源码 EV-047；历史 v4 截图 EV-048 仅证明所呈现状态。TASK-034 保留回归任务。
