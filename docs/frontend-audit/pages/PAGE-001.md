# PAGE-001 Executive briefing

Route `/`; source `web/briefing.html`; entry evidence EV-002, EV-023, EV-029, EV-035, EV-036, EV-050, EV-055, EV-061.

Evidence applies only to its named baseline, action and parent context. Complete-view scenarios remain blocked. Repeated records share an equivalence class only within the documented template and parent contract.

## Logical instances

| Instance | Definition / blueprint | Parent | Locator and variant | Disposition / tasks | Eight dimensions and additional checks |
|---|---|---|---|---|---|
| CMP-001 Page shell/navigation/status | DEF-005 / BP-005 | page | web/briefing.html: header / nav / main; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0001); states:blocked(CHK-0002); semantics_accessibility:blocked(CHK-0003); layout_content:blocked(CHK-0004); data_effects:blocked(CHK-0005); security_privacy:blocked(CHK-0006); performance_lifecycle:blocked(CHK-0007); maintainability_integration:passed(CHK-0008); layout_content:passed(CHK-1435) |
| CMP-002 Connection settings and toast | DEF-001 / BP-001 | page | web/briefing.html: UI.bootstrap / #ui-connection-dialog; implementation web/assets/ui.js: UI.bootstrap / connection dialog / UI.json / UI.readSessions; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-017 | behavior:blocked(CHK-0009); states:blocked(CHK-0010); semantics_accessibility:blocked(CHK-0011); layout_content:blocked(CHK-0012); data_effects:blocked(CHK-0013); security_privacy:blocked(CHK-0014); performance_lifecycle:blocked(CHK-0015); maintainability_integration:passed(CHK-0016); security_privacy:passed(CHK-1281) |
| CMP-003 Service/key/library status | DEF-005 / BP-005 | page | web/briefing.html: dot-srv / key-txt / lib-n; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0017); states:blocked(CHK-0018); semantics_accessibility:blocked(CHK-0019); layout_content:blocked(CHK-0020); data_effects:blocked(CHK-0021); security_privacy:blocked(CHK-0022); performance_lifecycle:blocked(CHK-0023); maintainability_integration:passed(CHK-0024) |
| CMP-004 Hero counts and chapter navigation | DEF-005 / BP-005 | page | web/briefing.html: top / hm-skills / hm-edges / hm-domains; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0025); states:blocked(CHK-0026); semantics_accessibility:blocked(CHK-0027); layout_content:blocked(CHK-0028); data_effects:blocked(CHK-0029); security_privacy:blocked(CHK-0030); performance_lifecycle:blocked(CHK-0031); maintainability_integration:passed(CHK-0032) |
| CMP-005 Hero sphere and tooltip | DEF-003 / BP-003 | page | web/briefing.html: netcv / nettip; implementation web/assets/sphere.js: SkillSphere.create; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0033); states:blocked(CHK-0034); semantics_accessibility:blocked(CHK-0035); layout_content:blocked(CHK-0036); data_effects:blocked(CHK-0037); security_privacy:blocked(CHK-0038); performance_lifecycle:blocked(CHK-0039); maintainability_integration:passed(CHK-0040) |
| CMP-006 Hero rotation button | DEF-003 / BP-003 | page | web/briefing.html: hero-rotate; implementation web/assets/sphere.js: SkillSphere.create; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0041); states:blocked(CHK-0042); semantics_accessibility:blocked(CHK-0043); layout_content:blocked(CHK-0044); data_effects:blocked(CHK-0045); security_privacy:blocked(CHK-0046); performance_lifecycle:blocked(CHK-0047); maintainability_integration:passed(CHK-0048) |
| CMP-007 Seven-phase stage and rail | DEF-004 / BP-004 | page | web/briefing.html: show-stage / show-rail; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0049); states:blocked(CHK-0050); semantics_accessibility:blocked(CHK-0051); layout_content:blocked(CHK-0052); data_effects:blocked(CHK-0053); security_privacy:blocked(CHK-0054); performance_lifecycle:blocked(CHK-0055); maintainability_integration:passed(CHK-0056); behavior:passed(CHK-1436); states:passed(CHK-1437) |
| CMP-008 Follow-live action | DEF-004 / BP-004 | page | web/briefing.html: show-follow; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0057); states:blocked(CHK-0058); semantics_accessibility:blocked(CHK-0059); layout_content:blocked(CHK-0060); data_effects:blocked(CHK-0061); security_privacy:blocked(CHK-0062); performance_lifecycle:blocked(CHK-0063); maintainability_integration:passed(CHK-0064) |
| CMP-009 Cancel action | DEF-004 / BP-004 | page | web/briefing.html: show-cancel; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0065); states:blocked(CHK-0066); semantics_accessibility:blocked(CHK-0067); layout_content:blocked(CHK-0068); data_effects:blocked(CHK-0069); security_privacy:blocked(CHK-0070); performance_lifecycle:blocked(CHK-0071); maintainability_integration:passed(CHK-0072) |
| CMP-010 Replay last run action | DEF-004 / BP-004 | page | web/briefing.html: show-replay; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-026 | behavior:blocked(CHK-0073); states:blocked(CHK-0074); semantics_accessibility:blocked(CHK-0075); layout_content:blocked(CHK-0076); data_effects:blocked(CHK-0077); security_privacy:blocked(CHK-0078); performance_lifecycle:blocked(CHK-0079); maintainability_integration:passed(CHK-0080) |
| CMP-011 Presentation action | DEF-004 / BP-004 | page | web/briefing.html: show-present; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0081); states:blocked(CHK-0082); semantics_accessibility:blocked(CHK-0083); layout_content:blocked(CHK-0084); data_effects:blocked(CHK-0085); security_privacy:blocked(CHK-0086); performance_lifecycle:blocked(CHK-0087); maintainability_integration:passed(CHK-0088) |
| CMP-012 Question collapse control | DEF-004 / BP-004 | page | web/briefing.html: show-question-toggle; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0089); states:blocked(CHK-0090); semantics_accessibility:blocked(CHK-0091); layout_content:blocked(CHK-0092); data_effects:blocked(CHK-0093); security_privacy:blocked(CHK-0094); performance_lifecycle:blocked(CHK-0095); maintainability_integration:passed(CHK-0096) |
| CMP-013 Task DAG and step buttons | DEF-004 / BP-004 | page | web/briefing.html: show-network / [data-show-step]; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-027 | behavior:blocked(CHK-0097); states:blocked(CHK-0098); semantics_accessibility:blocked(CHK-0099); layout_content:blocked(CHK-0100); data_effects:blocked(CHK-0101); security_privacy:blocked(CHK-0102); performance_lifecycle:blocked(CHK-0103); maintainability_integration:passed(CHK-0104) |
| CMP-014 Operation, activity and facts | DEF-004 / BP-004 | page | web/briefing.html: show-operation / show-activity / show-facts; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-023 | behavior:blocked(CHK-0105); states:blocked(CHK-0106); semantics_accessibility:blocked(CHK-0107); layout_content:blocked(CHK-0108); data_effects:blocked(CHK-0109); security_privacy:blocked(CHK-0110); performance_lifecycle:blocked(CHK-0111); maintainability_integration:passed(CHK-0112); states:passed(CHK-1305) |
| CMP-015 Replay pause/seek/speed controls | DEF-004 / BP-004 | page | web/briefing.html: show-pause / show-seek / show-speed; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0113); states:blocked(CHK-0114); semantics_accessibility:blocked(CHK-0115); layout_content:blocked(CHK-0116); data_effects:blocked(CHK-0117); security_privacy:blocked(CHK-0118); performance_lifecycle:blocked(CHK-0119); maintainability_integration:passed(CHK-0120); behavior:passed(CHK-1438); states:passed(CHK-1439) |
| CMP-016 Question input | DEF-006 / BP-006 | page | web/briefing.html: task; implementation web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0121); states:blocked(CHK-0122); semantics_accessibility:blocked(CHK-0123); layout_content:blocked(CHK-0124); data_effects:blocked(CHK-0125); security_privacy:blocked(CHK-0126); performance_lifecycle:blocked(CHK-0127); maintainability_integration:passed(CHK-0128) |
| CMP-017 Create-run action | DEF-006 / BP-006 | page | web/briefing.html: run; implementation web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0129); states:blocked(CHK-0130); semantics_accessibility:blocked(CHK-0131); layout_content:blocked(CHK-0132); data_effects:blocked(CHK-0133); security_privacy:blocked(CHK-0134); performance_lifecycle:blocked(CHK-0135); maintainability_integration:passed(CHK-0136) |
| CMP-018 Scenario/demo prompt buttons | DEF-006 / BP-006 | page | web/briefing.html: chips / [data-i]; implementation web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-029 | behavior:blocked(CHK-0137); states:blocked(CHK-0138); semantics_accessibility:blocked(CHK-0139); layout_content:blocked(CHK-0140); data_effects:blocked(CHK-0141); security_privacy:blocked(CHK-0142); performance_lifecycle:blocked(CHK-0143); maintainability_integration:passed(CHK-0144) |
| CMP-019 Saved session buttons | DEF-006 / BP-006 | page | web/briefing.html: ws-list / [data-session]; implementation web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-021 | behavior:blocked(CHK-0145); states:blocked(CHK-0146); semantics_accessibility:blocked(CHK-0147); layout_content:blocked(CHK-0148); data_effects:blocked(CHK-0149); security_privacy:blocked(CHK-0150); performance_lifecycle:blocked(CHK-0151); maintainability_integration:passed(CHK-0152); security_privacy:passed(CHK-1300) |
| CMP-020 Saved messages and detailed results | DEF-006 / BP-006 | page | web/briefing.html: ws-msgs; implementation web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0153); states:blocked(CHK-0154); semantics_accessibility:blocked(CHK-0155); layout_content:blocked(CHK-0156); data_effects:blocked(CHK-0157); security_privacy:blocked(CHK-0158); performance_lifecycle:blocked(CHK-0159); maintainability_integration:passed(CHK-0160) |
| CMP-021 Routing/impact/answer/file result regions | DEF-004 / BP-004 | page | web/briefing.html: show-routing / show-impact / show-answer-body / show-files-body; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0161); states:blocked(CHK-0162); semantics_accessibility:blocked(CHK-0163); layout_content:blocked(CHK-0164); data_effects:blocked(CHK-0165); security_privacy:blocked(CHK-0166); performance_lifecycle:blocked(CHK-0167); maintainability_integration:passed(CHK-0168) |
| CMP-022 Run and evidence navigation | DEF-004 / BP-004 | page | web/briefing.html: show-run-link / show-evidence-link; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0169); states:blocked(CHK-0170); semantics_accessibility:blocked(CHK-0171); layout_content:blocked(CHK-0172); data_effects:blocked(CHK-0173); security_privacy:blocked(CHK-0174); performance_lifecycle:blocked(CHK-0175); maintainability_integration:passed(CHK-0176) |
| CMP-023 Step preview dialog and close | DEF-004 / BP-004 | page | web/briefing.html: show-preview / show-preview-close; implementation web/assets/showcase.js: createState / reduceEvent / phaseFacts / replay controls / inspectStep; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-026 | behavior:blocked(CHK-0177); states:blocked(CHK-0178); semantics_accessibility:blocked(CHK-0179); layout_content:blocked(CHK-0180); data_effects:blocked(CHK-0181); security_privacy:blocked(CHK-0182); performance_lifecycle:blocked(CHK-0183); maintainability_integration:passed(CHK-0184) |
| CMP-024 Legacy artifact/skill preview dialog | DEF-007 / BP-007 | page | web/briefing.html: openLayer / [data-legacy-file] / [data-raw-skill]; implementation web/briefing.html: openLayer / closeLayer / previewArtifact / viewSkillRaw / renderArtifacts; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-025 | behavior:blocked(CHK-0185); states:blocked(CHK-0186); semantics_accessibility:blocked(CHK-0187); layout_content:blocked(CHK-0188); data_effects:blocked(CHK-0189); security_privacy:blocked(CHK-0190); performance_lifecycle:blocked(CHK-0191); maintainability_integration:passed(CHK-0192) |
| CMP-025 Legacy seven-stage timeline | DEF-006 / BP-006 | page | web/briefing.html: demo-seven / .tl-item; implementation web/briefing.html: task / run / wsRenderList / wsLoad / handleRunEvent; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0193); states:blocked(CHK-0194); semantics_accessibility:blocked(CHK-0195); layout_content:blocked(CHK-0196); data_effects:blocked(CHK-0197); security_privacy:blocked(CHK-0198); performance_lifecycle:blocked(CHK-0199); maintainability_integration:passed(CHK-0200) |
| CMP-026 Core problem/framework explanation | DEF-005 / BP-005 | page | web/briefing.html: s1 / s2 / ar / arg; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-030, TASK-033 | behavior:blocked(CHK-0201); states:blocked(CHK-0202); semantics_accessibility:blocked(CHK-0203); layout_content:blocked(CHK-0204); data_effects:blocked(CHK-0205); security_privacy:blocked(CHK-0206); performance_lifecycle:blocked(CHK-0207); maintainability_integration:passed(CHK-0208); layout_content:passed(CHK-1434) |
| CMP-027 Product screenshots and capabilities | DEF-005 / BP-005 | page | web/briefing.html: sproduct / s4; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0209); states:blocked(CHK-0210); semantics_accessibility:blocked(CHK-0211); layout_content:blocked(CHK-0212); data_effects:blocked(CHK-0213); security_privacy:blocked(CHK-0214); performance_lifecycle:blocked(CHK-0215); maintainability_integration:passed(CHK-0216) |
| CMP-028 Recorded run catalogue | DEF-005 / BP-005 | page | web/briefing.html: runlist / loadRunCenter; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0217); states:blocked(CHK-0218); semantics_accessibility:blocked(CHK-0219); layout_content:blocked(CHK-0220); data_effects:blocked(CHK-0221); security_privacy:blocked(CHK-0222); performance_lifecycle:blocked(CHK-0223); maintainability_integration:passed(CHK-0224) |
| CMP-029 Evidence/comparison controls and panel | DEF-005 / BP-005 | page | web/briefing.html: evpanel / cmpbox; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001 | behavior:blocked(CHK-0225); states:blocked(CHK-0226); semantics_accessibility:blocked(CHK-0227); layout_content:blocked(CHK-0228); data_effects:blocked(CHK-0229); security_privacy:blocked(CHK-0230); performance_lifecycle:blocked(CHK-0231); maintainability_integration:passed(CHK-0232) |
| CMP-030 S1 delivery / footer | DEF-005 / BP-005 | page | web/briefing.html: s5 / s6; implementation web/briefing.html: top / s1 / s2 / sproduct / s4 / s5 / s6; variants: route /; conditional and repeated data templates listed in label/locator | investigate / TASK-001, TASK-030 | behavior:blocked(CHK-0233); states:blocked(CHK-0234); semantics_accessibility:blocked(CHK-0235); layout_content:blocked(CHK-0236); data_effects:blocked(CHK-0237); security_privacy:blocked(CHK-0238); performance_lifecycle:blocked(CHK-0239); maintainability_integration:passed(CHK-0240) |
| CMP-153 Conditional Product resource manifest dialog | DEF-024 / BP-024 | page | web/assets/product.js: inspectResources / #resources-dialog / [data-skill-resources]; briefing evidence/result/context controls; variants: manifest loading/ready/error/closed | investigate / TASK-001, TASK-031 | behavior:blocked(CHK-1313); states:blocked(CHK-1314); semantics_accessibility:blocked(CHK-1315); layout_content:blocked(CHK-1316); data_effects:blocked(CHK-1317); security_privacy:blocked(CHK-1318); performance_lifecycle:blocked(CHK-1319); maintainability_integration:passed(CHK-1320); behavior:passed(CHK-1377); data_effects:passed(CHK-1378); security_privacy:passed(CHK-1379); behavior:passed(CHK-1404); data_effects:passed(CHK-1405); security_privacy:passed(CHK-1406) |
| CMP-154 Conditional Product verified resource file dialog | DEF-025 / BP-025 | page | web/assets/product.js: readResource / #resource-file-dialog / [data-resource-read]; briefing evidence/result/context controls; variants: digest verifying/mismatch/oversized/text/binary/closed | investigate / TASK-001, TASK-031 | behavior:blocked(CHK-1321); states:blocked(CHK-1322); semantics_accessibility:blocked(CHK-1323); layout_content:blocked(CHK-1324); data_effects:blocked(CHK-1325); security_privacy:blocked(CHK-1326); performance_lifecycle:blocked(CHK-1327); maintainability_integration:passed(CHK-1328); behavior:passed(CHK-1380); data_effects:passed(CHK-1381); security_privacy:passed(CHK-1382); behavior:passed(CHK-1401); data_effects:passed(CHK-1402); security_privacy:passed(CHK-1403); behavior:passed(CHK-1407); data_effects:passed(CHK-1408); security_privacy:passed(CHK-1409) |
| CMP-155 Conditional Product evidence export dialog | DEF-026 / BP-026 | page | web/assets/product.js: handoff / #evidence-dialog / [data-evidence-export]; briefing evidence/result/context controls; variants: evidence loading/ready/download/error/closed | investigate / TASK-001, TASK-031 | behavior:blocked(CHK-1329); states:blocked(CHK-1330); semantics_accessibility:blocked(CHK-1331); layout_content:blocked(CHK-1332); data_effects:blocked(CHK-1333); security_privacy:blocked(CHK-1334); performance_lifecycle:blocked(CHK-1335); maintainability_integration:passed(CHK-1336); behavior:passed(CHK-1383); data_effects:passed(CHK-1384); security_privacy:passed(CHK-1385) |
| CMP-156 Conditional Product run value dialog | DEF-027 / BP-027 | page | web/assets/product.js: inspectValue / #value-dialog / [data-run-value]; briefing evidence/result/context controls; variants: run loading/value ready/error/closed | investigate / TASK-001, TASK-031, TASK-034 | behavior:blocked(CHK-1337); states:blocked(CHK-1338); semantics_accessibility:blocked(CHK-1339); layout_content:blocked(CHK-1340); data_effects:blocked(CHK-1341); security_privacy:blocked(CHK-1342); performance_lifecycle:blocked(CHK-1343); maintainability_integration:passed(CHK-1344); behavior:passed(CHK-1386); data_effects:passed(CHK-1387); security_privacy:passed(CHK-1388); data_effects:passed(CHK-1450) |
| CMP-157 Conditional Product capability report dialog | DEF-028 / BP-028 | page | web/assets/product.js: inspectCapabilities / #capabilities-dialog / [data-capability-report]; briefing evidence/result/context controls; variants: report loading/unknown/failed/ready/download/closed | investigate / TASK-001, TASK-031 | behavior:blocked(CHK-1345); states:blocked(CHK-1346); semantics_accessibility:blocked(CHK-1347); layout_content:blocked(CHK-1348); data_effects:blocked(CHK-1349); security_privacy:blocked(CHK-1350); performance_lifecycle:blocked(CHK-1351); maintainability_integration:passed(CHK-1352); behavior:passed(CHK-1389); data_effects:passed(CHK-1390); security_privacy:passed(CHK-1391); behavior:passed(CHK-1410); data_effects:passed(CHK-1411); security_privacy:passed(CHK-1412); behavior:passed(CHK-1416); data_effects:passed(CHK-1417); security_privacy:passed(CHK-1418) |
| CMP-158 Conditional Product skill passport dialog | DEF-029 / BP-029 | page | web/assets/product.js: inspectPassport / #passport-dialog / [data-capability-skill]; briefing evidence/result/context controls; variants: declaration loading/ready/unknown/error/closed | investigate / TASK-001, TASK-031, TASK-040 | behavior:blocked(CHK-1353); states:blocked(CHK-1354); semantics_accessibility:blocked(CHK-1355); layout_content:blocked(CHK-1356); data_effects:blocked(CHK-1357); security_privacy:blocked(CHK-1358); performance_lifecycle:blocked(CHK-1359); maintainability_integration:passed(CHK-1360); behavior:passed(CHK-1392); data_effects:passed(CHK-1393); security_privacy:passed(CHK-1394); data_effects:passed(CHK-1641) |
| CMP-159 Conditional Product step details dialog | DEF-030 / BP-030 | page | web/assets/product.js: focusStep / #kernel-step-dialog / [data-kernel-step]; briefing evidence/result/context controls; variants: step loading/missing/ready/error/closed | investigate / TASK-001, TASK-031, TASK-040 | behavior:blocked(CHK-1361); states:blocked(CHK-1362); semantics_accessibility:blocked(CHK-1363); layout_content:blocked(CHK-1364); data_effects:blocked(CHK-1365); security_privacy:blocked(CHK-1366); performance_lifecycle:blocked(CHK-1367); maintainability_integration:passed(CHK-1368); behavior:passed(CHK-1395); data_effects:passed(CHK-1396); security_privacy:passed(CHK-1397); behavior:passed(CHK-1413); data_effects:passed(CHK-1414); security_privacy:passed(CHK-1415); behavior:passed(CHK-1419); data_effects:passed(CHK-1420); security_privacy:passed(CHK-1421); data_effects:passed(CHK-1642) |
| CMP-160 Conditional Product artifact preview dialog | DEF-031 / BP-031 | page | web/assets/product.js: preview / #product-preview / [data-artifact-preview]; briefing evidence/result/context controls; variants: run/file loading/text/image/pdf/unknown/large/error/closed | investigate / TASK-001, TASK-031 | behavior:blocked(CHK-1369); states:blocked(CHK-1370); semantics_accessibility:blocked(CHK-1371); layout_content:blocked(CHK-1372); data_effects:blocked(CHK-1373); security_privacy:blocked(CHK-1374); performance_lifecycle:blocked(CHK-1375); maintainability_integration:passed(CHK-1376); behavior:passed(CHK-1398); data_effects:passed(CHK-1399); security_privacy:passed(CHK-1400) |
| CMP-161 Capability frontier experiment launcher/dialog — Executive briefing | DEF-032 / BP-032 | page | web/briefing.html: frontier.js/frontier.css includes; / #frontier-launch → #frontier-dialog; variants: closed/loading/lab-error/scenario-empty/POST-pending/observed-success/rejected-by-oracle/unknown/closed-during-request | investigate / TASK-035, TASK-038, TASK-036, TASK-037 | semantics_accessibility:passed(CHK-1451); data_effects:passed(CHK-1452); states:passed(CHK-1453); security_privacy:passed(CHK-1454); behavior:passed(CHK-1455); security_privacy:passed(CHK-1456); semantics_accessibility:passed(CHK-1457); layout_content:passed(CHK-1458); layout_content:passed(CHK-1459); semantics_accessibility:passed(CHK-1460); behavior:blocked(CHK-1461); states:blocked(CHK-1462); semantics_accessibility:blocked(CHK-1463); layout_content:blocked(CHK-1464); data_effects:blocked(CHK-1465); security_privacy:blocked(CHK-1466); performance_lifecycle:blocked(CHK-1467); maintainability_integration:blocked(CHK-1468); maintainability_integration:passed(CHK-1469); maintainability_integration:passed(CHK-1605); maintainability_integration:passed(CHK-1606); maintainability_integration:passed(CHK-1607); maintainability_integration:passed(CHK-1608) |
| CMP-177 Hero capability explorer region and catalogue scope status | DEF-033 / BP-033 | CMP-001 | web/briefing.html #hero-explorer; hero-explorer.js mount/updateScope/failed; variants: catalogue loading/ready/empty/error/retry; current data count; DAG suspended/resumed | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1609); performance_lifecycle:passed(CHK-1622); behavior:blocked(CHK-1644); states:blocked(CHK-1645); semantics_accessibility:blocked(CHK-1646); layout_content:blocked(CHK-1647); data_effects:blocked(CHK-1648); security_privacy:blocked(CHK-1649); performance_lifecycle:blocked(CHK-1650); maintainability_integration:passed(CHK-1651); behavior:passed(CHK-2005) |
| CMP-178 Domain chips and all-catalogue scope | DEF-033 / BP-033 | CMP-177 | web/assets/hero-explorer.js: #netlegend [data-hero-domain] / setDomain/paintLegend; variants: all or top four domain chips; active domain toggled off; all skills remain searchable | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1610); behavior:blocked(CHK-1652); states:blocked(CHK-1653); semantics_accessibility:blocked(CHK-1654); layout_content:blocked(CHK-1655); data_effects:blocked(CHK-1656); security_privacy:blocked(CHK-1657); performance_lifecycle:blocked(CHK-1658); maintainability_integration:passed(CHK-1659); behavior:passed(CHK-2006) |
| CMP-179 Search expansion | DEF-033 / BP-033 | CMP-177 | web/assets/hero-explorer.js: #hero-explorer .hero-search-panel > summary; variants: collapsed/expanded; domain-specific summary text | investigate / TASK-039, TASK-040 | behavior:blocked(CHK-1660); states:blocked(CHK-1661); semantics_accessibility:blocked(CHK-1662); layout_content:blocked(CHK-1663); data_effects:blocked(CHK-1664); security_privacy:blocked(CHK-1665); performance_lifecycle:blocked(CHK-1666); maintainability_integration:passed(CHK-1667) |
| CMP-180 Skill search field and label | DEF-033 / BP-033 | CMP-179 | web/assets/hero-explorer.js: #hero-skill-search / input/key handlers; variants: blank/matches/no matches; ArrowDown/Enter/Escape; disabled empty catalogue | investigate / TASK-039, TASK-040 | states:passed(CHK-1615); behavior:blocked(CHK-1668); states:blocked(CHK-1669); semantics_accessibility:blocked(CHK-1670); layout_content:blocked(CHK-1671); data_effects:blocked(CHK-1672); security_privacy:blocked(CHK-1673); performance_lifecycle:blocked(CHK-1674); maintainability_integration:passed(CHK-1675); behavior:passed(CHK-2007) |
| CMP-181 Search-result row template | DEF-033 / BP-033 | CMP-179 | web/assets/hero-explorer.js: #hero-skill-results [data-hero-skill] / select; variants: up to eight visible rows with full match count; keyboard cycling and selection | investigate / TASK-039, TASK-040 | states:passed(CHK-1616); behavior:blocked(CHK-1676); states:blocked(CHK-1677); semantics_accessibility:blocked(CHK-1678); layout_content:blocked(CHK-1679); data_effects:blocked(CHK-1680); security_privacy:blocked(CHK-1681); performance_lifecycle:blocked(CHK-1682); maintainability_integration:passed(CHK-1683); behavior:passed(CHK-2008) |
| CMP-182 Search match count and empty feedback | DEF-033 / BP-033 | CMP-179 | web/assets/hero-explorer.js: .hero-search-status / search; variants: hidden/positive/full count/no match; no false zero during loading | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1611); behavior:blocked(CHK-1684); states:blocked(CHK-1685); semantics_accessibility:blocked(CHK-1686); layout_content:blocked(CHK-1687); data_effects:blocked(CHK-1688); security_privacy:blocked(CHK-1689); performance_lifecycle:blocked(CHK-1690); maintainability_integration:passed(CHK-1691) |
| CMP-183 Selected declaration card | DEF-033 / BP-033 | CMP-177 | web/assets/hero-explorer.js: .hero-skill-card / select/closeSelection; variants: hidden/selected/loading/declaration/error/timeout; title focus | investigate / TASK-039, TASK-040 | states:passed(CHK-1617); behavior:blocked(CHK-1692); states:blocked(CHK-1693); semantics_accessibility:blocked(CHK-1694); layout_content:blocked(CHK-1695); data_effects:blocked(CHK-1696); security_privacy:blocked(CHK-1697); performance_lifecycle:blocked(CHK-1698); maintainability_integration:passed(CHK-1699); behavior:passed(CHK-2009) |
| CMP-184 Selected-card close action | DEF-033 / BP-033 | CMP-183 | web/assets/hero-explorer.js: .hero-skill-close / closeSelection; variants: close while pending/ready and restore only owned focus | investigate / TASK-039, TASK-040 | states:passed(CHK-1618); behavior:blocked(CHK-1700); states:blocked(CHK-1701); semantics_accessibility:blocked(CHK-1702); layout_content:blocked(CHK-1703); data_effects:blocked(CHK-1704); security_privacy:blocked(CHK-1705); performance_lifecycle:blocked(CHK-1706); maintainability_integration:passed(CHK-1707) |
| CMP-185 Selected skill source, purpose and typed relation summary | DEF-033 / BP-033 | CMP-183 | web/assets/hero-explorer.js: .hero-skill-source/.hero-skill-purpose/.hero-skill-relations / loadDetails; variants: current seed/community/evolved declaration; loading/purpose/error; full incident edge counts | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1612); behavior:blocked(CHK-1708); states:blocked(CHK-1709); semantics_accessibility:blocked(CHK-1710); layout_content:blocked(CHK-1711); data_effects:blocked(CHK-1712); security_privacy:blocked(CHK-1713); performance_lifecycle:blocked(CHK-1714); maintainability_integration:passed(CHK-1715); behavior:passed(CHK-2010) |
| CMP-186 Selected-card capability passport action | DEF-029 / BP-029 | CMP-183 | web/assets/hero-explorer.js: .hero-skill-actions [data-capability-skill] → Product.inspectPassport; variants: current declaration with no invented run context; native dialog return | investigate / TASK-039, TASK-040 | states:passed(CHK-1619); behavior:blocked(CHK-1716); states:blocked(CHK-1717); semantics_accessibility:blocked(CHK-1718); layout_content:blocked(CHK-1719); data_effects:blocked(CHK-1720); security_privacy:blocked(CHK-1721); performance_lifecycle:blocked(CHK-1722); maintainability_integration:passed(CHK-1723); behavior:passed(CHK-2011) |
| CMP-187 Selected-purpose retry action | DEF-033 / BP-033 | CMP-183 | web/assets/hero-explorer.js: .hero-skill-actions retry / loadDetails; variants: hidden/purpose-error/timeout/retry; old reply discarded | investigate / TASK-039, TASK-040 | states:passed(CHK-1620); behavior:blocked(CHK-1724); states:blocked(CHK-1725); semantics_accessibility:blocked(CHK-1726); layout_content:blocked(CHK-1727); data_effects:blocked(CHK-1728); security_privacy:blocked(CHK-1729); performance_lifecycle:blocked(CHK-1730); maintainability_integration:passed(CHK-1731) |
| CMP-188 Selected-card full graph link | DEF-033 / BP-033 | CMP-183 | web/assets/hero-explorer.js: .hero-skill-actions a / updateLink; variants: safe selected skill+domain context and usable no-run exploration | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1613); behavior:blocked(CHK-1732); states:blocked(CHK-1733); semantics_accessibility:blocked(CHK-1734); layout_content:blocked(CHK-1735); data_effects:blocked(CHK-1736); security_privacy:blocked(CHK-1737); performance_lifecycle:blocked(CHK-1738); maintainability_integration:passed(CHK-1739) |
| CMP-189 Catalogue read retry action | DEF-033 / BP-033 | CMP-177 | web/assets/hero-explorer.js: .hero-catalogue-retry / options.reload; variants: hidden/failed/pending/ready; repeated retry disabled | investigate / TASK-039, TASK-040 | states:passed(CHK-1621); behavior:blocked(CHK-1740); states:blocked(CHK-1741); semantics_accessibility:blocked(CHK-1742); layout_content:blocked(CHK-1743); data_effects:blocked(CHK-1744); security_privacy:blocked(CHK-1745); performance_lifecycle:blocked(CHK-1746); maintainability_integration:passed(CHK-1747) |
| CMP-190 Original hero full-graph link integration | DEF-033 / BP-033 | CMP-177 | web/assets/hero-explorer.js: .sphere-hero-controls a / HeroExplorer graphLink updateLink; variants: original link retained; selected skill/domain reflected; restored all scope | investigate / TASK-039, TASK-040 | behavior:passed(CHK-1614); behavior:blocked(CHK-1748); states:blocked(CHK-1749); semantics_accessibility:blocked(CHK-1750); layout_content:blocked(CHK-1751); data_effects:blocked(CHK-1752); security_privacy:blocked(CHK-1753); performance_lifecycle:blocked(CHK-1754); maintainability_integration:passed(CHK-1755) |
| CMP-202 Progressive skill selection to execution evidence | DEF-002 / BP-002 | CMP-021 | web/assets/product.js: selectionHTML/skillTraceHTML; #show-routing .route-evidence > summary; variants: native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA | investigate / TASK-039, TASK-040 | security_privacy:passed(CHK-1637); behavior:blocked(CHK-1844); states:blocked(CHK-1845); semantics_accessibility:blocked(CHK-1846); layout_content:blocked(CHK-1847); data_effects:blocked(CHK-1848); security_privacy:blocked(CHK-1849); performance_lifecycle:blocked(CHK-1850); maintainability_integration:passed(CHK-1851); data_effects:passed(CHK-2020) |
| CMP-203 Associated-step execution and review action | DEF-030 / BP-030 | CMP-202 | web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent #show-routing; variants: one original idx per actual matched skill step; no fabricated button for recommended-only skill | investigate / TASK-039, TASK-040 | security_privacy:passed(CHK-1638); behavior:blocked(CHK-1852); states:blocked(CHK-1853); semantics_accessibility:blocked(CHK-1854); layout_content:blocked(CHK-1855); data_effects:blocked(CHK-1856); security_privacy:blocked(CHK-1857); performance_lifecycle:blocked(CHK-1858); maintainability_integration:passed(CHK-1859); data_effects:passed(CHK-2021) |
| CMP-204 Run-associated current skill passport | DEF-029 / BP-029 | CMP-202 | web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent #show-routing; variants: parallel current/history read; partial failures, wrong run id and closed/stale responses | investigate / TASK-039, TASK-040 | data_effects:passed(CHK-1643); behavior:blocked(CHK-1860); states:blocked(CHK-1861); semantics_accessibility:blocked(CHK-1862); layout_content:blocked(CHK-1863); data_effects:blocked(CHK-1864); security_privacy:blocked(CHK-1865); performance_lifecycle:blocked(CHK-1866); maintainability_integration:passed(CHK-1867); data_effects:passed(CHK-2022) |
| CMP-205 Run/skill/step sphere location link | DEF-002 / BP-002 | CMP-202 | web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent #show-routing; variants: safe encoded local path; preserved noncontiguous idx; no implicit last_run | investigate / TASK-039, TASK-040 | security_privacy:passed(CHK-1639); behavior:blocked(CHK-1868); states:blocked(CHK-1869); semantics_accessibility:blocked(CHK-1870); layout_content:blocked(CHK-1871); data_effects:blocked(CHK-1872); security_privacy:blocked(CHK-1873); performance_lifecycle:blocked(CHK-1874); maintainability_integration:passed(CHK-1875); data_effects:passed(CHK-2023) |
| CMP-206 Explicit file/transition recheck action | DEF-028 / BP-028 | CMP-202 | web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent #show-routing; variants: explicit read-only evidence rehash; no reward/write; stale dialog isolation | investigate / TASK-039, TASK-040 | security_privacy:passed(CHK-1640); behavior:blocked(CHK-1876); states:blocked(CHK-1877); semantics_accessibility:blocked(CHK-1878); layout_content:blocked(CHK-1879); data_effects:blocked(CHK-1880); security_privacy:blocked(CHK-1881); performance_lifecycle:blocked(CHK-1882); maintainability_integration:passed(CHK-1883); data_effects:passed(CHK-2024) |

