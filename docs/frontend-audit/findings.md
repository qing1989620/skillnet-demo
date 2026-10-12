# Findings and repairs

audit.json is authoritative. Historical failure evidence is retained; resolved means only the explicitly verified repair scope. Pending full-view or production acceptance is not a newly reproduced defect.

## FND-001 Token clear/close race

Severity P1; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-001, PAGE-002, PAGE-003, PAGE-004, PAGE-005, PAGE-006, PAGE-007, PAGE-008, PAGE-009, PAGE-010, PAGE-011, PAGE-012, PAGE-013, PAGE-014, PAGE-015, PAGE-016, CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148, DEF-001

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** token validation pending → clear → reject late request, validate new candidate → close → resolve old response

**Actual:** Clear token while validation is pending; a late failure previously restored the old credential. Closing could allow a late save.

**Expected:** Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** Clear token while validation is pending; a late failure previously restored the old credential. Closing could allow a late save.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Candidate validation has a generation and AbortController; only the latest still-open dialog may commit.

**Regression test:** tools/frontend_resilience_check.js: tokenRace

**Checks / scenarios:** CHK-1281, CHK-1282, CHK-1283, CHK-1284, CHK-1285, CHK-1286, CHK-1287, CHK-1288, CHK-1289, CHK-1290, CHK-1291, CHK-1292, CHK-1293, CHK-1294, CHK-1295, CHK-1296, SCN-017

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-008

## FND-002 Chained skill metadata overwrites a newer query

Severity P2; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-005, CMP-065, DEF-011

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** A result waits for stats → B result/stats completes → A stats completes, A errors after B success; stats outage after valid page

**Actual:** Old skills request could finish optional metadata after a newer query and overwrite its results; metadata outage erased a valid page.

**Expected:** Guard after each await/catch/finally and keep a successfully loaded page if optional metadata fails.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** Old skills request could finish optional metadata after a newer query and overwrite its results; metadata outage erased a valid page.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Guard after each await/catch/finally and keep a successfully loaded page if optional metadata fails.

**Regression test:** tools/frontend_resilience_check.js: skillsRace

**Checks / scenarios:** CHK-1297, SCN-018

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-004

## FND-003 Confirmed run creation misreported when storage is disabled

Severity P2; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-003, CMP-052, DEF-009

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** successful POST → localStorage throws → navigate once

**Actual:** localStorage.setItem threw after successful POST and blocked navigation, inviting a repeated paid run.

**Expected:** Persistence failure cannot change confirmed run identity; redirect using returned ID.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** localStorage.setItem threw after successful POST and blocked navigation, inviting a repeated paid run.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Persistence failure cannot change confirmed run identity; redirect using returned ID.

**Regression test:** tools/frontend_resilience_check.js: blockedStorage

**Checks / scenarios:** CHK-1298, SCN-019

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-004

## FND-004 Run detail crashes before empty-state rendering with storage disabled

Severity P2; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-008, CMP-089, DEF-014

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** URL has no id and localStorage.getItem throws

**Actual:** RUN_ID read localStorage without a guard when the URL had no ID.

**Expected:** Guard fallback storage and render the missing-run state normally.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** RUN_ID read localStorage without a guard when the URL had no ID.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Guard fallback storage and render the missing-run state normally.

**Regression test:** tools/frontend_resilience_check.js: blockedStorage

**Checks / scenarios:** CHK-1299, SCN-020

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-005

## FND-005 Stored sessions trust cached rendering and dynamic inline handlers

Severity P1; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-001, PAGE-002, CMP-019, CMP-038, DEF-006, DEF-008

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** load malformed/session data with cached HTML and quote-bearing ID, render native session buttons without event attribute injection

**Actual:** Parsed history retained cached HTML/final snapshots; session IDs entered inline JavaScript handlers. This is a source-confirmed trust boundary, not a demonstrated remote exploit.