## Scenarios

| Scenario | Current status | Scope and expected result | Evidence / findings | History |
|---|---|---|---|---|
| SCN-001 Executive briefing browser journey and recovery | blocked | CMP-001, CMP-002, CMP-003, CMP-004, CMP-005, CMP-006, CMP-007, CMP-008, CMP-009, CMP-010, CMP-011, CMP-012, CMP-013, CMP-014, CMP-015, CMP-016, CMP-017, CMP-018, CMP-019, CMP-020, CMP-021, CMP-022, CMP-023, CMP-024, CMP-025, CMP-026, CMP-027, CMP-028, CMP-029, CMP-030, CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160, CMP-177, CMP-178, CMP-179, CMP-180, CMP-181, CMP-182, CMP-183, CMP-184, CMP-185, CMP-186, CMP-187, CMP-188, CMP-189, CMP-190, CMP-202, CMP-203, CMP-204, CMP-205, CMP-206; The user can complete Executive briefing without lost state, stale overwrite or duplicate side effects., All registered controls have accessible names and usable focus; dialogs close and restore focus; visual hierarchy/background stay coherent., Unknown/blocked/missing evaluation is distinguished from pass/zero/reward; real data/source links remain available. | FND-009, FND-010, FND-011, FND-013, FND-014 | [] |
| SCN-017 Token clear/close race — bounded Node regression | passed | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148; Candidate validation has a generation and AbortController; only the latest still-open dialog may commit., All assertions in tools/frontend_resilience_check.js: tokenRace pass. | EV-019, FND-001 | [] |
| SCN-021 Stored sessions trust cached rendering and dynamic inline handlers — bounded Node regression | passed | CMP-019, CMP-038; Whitelist plain session/turn fields; reconstruct remote run content; escaped data attributes and native buttons replace interpolated onclick arguments., All assertions in tools/frontend_resilience_check.js: storedHistory pass. | EV-019, FND-005 | [] |
| SCN-023 State contract events need truthful separation from reward — bounded Node regression | passed | CMP-014; Show declaration compatibility separately from observed checks; unknown blocks remain unknown; no judge/evolution is synthesized., All assertions in tools/showcase_check.js: contracts pass. | EV-019, FND-007 | [] |
| SCN-025 Controlled Product DOM: resource manifest | passed | CMP-153; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-026 Controlled Product DOM: verified resource file | passed | CMP-154; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-027 Controlled Product DOM: evidence export | passed | CMP-155; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-028 Controlled Product DOM: run value | passed | CMP-156; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-029 Controlled Product DOM: capability report | passed | CMP-157; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-030 Controlled Product DOM: skill passport | passed | CMP-158; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-031 Controlled Product DOM: step details | passed | CMP-159; Only the current still-open request changes the dialog., The original request does not revive or overwrite the latest view. | EV-022, FND-015 | [] |
| SCN-032 Controlled Product DOM: artifact identity and bounded source preview | passed | CMP-160; Run and file identity are retained, old streams/readers do not mutate new preview., HTML is text; preview bounds and reader cancellation hold. | EV-022, FND-015 | [] |
| SCN-033 Controlled Product DOM: resource integrity rejection | passed | CMP-154; Error explains failed verification; unverified content never receives a verified download action. | EV-022, FND-015 | [] |
| SCN-034 Controlled Product DOM: hostile content and unknown/failed state semantics | passed | CMP-153, CMP-154, CMP-157, CMP-159; Payloads remain escaped text. Unknown and failed remain distinct; declarations do not create reward. | EV-022, FND-015 | [] |
| SCN-035 Controlled Product DOM: capability numeric-field escaping | passed | CMP-157; All count values remain escaped data rather than interpreted HTML. | EV-022, FND-015 | [] |
| SCN-036 Controlled Product DOM: missing step and delegated keyboard handling | passed | CMP-159; One controller request starts; missing step settles into an explicit error/empty result. Native keyboard/focus remains a separate browser check. | EV-022, FND-015 | [] |
| SCN-037 IAB initial viewport home 1440×900 | passed | CMP-001; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-023 | [] |
| SCN-043 IAB initial viewport home 390×844 | passed | CMP-001; No horizontal overflow in this initial viewport., Record the actually observed screen; do not treat it as full-route interaction acceptance. | EV-029 | [] |
| SCN-049 IAB Background continuity and corrected mobile uniq-three width in observed conditions | passed | CMP-026, CMP-001; The recorded interaction yields the focus/rotation/replay/layout result stated in the observation., No generalization to untested controls, zoom, OS settings or production. | EV-035, FND-017 | [] |
| SCN-050 IAB Recorded seven-stage replay/pause/End | passed | CMP-007, CMP-015; The recorded interaction yields the focus/rotation/replay/layout result stated in the observation., No generalization to untested controls, zoom, OS settings or production. | EV-036 | [] |
| SCN-053 Final local regression: task/cross-turn inputs are not new deliverables | passed | CMP-156; Only the CSV output contributes to new deliverable count., Input evidence and produced deliverables remain semantically distinct. | EV-046, FND-018 | [] |
| SCN-054 Shared frontier IIFE navigation, native-control keyboard and return focus (controlled DOM only) | passed | CMP-161; One trigger/dialog is created; initial, trapped and return focus follow the controlled DOM contract. | EV-051 | [] |
| SCN-055 Frontier async ownership after close, re-entry and pagehide (controlled DOM only) | passed | CMP-161; Aborted or older requests cannot overwrite a newer or closed session; pagehide closes the pending dialog. | EV-051 | [] |
| SCN-056 Frontier read errors, timeout and explicit recovery (controlled DOM only) | passed | CMP-161; Independent scenario execution remains available after lab failure; invalid data is not shown as success; 45-second timeout has actionable recovery. | EV-051 | [] |
| SCN-057 Frontier POST deduplication, unsafe-data rendering and truthful metrics (controlled DOM only) | passed | CMP-161; Only one POST is sent; only scenario_id is submitted; text is never executed as markup; POST is not auto-retried; costs and independently verified results stay distinct. | EV-051 | [] |
| SCN-058 Frontier real report shape and delegated snapshot entry (controlled DOM only) | passed | CMP-161; Opening is read-only; recorded state checks render from their real schema; null independent checks are explicitly unavailable. | EV-051 | [] |
| SCN-059 Frontier fixed same-origin evidence download lifecycle (controlled DOM only) | passed | CMP-161; Evidence is a bounded authenticated read; duplicate downloads and stale completion are suppressed; arbitrary external report URLs are not accepted. | EV-051 | [] |
| SCN-060 Frontier disabled-submit focus recovery and compact results (controlled DOM only) | passed | CMP-161; Focus recovery restores the submit only when lost; deliberate internal focus is preserved; row changes, new facts and 11/11 oracle checks render accurately. | EV-051 | [] |
| SCN-061 Current repair recheck: Frontier v7 dialog ignored centered modal margin | passed | CMP-161; The bounded native modal should have an even desktop inset and preserve internal scrolling. | EV-050, EV-051, EV-054, FND-019 | [{"baseline": "v20261012.7", "status": "failed", "evidence_ids": ["EV-052", "EV-053"], "finding_ids": ["FND-019"]}] |
| SCN-062 Current repair recheck: Global footer styles overrode frontier modal footer | passed | CMP-161; The modal footer should use its own 13px/30px spacing and adapt to the mobile 12px/18px rule. | EV-050, EV-051, EV-054, FND-020 | [{"baseline": "v20261012.7", "status": "failed", "evidence_ids": ["EV-052", "EV-053"], "finding_ids": ["FND-020"]}] |
| SCN-063 Current repair recheck: Disabled frontier submit left native focus on BODY | passed | CMP-161; After result/error, recover lost focus to the enabled submit while preserving a deliberate focus move within the dialog. | EV-050, EV-051, EV-054, FND-021 | [{"baseline": "v20261012.7", "status": "failed", "evidence_ids": ["EV-053"], "finding_ids": ["FND-021"]}] |
| SCN-064 Final full frontier integration on / | blocked | CMP-161; Only the current session renders; fixed public POST and accurate scoped oracle results remain distinct from the production workflow., Parent layout/background, internal scrolling and accessible control/feedback behavior remain usable; actual failures have recovery. |  | [] |
| SCN-080 Native centered modal and mobile width repair | passed | CMP-161; v8 desktop rect x189.8 y16 width1050 h868; mobile client=scroll373 at390px; v9 same CSS and no overflow. | EV-054 | [] |
| SCN-081 Native footer cascade repair | passed | CMP-161; v8 computed footer margin0 padding13px30px; inspected desktop/mobile screenshots; final v9 CSS unchanged. | EV-054 | [] |
| SCN-082 Native POST and Escape focus repair | passed | CMP-161; v8/v9 success restores submit focus; v8 Escape restores opener; v9 six document entries open and Escape returns opener. | EV-054 | [] |
| SCN-083 Final native research results and shared entries | passed | CMP-161; v9 combined succeeds11/11; threshold rejected5/11 with Chinese labels; six document entries and public replay observed, without claiming full journeys. | EV-054 | [] |
| SCN-084 Hero explorer native domain/search/selected-card acceptance (bounded) | blocked | CMP-177, CMP-178, CMP-179, CMP-180, CMP-181, CMP-182, CMP-183, CMP-184, CMP-185, CMP-186, CMP-187, CMP-188, CMP-189, CMP-190; Domain and full counts agree with catalogue; whole catalogue remains searchable; no stale/identity-mismatched purpose., Card/keyboard/close/native passport focus and viewport layout remain usable in the measured states; declaration is never presented as executed certification. |  | [] |
| SCN-086 Shared progressive skill trace and paired passport native integration (bounded) | blocked | CMP-202, CMP-203, CMP-204, CMP-205, CMP-206, CMP-207, CMP-208, CMP-209, CMP-210, CMP-211, CMP-212, CMP-213, CMP-214, CMP-215, CMP-216, CMP-217, CMP-218, CMP-219, CMP-220, CMP-221, CMP-158, CMP-159; Actual matched steps and recorded artifacts/checks appear; unexecuted recommendations create no execution facts., Current declaration cannot replace historical SHA; partial failure is explicit and retains readable evidence; same idx in another run cannot focus the wrong current inspector., Parent route and selected skill/original idx survive navigation; no network/reward writes are implied. |  | [] |
| SCN-088 Hero catalogue scope, domain and source-declaration truth (controlled logic only) | passed | CMP-177, CMP-178, CMP-182, CMP-185, CMP-188, CMP-190; Real node counts, exact selected name/domain and incident typed relations remain catalogue-derived; imported provenance never certifies code. | EV-056 | [] |
| SCN-089 Hero keyboard entry, detail identity and recovery (controlled logic only) | passed | CMP-180, CMP-181, CMP-183, CMP-184, CMP-186, CMP-187, CMP-189; Controlled handlers preserve selected identity/focus fallback; error/retry does not accept stale or wrong skill response. Native focus itself remains unmeasured. | EV-056 | [] |
| SCN-090 Hero DAG suspension, filter cycles and teardown (controlled logic only) | passed | CMP-177; No duplicate scene is introduced; pending purpose generation/timer/listeners clear; suspended hero cannot steal DAG selection. | EV-056 | [] |
| SCN-094 Product encoded local context and truthful skill trace (controlled logic only) | passed | CMP-202, CMP-203, CMP-205, CMP-206; Links remain fixed same-origin paths with separate encoded fields; invalid idx is rejected; no run means /runs rather than stale last_run; trace uses actual steps/versions/checks without fabricating independent evidence. | EV-058 | [] |
| SCN-095 Product paired passport identity and cross-run focus (controlled logic only) | passed | CMP-158, CMP-159, CMP-204; Current/history promises cannot mix epochs or wrong run ids; either side can fail independently; same-run step focus dismisses covering dialog, other-run same idx reads its own evidence, invalid idx performs no request. | EV-058 | [] |
| SCN-097 Actual hero catalogue domain/search and mobile selected declaration subset | passed | CMP-177, CMP-178, CMP-180, CMP-181, CMP-183, CMP-185, CMP-186; Exact catalogue scope/search/declared-purpose observations are supported; no skill execution certification is inferred., Native measured mobile selected card fits; only recorded desktop passport/Escape focus sequence is admitted. | EV-061 | [] |
| SCN-099 Actual homepage skill trace, paired passport and step modal subset | passed | CMP-202, CMP-203, CMP-204, CMP-205, CMP-206; Only actual homepage context is supported; current declaration and historical execution stay separately labelled., Actual action/checks/artifacts and safe graph run/skill/idx link are retained; not all four parent contexts are accepted. | EV-061 | [] |

## Instance plans

### CMP-001 Page shell/navigation/status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing.

**Instance changes:** Keep route / and locator header / nav / main behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Page shell/navigation/status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-002 Connection settings and toast

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing.

**Instance changes:** Keep route / and locator UI.bootstrap / #ui-connection-dialog behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Connection settings and toast remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-003 Service/key/library status

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Service/key/library status is missing.

**Instance changes:** Keep route / and locator dot-srv / key-txt / lib-n behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Service/key/library status remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-004 Hero counts and chapter navigation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Hero counts and chapter navigation is missing.

**Instance changes:** Keep route / and locator top / hm-skills / hm-edges / hm-domains behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Hero counts and chapter navigation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-005 Hero sphere and tooltip

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Hero sphere and tooltip is missing.

**Instance changes:** Keep route / and locator netcv / nettip behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Hero sphere and tooltip remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-006 Hero rotation button

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Hero rotation button is missing.

**Instance changes:** Keep route / and locator hero-rotate behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Hero rotation button remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-007 Seven-phase stage and rail

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Seven-phase stage and rail is missing.

**Instance changes:** Keep route / and locator show-stage / show-rail behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Seven-phase stage and rail remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-008 Follow-live action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Follow-live action is missing.

**Instance changes:** Keep route / and locator show-follow behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Follow-live action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-009 Cancel action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Cancel action is missing.