**Expected:** Whitelist plain session/turn fields; reconstruct remote run content; escaped data attributes and native buttons replace interpolated onclick arguments.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** Parsed history retained cached HTML/final snapshots; session IDs entered inline JavaScript handlers. This is a source-confirmed trust boundary, not a demonstrated remote exploit.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Whitelist plain session/turn fields; reconstruct remote run content; escaped data attributes and native buttons replace interpolated onclick arguments.

**Regression test:** tools/frontend_resilience_check.js: storedHistory

**Checks / scenarios:** CHK-1300, CHK-1301, SCN-021

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-008

## FND-006 Invalid model score and zero-attempt presentation

Severity P2; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-002, PAGE-011, PAGE-014, CMP-041, CMP-122, CMP-143, DEF-008, DEF-018, DEF-021

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** render invalid/null/infinite/actual-zero scores, render admission-blocked step with n_attempts=0

**Actual:** Legacy renderers could format missing/invalid scores as numeric values and show blocked zero-attempt steps as one attempt.

**Expected:** Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** Legacy renderers could format missing/invalid scores as numeric values and show blocked zero-attempt steps as one attempt.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Only finite valid model values display; actual numeric zero stays valid; null/invalid are unavailable and blocked execution stays at zero attempts.

**Regression test:** tools/frontend_resilience_check.js: honestScoreAndAttempts

**Checks / scenarios:** CHK-1302, CHK-1303, CHK-1304, SCN-022

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-007

## FND-007 State contract events need truthful separation from reward

Severity P2; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-001, CMP-014, DEF-004

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** planned unknown frontier → admission unknown/admitted false → effects failed, hostile check detail escapes and no score/reward is created

**Actual:** New state.planned/admission/effects require a frontend branch; otherwise pre-execution block and evidence gap are invisible in executive replay.

**Expected:** Show declaration compatibility separately from observed checks; unknown blocks remain unknown; no judge/evolution is synthesized.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** New state.planned/admission/effects require a frontend branch; otherwise pre-execution block and evidence gap are invisible in executive replay.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Show declaration compatibility separately from observed checks; unknown blocks remain unknown; no judge/evolution is synthesized.

**Regression test:** tools/showcase_check.js: contracts

**Checks / scenarios:** CHK-1305, SCN-023

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-010

## FND-008 Late mission/evaluation/system/health responses overwrite newer state

Severity P2; confidence confirmed; status **resolved**; owner frontend implementation.

**Scope:** PAGE-003, PAGE-006, PAGE-007, CMP-051, CMP-070, CMP-073, DEF-002, DEF-012, DEF-013

**Preconditions:** pre-change source baseline af07f453edf24a38782b4250e07f2d5fa0775416 and declared data/order

**Reproduction:** health B completes then health A fails, latest A waits for detail; B completes; A detail fails, evaluation/system B completes; A fails

**Actual:** Re-entered or connection-changed centre requests had no generation ownership, including two-stage latest detail and stale failure branches.

**Expected:** Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result.

**Impact:** Correctness/confidentiality or demonstration credibility degrades in the declared reachable event/data sequence. Severity reflects that bounded impact; no broader exploit/runtime claim.

**Root cause:** Re-entered or connection-changed centre requests had no generation ownership, including two-stage latest detail and stale failure branches.

**Root cause confidence:** confirmed source/control-flow; regression harness verifies bounded correction

**Remediation:** Each health/latest/evaluation/system request owns its current generation; outdated success/failure cannot overwrite the latest result.

**Regression test:** tools/frontend_resilience_check.js: centreRequestOwnership

**Checks / scenarios:** CHK-1306, CHK-1307, CHK-1308, SCN-024

**Original evidence:** EV-021, EV-019

**Repair evidence:** EV-019, EV-004

## FND-009 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs

Severity P1; confidence confirmed; status **fixed_unverified**; owner frontend implementation and browser QA.

**Scope:** PAGE-001, CMP-024, DEF-007

**Preconditions:** Known pre-change worktree/route and affected instance