**Instance changes:** Keep route / and locator show-cancel behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Cancel action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-010 Replay last run action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Replay last run action is missing.

**Instance changes:** Keep route / and locator show-replay behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Replay last run action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-011 Presentation action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Presentation action is missing.

**Instance changes:** Keep route / and locator show-present behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Presentation action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-012 Question collapse control

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Question collapse control is missing.

**Instance changes:** Keep route / and locator show-question-toggle behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Question collapse control remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-013 Task DAG and step buttons

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Task DAG and step buttons is missing.

**Instance changes:** Keep route / and locator show-network / [data-show-step] behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Task DAG and step buttons remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-014 Operation, activity and facts

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Operation, activity and facts is missing.

**Instance changes:** Keep route / and locator show-operation / show-activity / show-facts behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Operation, activity and facts remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-015 Replay pause/seek/speed controls

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Replay pause/seek/speed controls is missing.

**Instance changes:** Keep route / and locator show-pause / show-seek / show-speed behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Replay pause/seek/speed controls remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-016 Question input

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Question input is missing.

**Instance changes:** Keep route / and locator task behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Question input remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-017 Create-run action

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Create-run action is missing.

**Instance changes:** Keep route / and locator run behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Create-run action remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-018 Scenario/demo prompt buttons

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Scenario/demo prompt buttons is missing.

**Instance changes:** Keep route / and locator chips / [data-i] behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Scenario/demo prompt buttons remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-019 Saved session buttons

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Saved session buttons is missing.

**Instance changes:** Keep route / and locator ws-list / [data-session] behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Saved session buttons remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-020 Saved messages and detailed results

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Saved messages and detailed results is missing.

**Instance changes:** Keep route / and locator ws-msgs behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Saved messages and detailed results remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-021 Routing/impact/answer/file result regions

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Routing/impact/answer/file result regions is missing.

**Instance changes:** Keep route / and locator show-routing / show-impact / show-answer-body / show-files-body behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Routing/impact/answer/file result regions remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-022 Run and evidence navigation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Run and evidence navigation is missing.

**Instance changes:** Keep route / and locator show-run-link / show-evidence-link behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Run and evidence navigation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-023 Step preview dialog and close

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Step preview dialog and close is missing.

**Instance changes:** Keep route / and locator show-preview / show-preview-close behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Step preview dialog and close remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-024 Legacy artifact/skill preview dialog

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Legacy artifact/skill preview dialog is missing.

**Instance changes:** Keep route / and locator openLayer / [data-legacy-file] / [data-raw-skill] behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Legacy artifact/skill preview dialog remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-025 Legacy seven-stage timeline

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Legacy seven-stage timeline is missing.