**Reproduction:** Escaping HTML is insufficient inside an inline JavaScript argument; delayed preview completion lacked owner/close invalidation., Exercise the listed component with delayed/failing response, quote-bearing name or keyboard interaction as applicable.

**Actual:** Escaping HTML is insufficient inside an inline JavaScript argument; delayed preview completion lacked owner/close invalidation.

**Expected:** Native dialog, escaped data attributes/delegated clicks and per-open generation ownership now replace those paths.

**Impact:** Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

**Root cause:** Escaping HTML is insufficient inside an inline JavaScript argument; delayed preview completion lacked owner/close invalidation.

**Root cause confidence:** confirmed source; browser outcome pending

**Remediation:** Native dialog, escaped data attributes/delegated clicks and per-open generation ownership now replace those paths.

**Regression test:** Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.

**Checks / scenarios:** SCN-001

**Original evidence:** EV-021, EV-002

## FND-010 Replay load/preview stale failures can overwrite current state

Severity P2; confidence confirmed; status **fixed_unverified**; owner frontend implementation and browser QA.

**Scope:** PAGE-001, CMP-010, CMP-023, DEF-004

**Preconditions:** Known pre-change worktree/route and affected instance

**Reproduction:** Stale catch/finally branches were outside request generation guards; old failed requests could mutate a newer load., Exercise the listed component with delayed/failing response, quote-bearing name or keyboard interaction as applicable.

**Actual:** Stale catch/finally branches were outside request generation guards; old failed requests could mutate a newer load.

**Expected:** Guard catch/finally and dialog updates with their request generation and open state.

**Impact:** Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

**Root cause:** Stale catch/finally branches were outside request generation guards; old failed requests could mutate a newer load.

**Root cause confidence:** confirmed source; browser outcome pending

**Remediation:** Guard catch/finally and dialog updates with their request generation and open state.

**Regression test:** Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.

**Checks / scenarios:** SCN-001

**Original evidence:** EV-021, EV-010

## FND-011 Native step controls used a manual keyboard override

Severity P3; confidence probable; status **fixed_unverified**; owner frontend implementation and browser QA.

**Scope:** PAGE-001, CMP-013, DEF-004

**Preconditions:** Known pre-change worktree/route and affected instance

**Reproduction:** Global Enter/Space handler also applied to native buttons, alongside their synthesized click., Exercise the listed component with delayed/failing response, quote-bearing name or keyboard interaction as applicable.

**Actual:** The shared fallback key handler also intercepted native step buttons and prevented their browser default. Source proves the override; duplicate native activation was not reproduced and is not asserted.

**Expected:** Native buttons use native activation; only non-native graph targets require manual Enter/Space fallback.

**Impact:** Manual override broadens keyboard handling; the actual user-visible difference requires browser comparison.

**Root cause:** Fallback target selector included native controls.

**Root cause confidence:** confirmed selector; user-visible keyboard effect remains unverified

**Remediation:** Only non-native step targets use manual key activation; buttons keep their native behavior.

**Regression test:** Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.

**Checks / scenarios:** SCN-001

**Original evidence:** EV-021, EV-010

## FND-012 Sphere keyboard pause/focus state not reflected consistently

Severity P2; confidence confirmed; status **fixed_unverified**; owner frontend implementation and browser QA.

**Scope:** PAGE-009, CMP-104, CMP-106, CMP-107, DEF-015

**Preconditions:** Known pre-change worktree/route and affected instance

**Reproduction:** Canvas Space/focus/reduced-motion changes could leave pause labels stale; detail selection did not focus the detail heading., Exercise the listed component with delayed/failing response, quote-bearing name or keyboard interaction as applicable.

**Actual:** Canvas Space/focus/reduced-motion changes could leave pause labels stale; detail selection did not focus the detail heading.

**Expected:** Central onPause synchronizes button text/aria; selected heading receives focus and close restores origin; filter reset synchronizes aria-pressed.

**Impact:** Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

**Root cause:** Canvas Space/focus/reduced-motion changes could leave pause labels stale; detail selection did not focus the detail heading.

**Root cause confidence:** confirmed source; browser outcome pending

**Remediation:** Central onPause synchronizes button text/aria; selected heading receives focus and close restores origin; filter reset synchronizes aria-pressed.

**Regression test:** Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.

**Checks / scenarios:** SCN-009

**Original evidence:** EV-021, EV-012

## FND-013 Global chip binding replaces injected scenario actions

Severity P2; confidence confirmed; status **fixed_unverified**; owner frontend implementation and browser QA.

**Scope:** PAGE-001, CMP-018, DEF-006

**Preconditions:** Known pre-change worktree/route and affected instance

**Reproduction:** Binding all .chip elements assigned legacy data-i handler to unrelated injected scenario chips., Exercise the listed component with delayed/failing response, quote-bearing name or keyboard interaction as applicable.

**Actual:** Binding all .chip elements assigned legacy data-i handler to unrelated injected scenario chips.

**Expected:** Scope legacy handlers to #chips [data-i] so each component retains ownership.

**Impact:** Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

**Root cause:** Binding all .chip elements assigned legacy data-i handler to unrelated injected scenario chips.

**Root cause confidence:** confirmed source; browser outcome pending

**Remediation:** Scope legacy handlers to #chips [data-i] so each component retains ownership.

**Regression test:** Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.

**Checks / scenarios:** SCN-001

**Original evidence:** EV-021, EV-002

## FND-014 Historical growth and S1 deployment labels overstate supported evidence

Severity P2; confidence confirmed; status **fixed_unverified**; owner frontend implementation and browser QA.

**Scope:** PAGE-001, PAGE-007, PAGE-011, PAGE-016, CMP-026, CMP-030, CMP-074, CMP-122, CMP-149, DEF-005, DEF-013, DEF-018, DEF-023

**Preconditions:** Known pre-change worktree/route and affected instance

**Reproduction:** Some legacy text equated new asset counts with ability improvement or available deploy code with accepted production integration., Exercise the listed component with delayed/failing response, quote-bearing name or keyboard interaction as applicable.

**Actual:** Some legacy text equated new asset counts with ability improvement or available deploy code with accepted production integration.

**Expected:** State asset growth separately from quality; model scores only reference; current queue/isolation mode separate from unverified S1/production acceptance.

**Impact:** Reachable legacy control/data/state sequence can mislead, break navigation or impair keyboard use. Source confirms the mechanism; browser impact is not claimed reproduced.

**Root cause:** Some legacy text equated new asset counts with ability improvement or available deploy code with accepted production integration.

**Root cause confidence:** confirmed source; browser outcome pending

**Remediation:** State asset growth separately from quality; model scores only reference; current queue/isolation mode separate from unverified S1/production acceptance.

**Regression test:** Execute linked per-view browser scenarios with reordered preview requests, hostile names and keyboard focus.

**Checks / scenarios:** SCN-001, SCN-007, SCN-011, SCN-016

**Original evidence:** EV-021, EV-002, EV-004, EV-007

## FND-015 Shared Product dialog async ownership, unsafe field boundaries and missing-step recovery

Severity P1; confidence confirmed; status **resolved**; owner parent frontend implementation; controlled DOM verification merged by auditor.

**Scope:** PAGE-001, CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160, DEF-024, DEF-025, DEF-026, DEF-027, DEF-028, DEF-029, DEF-030, DEF-031

**Preconditions:** Pre-correction Product controller and delayed/hostile inputs specified by controlled harness.

**Reproduction:** Run the descriptor request sequences and hostile-field fixtures in tools/product_dialog_check.js.

**Actual:** The reviewed original Product inspectors could open on late completion or overwrite another view, including stale catch; previews relied on filename rather than run/file identity, some count/attempt fields interpreted API strings, and missing-step lookup did not settle explicitly.

**Expected:** All opens/callbacks belong to current dialog epoch, identity includes run/file; untrusted fields remain text; resource integrity and read bounds are enforced; missing step settles.