**Instance changes:** Keep route / and locator demo-seven / .tl-item behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Legacy seven-stage timeline remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-026 Core problem/framework explanation

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Core problem/framework explanation is missing.

**Instance changes:** Keep route / and locator s1 / s2 / ar / arg behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Core problem/framework explanation remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001, SCN-049

### CMP-027 Product screenshots and capabilities

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Product screenshots and capabilities is missing.

**Instance changes:** Keep route / and locator sproduct / s4 behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Product screenshots and capabilities remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-028 Recorded run catalogue

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Recorded run catalogue is missing.

**Instance changes:** Keep route / and locator runlist / loadRunCenter behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Recorded run catalogue remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-029 Evidence/comparison controls and panel

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for Evidence/comparison controls and panel is missing.

**Instance changes:** Keep route / and locator evpanel / cmpbox behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** Evidence/comparison controls and panel remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-030 S1 delivery / footer

**Rationale:** Read source, preserve this implementation; runtime-specific evidence for S1 delivery / footer is missing.

**Instance changes:** Keep route / and locator s5 / s6 behavior; verify/fix only reproduced failures after browser exercise.

**Acceptance criteria:** S1 delivery / footer remains usable with expected state/data/focus at this route., Verify the registered conditional templates and long/untrusted data boundaries.