**Impact:** Stale cross-context output, misleading/unsafe rendered fields and stuck loading can affect the demo. The actual correction is verified by controlled DOM fault injection; native browser acceptance remains separate.

**Root cause:** Dialog/request ownership and escaping/empty-path checks were inconsistent across independent Product controllers.

**Root cause confidence:** confirmed source and actual controlled DOM assertions; native browser behavior not inferred

**Remediation:** Parent implemented beginPanel/requestEpoch with close/cancel/pagehide invalidation, run/file-owned callbacks, escaped fields, bounded/cancelled artifact reads and explicit missing-step handling.

**Regression test:** node tools/product_dialog_check.js; twelve independently named assertion groups

**Checks / scenarios:** CHK-1377, CHK-1378, CHK-1379, CHK-1380, CHK-1381, CHK-1382, CHK-1383, CHK-1384, CHK-1385, CHK-1386, CHK-1387, CHK-1388, CHK-1389, CHK-1390, CHK-1391, CHK-1392, CHK-1393, CHK-1394, CHK-1395, CHK-1396, CHK-1397, CHK-1398, CHK-1399, CHK-1400, CHK-1401, CHK-1402, CHK-1403, CHK-1404, CHK-1405, CHK-1406, CHK-1407, CHK-1408, CHK-1409, CHK-1410, CHK-1411, CHK-1412, CHK-1413, CHK-1414, CHK-1415, CHK-1416, CHK-1417, CHK-1418, CHK-1419, CHK-1420, CHK-1421, SCN-025, SCN-026, SCN-027, SCN-028, SCN-029, SCN-030, SCN-031, SCN-032, SCN-033, SCN-034, SCN-035, SCN-036

**Original evidence:** EV-009, EV-022

**Repair evidence:** EV-009, EV-022

## FND-016 Graph search lacked keyboard selection

Severity P2; confidence confirmed; status **resolved**; owner root frontend implementation and actual IAB regression.

**Scope:** PAGE-009, CMP-093, DEF-015

**Preconditions:** Root observed pre-correction browser at the recorded device/query state.

**Reproduction:** Root actual IAB check found Enter did not activate the first search result; the keyboard journey stopped before detail focus.

**Actual:** Root actual IAB check found Enter did not activate the first search result; the keyboard journey stopped before detail focus.

**Expected:** Root added Enter selection and ArrowDown focus to query results; actual Enter→heading→Escape and Space synchronization were rechecked.

**Impact:** The recorded mobile/keyboard journey is impaired in the specific observed conditions; no broader scope inferred.

**Root cause:** Root actual IAB check found Enter did not activate the first search result; the keyboard journey stopped before detail focus.

**Root cause confidence:** confirmed actual IAB finding and source change recorded by root

**Remediation:** Root added Enter selection and ArrowDown focus to query results; actual Enter→heading→Escape and Space synchronization were rechecked.

**Regression test:** SCN-051 in actual Codex IAB

**Checks / scenarios:** CHK-1440, CHK-1441, SCN-051

**Original evidence:** EV-042, EV-037, EV-012

**Repair evidence:** EV-037, EV-012

## FND-017 Mobile uniqueness cards inherited three inline columns and overflowed

Severity P2; confidence confirmed; status **resolved**; owner root frontend implementation and actual IAB regression.

**Scope:** PAGE-001, CMP-026, DEF-005

**Preconditions:** Root observed pre-correction browser at the recorded device/query state.

**Reproduction:** Root actual phone view found inline three-column uniq-three cards extending 6 px beyond the intended width.

**Actual:** Root actual phone view found inline three-column uniq-three cards extending 6 px beyond the intended width.

**Expected:** Root removed inline columns and added mobile one-column presentation.css rule; final observed grid width 340 px and document scrollWidth 380 ≤ viewport 390.

**Impact:** The recorded mobile/keyboard journey is impaired in the specific observed conditions; no broader scope inferred.

**Root cause:** Root actual phone view found inline three-column uniq-three cards extending 6 px beyond the intended width.