**Regression scenario ids:** SCN-001

### CMP-153 Conditional Product resource manifest dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-skill-resources identity and trigger ownership; exercise manifest loading/ready/error/closed in actual IAB.

**Acceptance criteria:** Run-specific resource manifest cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-025, SCN-034

### CMP-154 Conditional Product verified resource file dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-resource-read identity and trigger ownership; exercise digest verifying/mismatch/oversized/text/binary/closed in actual IAB.

**Acceptance criteria:** Run-specific verified resource file cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-026, SCN-033

### CMP-155 Conditional Product evidence export dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-evidence-export identity and trigger ownership; exercise evidence loading/ready/download/error/closed in actual IAB.

**Acceptance criteria:** Run-specific evidence export cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-027

### CMP-156 Conditional Product run value dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-run-value identity and trigger ownership; exercise run loading/value ready/error/closed in actual IAB.

**Acceptance criteria:** Run-specific run value cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-028, SCN-053

### CMP-157 Conditional Product capability report dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-capability-report identity and trigger ownership; exercise report loading/unknown/failed/ready/download/closed in actual IAB.

**Acceptance criteria:** Run-specific capability report cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-029, SCN-035

### CMP-158 Conditional Product skill passport dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-capability-skill identity and trigger ownership; exercise declaration loading/ready/unknown/error/closed in actual IAB.