**Root cause confidence:** confirmed actual IAB finding and source change recorded by root

**Remediation:** Root removed inline columns and added mobile one-column presentation.css rule; final observed grid width 340 px and document scrollWidth 380 ≤ viewport 390.

**Regression test:** SCN-049 in actual Codex IAB

**Checks / scenarios:** CHK-1434, SCN-049

**Original evidence:** EV-043, EV-035, EV-002, EV-044

**Repair evidence:** EV-035, EV-002, EV-044

## FND-018 Task input was incorrectly included in newly delivered file count

Severity P2; confidence confirmed; status **resolved**; owner root final frontend correction and renderer verification.

**Scope:** PAGE-001, CMP-156, DEF-027

**Preconditions:** A run contains a registered task input along with generated files.

**Reproduction:** Open task delivery/value summary and compare displayed output count to file provenance.

**Actual:** Root browser review found valueHTML included task input as a newly delivered file. Historical task/cross-turn inputs are retained evidence, not outputs created by the current run.

**Expected:** Exclude both input kinds from deliverable totals while retaining their separate evidence/file availability.

**Impact:** Displayed engineering value is overstated by counting supplied input as new work; this is a local metric defect, not a claim of corrupted physical artifacts.

**Root cause:** The value renderer excluded cross-turn input but did not consistently exclude task input; executive count needed the same predicate.

**Root cause confidence:** confirmed root browser finding, source correction and bounded test assertion

**Remediation:** Root filters both input kinds in Product value summary and Showcase result/impact counts. Added product_check.js assertion verifies one output from the mixed three-file fixture.

**Regression test:** node tools/product_check.js; SCN-053

**Checks / scenarios:** CHK-1450, SCN-053

**Original evidence:** EV-047, EV-046, EV-048

**Repair evidence:** EV-046, EV-047

## FND-019 Frontier v7 dialog ignored centered modal margin

Severity P2; confidence confirmed; status **resolved**; owner root frontend implementation / actual IAB QA.

**Scope:** PAGE-001, CMP-161, DEF-032

**Preconditions:** Local IAB asset v20261012.7 with frontier dialog opened from homepage.

**Reproduction:** Open 能力边界实验., Execute combined and inspect modal geometry/footer/focus as applicable.

**Actual:** The desktop v7 dialog begins at x=0/y=0, while the rest of the viewport remains on its right.

**Expected:** The bounded native modal should have an even desktop inset and preserve internal scrolling.

**Impact:** The shared research presentation loses visual coherence or keyboard continuity in the demonstrated state; data/algorithm corruption is not established.

**Root cause:** The native dialog margin was overridden by a higher-priority global margin reset.

**Root cause confidence:** Confirmed cascade/focus explanation and bounded actual v8/v9 repair recheck; historical failure retained.

**Remediation:** Scope the fixed/inset/auto modal margin with sufficient cascade priority; remeasure x/y/width and body scrolling in final IAB.

**Regression test:** SCN-061; node tools/frontier_ui_check.js; final IAB geometry/focus recheck

**Checks / scenarios:** CHK-1605, CHK-1458, SCN-080, SCN-061

**Original evidence:** EV-052, EV-050, EV-051

**Repair evidence:** EV-054

**Historical scenarios:** SCN-061

## FND-020 Global footer styles overrode frontier modal footer

Severity P2; confidence confirmed; status **resolved**; owner root frontend implementation / actual IAB QA.

**Scope:** PAGE-001, CMP-161, DEF-032

**Preconditions:** Local IAB asset v20261012.7 with frontier dialog opened from homepage.

**Reproduction:** Open 能力边界实验., Execute combined and inspect modal geometry/footer/focus as applicable.

**Actual:** The v7 screenshot shows footer content starting flush against the dialog edge and an oversized bottom area.

**Expected:** The modal footer should use its own 13px/30px spacing and adapt to the mobile 12px/18px rule.

**Impact:** The shared research presentation loses visual coherence or keyboard continuity in the demonstrated state; data/algorithm corruption is not established.

**Root cause:** Unscoped page footer styles won the cascade over the shared research surface.

**Root cause confidence:** Confirmed cascade/focus explanation and bounded actual v8/v9 repair recheck; historical failure retained.

**Remediation:** Use direct-child .frontier-dialog>.frontier-footer specificity and scoped mobile spacing; remeasure actual padding and footer height.

**Regression test:** SCN-062; node tools/frontier_ui_check.js; final IAB geometry/focus recheck

**Checks / scenarios:** CHK-1606, CHK-1459, SCN-081, SCN-062

**Original evidence:** EV-052, EV-050, EV-051

**Repair evidence:** EV-054

**Historical scenarios:** SCN-062

## FND-021 Disabled frontier submit left native focus on BODY

Severity P2; confidence confirmed; status **resolved**; owner root frontend implementation / actual IAB QA.

**Scope:** PAGE-001, CMP-161, DEF-032

**Preconditions:** Local IAB asset v20261012.7 with frontier dialog opened from homepage.

**Reproduction:** Open 能力边界实验., Execute combined and inspect modal geometry/footer/focus as applicable.

**Actual:** Root v7 IAB reported activeElement BODY after the POST control was temporarily disabled.

**Expected:** After result/error, recover lost focus to the enabled submit while preserving a deliberate focus move within the dialog.

**Impact:** The shared research presentation loses visual coherence or keyboard continuity in the demonstrated state; data/algorithm corruption is not established.

**Root cause:** Disabling the focused submit can drop native focus, and completion originally lacked a conditional recovery.

**Root cause confidence:** Confirmed cascade/focus explanation and bounded actual v8/v9 repair recheck; historical failure retained.

**Remediation:** On current success/error only, restore focus if it is BODY or outside the dialog; never steal focus from an internal control.

**Regression test:** SCN-063; node tools/frontier_ui_check.js; final IAB geometry/focus recheck

**Checks / scenarios:** CHK-1607, CHK-1460, SCN-082, SCN-063

**Original evidence:** EV-053, EV-050, EV-051

**Repair evidence:** EV-054

**Historical scenarios:** SCN-063

## FND-022 Graph v10 recorded-task pane overlaps the filter header

Severity P2; confidence confirmed; status **resolved**; owner graph frontend implementation / root actual IAB QA.

**Scope:** PAGE-009, CMP-100, CMP-191, CMP-192, DEF-015

**Preconditions:** Actual local graph v20261012.10, public run step=2,1440x900

**Reproduction:** Open the public recorded task and expand task input/effect/check details., Compare task top371 against filter362..401; observe concealed heading in explorer-step-desktop-v10.png.

**Actual:** At actual 1440x900 v10, task pane top371 intersects filter vertical interval362..401, concealing its heading; viewed screenshot matches overlap.

**Expected:** Task and filter surfaces reserve independent usable space; task heading and original-step selector remain visible and the expanded pane scrolls internally.

**Impact:** The graph demonstration hides a task-context heading and mixes exploration controls; evidence/backend corruption is not established.

**Root cause:** The expanded positioned task pane used height/offset constraints that collided with the filter rail. Repaired CSS reserves desktop space and temporarily hides the same task DOM while filters or the mobile skill card own that area.

**Root cause confidence:** Actual v10 overlap plus v11 native geometry/display restoration and read repaired CSS; scope limited to recorded viewports/states.

**Remediation:** Adjust owning graph layout offsets/flow and responsive constraints without shrinking away the sphere; verify bounding boxes and expanded/collapsed combinations in native browser.

**Regression test:** SCN-096 current native recheck, plus graph_explorer_check preservation; CSS/source checks alone cannot resolve a geometry defect.

**Checks / scenarios:** CHK-2004, SCN-096

**Original evidence:** EV-059, EV-060

**Repair evidence:** EV-061, EV-062

**Historical scenarios:** SCN-096