**Acceptance criteria:** Run-specific skill passport cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-030, SCN-086

### CMP-159 Conditional Product step details dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-kernel-step identity and trigger ownership; exercise step loading/missing/ready/error/closed in actual IAB.

**Acceptance criteria:** Run-specific step details cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-031, SCN-036, SCN-086

### CMP-160 Conditional Product artifact preview dialog

**Rationale:** Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence.

**Instance changes:** Preserve data-artifact-preview identity and trigger ownership; exercise run/file loading/text/image/pdf/unknown/large/error/closed in actual IAB.

**Acceptance criteria:** Run-specific artifact preview cannot be overwritten by a stale request., Native dialog closes/returns focus and stays usable at the measured viewport.

**Regression scenario ids:** SCN-001, SCN-032

### CMP-161 Capability frontier experiment launcher/dialog — Executive briefing

**Rationale:** Shared logic/source inspected; / has distinct navigation/parent layout and requires its own native browser acceptance.

**Instance changes:** Preserve original / task/navigation/background; keep one frontier trigger and validate scoped modal in this parent., Verify independent lab/scenario failures, public POST lifecycle, keyboard return target and source-versus-projection digest labels.

**Acceptance criteria:** / preserves its original task while the frontier surface is operable and scrollable., Unknown, declared reachability, observed outcome and reward stay separate; closing does not resurrect stale results.

**Regression scenario ids:** SCN-064

### CMP-177 Hero capability explorer region and catalogue scope status

**Rationale:** Actual source and shared logic were reviewed; native Hero capability explorer region and catalogue scope status acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/briefing.html #hero-explorer; hero-explorer.js mount/updateScope/failed with variants catalogue loading/ready/empty/error/retry; current data count; DAG suspended/resumed., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Hero capability explorer region and catalogue scope status is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-178 Domain chips and all-catalogue scope

**Rationale:** Actual source and shared logic were reviewed; native Domain chips and all-catalogue scope acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: #netlegend [data-hero-domain] / setDomain/paintLegend with variants all or top four domain chips; active domain toggled off; all skills remain searchable., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Domain chips and all-catalogue scope is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-179 Search expansion

**Rationale:** Actual source and shared logic were reviewed; native Search expansion acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: #hero-explorer .hero-search-panel > summary with variants collapsed/expanded; domain-specific summary text., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Search expansion is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-180 Skill search field and label

**Rationale:** Actual source and shared logic were reviewed; native Skill search field and label acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: #hero-skill-search / input/key handlers with variants blank/matches/no matches; ArrowDown/Enter/Escape; disabled empty catalogue., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Skill search field and label is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-181 Search-result row template

**Rationale:** Actual source and shared logic were reviewed; native Search-result row template acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: #hero-skill-results [data-hero-skill] / select with variants up to eight visible rows with full match count; keyboard cycling and selection., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Search-result row template is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-182 Search match count and empty feedback

**Rationale:** Actual source and shared logic were reviewed; native Search match count and empty feedback acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-search-status / search with variants hidden/positive/full count/no match; no false zero during loading., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Search match count and empty feedback is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-183 Selected declaration card

**Rationale:** Actual source and shared logic were reviewed; native Selected declaration card acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-skill-card / select/closeSelection with variants hidden/selected/loading/declaration/error/timeout; title focus., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected declaration card is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-184 Selected-card close action

**Rationale:** Actual source and shared logic were reviewed; native Selected-card close action acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-skill-close / closeSelection with variants close while pending/ready and restore only owned focus., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected-card close action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-185 Selected skill source, purpose and typed relation summary

**Rationale:** Actual source and shared logic were reviewed; native Selected skill source, purpose and typed relation summary acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-skill-source/.hero-skill-purpose/.hero-skill-relations / loadDetails with variants current seed/community/evolved declaration; loading/purpose/error; full incident edge counts., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected skill source, purpose and typed relation summary is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-186 Selected-card capability passport action

**Rationale:** Actual source and shared logic were reviewed; native Selected-card capability passport action acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-skill-actions [data-capability-skill] → Product.inspectPassport with variants current declaration with no invented run context; native dialog return., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected-card capability passport action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001, SCN-097

### CMP-187 Selected-purpose retry action

**Rationale:** Actual source and shared logic were reviewed; native Selected-purpose retry action acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-skill-actions retry / loadDetails with variants hidden/purpose-error/timeout/retry; old reply discarded., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected-purpose retry action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-188 Selected-card full graph link

**Rationale:** Actual source and shared logic were reviewed; native Selected-card full graph link acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-skill-actions a / updateLink with variants safe selected skill+domain context and usable no-run exploration., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Selected-card full graph link is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-189 Catalogue read retry action

**Rationale:** Actual source and shared logic were reviewed; native Catalogue read retry action acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .hero-catalogue-retry / options.reload with variants hidden/failed/pending/ready; repeated retry disabled., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Catalogue read retry action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-190 Original hero full-graph link integration

**Rationale:** Actual source and shared logic were reviewed; native Original hero full-graph link integration acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/hero-explorer.js: .sphere-hero-controls a / HeroExplorer graphLink updateLink with variants original link retained; selected skill/domain reflected; restored all scope., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Original hero full-graph link integration is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-084, SCN-001

### CMP-202 Progressive skill selection to execution evidence

**Rationale:** Actual source and shared logic were reviewed; native Progressive skill selection to execution evidence acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML/skillTraceHTML; #show-routing .route-evidence > summary with variants native disclosure for recommended/adopted/executed/failed/no matching steps; original idx and historical SHA., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Progressive skill selection to execution evidence is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-001, SCN-099

### CMP-203 Associated-step execution and review action

**Rationale:** Actual source and shared logic were reviewed; native Associated-step execution and review action acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-kernel-step] → focusStep; parent #show-routing with variants one original idx per actual matched skill step; no fabricated button for recommended-only skill., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Associated-step execution and review action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-001, SCN-099

### CMP-204 Run-associated current skill passport

**Rationale:** Actual source and shared logic were reviewed; native Run-associated current skill passport acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: selectionHTML [data-capability-skill][data-run][data-step] → inspectPassport; parent #show-routing with variants parallel current/history read; partial failures, wrong run id and closed/stale responses., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run-associated current skill passport is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-001, SCN-099

### CMP-205 Run/skill/step sphere location link

**Rationale:** Actual source and shared logic were reviewed; native Run/skill/step sphere location link acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML graphURL → /graph?run=&skill=&step=; parent #show-routing with variants safe encoded local path; preserved noncontiguous idx; no implicit last_run., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Run/skill/step sphere location link is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-001, SCN-099

### CMP-206 Explicit file/transition recheck action

**Rationale:** Actual source and shared logic were reviewed; native Explicit file/transition recheck action acceptance in PAGE-001 is not yet merged. Do not treat the shared harness as an instance browser pass.

**Instance changes:** Keep web/assets/product.js: skillTraceHTML [data-capability-report] → inspectCapabilities; parent #show-routing with variants explicit read-only evidence rehash; no reward/write; stale dialog isolation., Verify only this actual parent/context plus original full-view scenario, preserving existing seven stages/background/globe and recorded evidence boundaries.

**Acceptance criteria:** Explicit file/transition recheck action is usable in this exact parent with native action/result/focus/layout evidence., Recorded/current declarations remain distinct; no artificial execution/unknown-to-pass/causal reward claim is introduced.

**Regression scenario ids:** SCN-086, SCN-001, SCN-099
