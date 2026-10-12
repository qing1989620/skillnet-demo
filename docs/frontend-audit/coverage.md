# 前端审查覆盖索引

项目：SkillNet · S1 ecosystem frontend robustness

目标：D:\qing_zhuomian_\开发区\skillnet\skillnet-demo

访问范围：source_runtime；发现状态：limited

> 本文件由台账生成。结构校验不验证证据真实性，也不等于产品认证。

## 覆盖结论

- schema_valid: True
- audit_coverage_closed: False
- plan_complete: True
- production_gates_satisfied: False

## 分母与状态

~~~json
{
  "pages_in_scope": 16,
  "pages_excluded": 0,
  "definitions": 32,
  "instances_in_scope": 176,
  "checks": {
    "blocked": 1316,
    "passed": 292
  },
  "scenarios": {
    "blocked": 32,
    "passed": 51
  },
  "findings": {
    "P1": 4,
    "P2": 16,
    "P3": 1
  },
  "component_plans": 176,
  "tasks": 38
}
~~~

## 页面与组件实例

| 页面 | 路由 | 组件实例 | 已通过 / 失败 / 阻塞 / 未检查 / 不适用 |
|---|---|---|---|
| PAGE-001 Executive briefing | / | 39 | 110 / 0 / 278 / 0 / 0 |
| PAGE-002 Conversation | /chat | 17 | 26 / 0 / 124 / 0 / 0 |
| PAGE-003 Mission centre | /runs#mission | 7 | 12 / 0 / 54 / 0 / 0 |
| PAGE-004 Run catalogue | /runs#runs | 9 | 10 / 0 / 68 / 0 / 0 |
| PAGE-005 Skill catalogue | /runs#skills | 8 | 10 / 0 / 61 / 0 / 0 |
| PAGE-006 Evaluation reports | /runs#eval | 4 | 6 / 0 / 33 / 0 / 0 |
| PAGE-007 Deployment information | /runs#system | 5 | 7 / 0 / 40 / 0 / 0 |
| PAGE-008 Run detail | /run?id=&lt;run-id&gt; | 16 | 20 / 0 / 117 / 0 / 0 |
| PAGE-009 Spherical skill network | /graph?run=&amp;skill=&amp;domain= | 22 | 31 / 0 / 159 / 0 / 0 |
| PAGE-010 Developer overview | /dashboard#overview | 6 | 9 / 0 / 47 / 0 / 0 |
| PAGE-011 Plan contrast | /dashboard#demo | 8 | 10 / 0 / 61 / 0 / 0 |
| PAGE-012 Developer skill inspector | /dashboard#skills?skill= | 8 | 9 / 0 / 61 / 0 / 0 |
| PAGE-013 Retrieval/routing laboratory | /dashboard#search | 8 | 9 / 0 / 61 / 0 / 0 |
| PAGE-014 Execution laboratory | /dashboard#run | 8 | 10 / 0 / 61 / 0 / 0 |
| PAGE-015 Historical results | /dashboard#results | 4 | 5 / 0 / 33 / 0 / 0 |
| PAGE-016 S1/export laboratory | /dashboard#adapters | 7 | 8 / 0 / 54 / 0 / 0 |

## 组件处置

| 实例 | 蓝图 | 处置 | 任务 | 理由 |
|---|---|---|---|---|
| CMP-001 | BP-005 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-002 | BP-001 | investigate | TASK-001, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-003 | BP-005 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Service/key/library status is missing. |
| CMP-004 | BP-005 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Hero counts and chapter navigation is missing. |
| CMP-005 | BP-003 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Hero sphere and tooltip is missing. |
| CMP-006 | BP-003 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Hero rotation button is missing. |
| CMP-007 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Seven-phase stage and rail is missing. |
| CMP-008 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Follow-live action is missing. |
| CMP-009 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Cancel action is missing. |
| CMP-010 | BP-004 | investigate | TASK-001, TASK-026 | Read source, preserve this implementation; runtime-specific evidence for Replay last run action is missing. |
| CMP-011 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Presentation action is missing. |
| CMP-012 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Question collapse control is missing. |
| CMP-013 | BP-004 | investigate | TASK-001, TASK-027 | Read source, preserve this implementation; runtime-specific evidence for Task DAG and step buttons is missing. |
| CMP-014 | BP-004 | investigate | TASK-001, TASK-023 | Read source, preserve this implementation; runtime-specific evidence for Operation, activity and facts is missing. |
| CMP-015 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Replay pause/seek/speed controls is missing. |
| CMP-016 | BP-006 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Question input is missing. |
| CMP-017 | BP-006 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Create-run action is missing. |
| CMP-018 | BP-006 | investigate | TASK-001, TASK-029 | Read source, preserve this implementation; runtime-specific evidence for Scenario/demo prompt buttons is missing. |
| CMP-019 | BP-006 | investigate | TASK-001, TASK-021 | Read source, preserve this implementation; runtime-specific evidence for Saved session buttons is missing. |
| CMP-020 | BP-006 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Saved messages and detailed results is missing. |
| CMP-021 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Routing/impact/answer/file result regions is missing. |
| CMP-022 | BP-004 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Run and evidence navigation is missing. |
| CMP-023 | BP-004 | investigate | TASK-001, TASK-026 | Read source, preserve this implementation; runtime-specific evidence for Step preview dialog and close is missing. |
| CMP-024 | BP-007 | investigate | TASK-001, TASK-025 | Read source, preserve this implementation; runtime-specific evidence for Legacy artifact/skill preview dialog is missing. |
| CMP-025 | BP-006 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Legacy seven-stage timeline is missing. |
| CMP-026 | BP-005 | investigate | TASK-001, TASK-030, TASK-033 | Read source, preserve this implementation; runtime-specific evidence for Core problem/framework explanation is missing. |
| CMP-027 | BP-005 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Product screenshots and capabilities is missing. |
| CMP-028 | BP-005 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Recorded run catalogue is missing. |
| CMP-029 | BP-005 | investigate | TASK-001 | Read source, preserve this implementation; runtime-specific evidence for Evidence/comparison controls and panel is missing. |
| CMP-030 | BP-005 | investigate | TASK-001, TASK-030 | Read source, preserve this implementation; runtime-specific evidence for S1 delivery / footer is missing. |
| CMP-031 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-032 | BP-001 | investigate | TASK-002, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-033 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Mobile history toggle is missing. |
| CMP-034 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for New session action is missing. |
| CMP-035 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Session list template is missing. |
| CMP-036 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Current session heading is missing. |
| CMP-037 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Last-run navigation is missing. |
| CMP-038 | BP-008 | investigate | TASK-002, TASK-021 | Read source, preserve this implementation; runtime-specific evidence for Message/turn template and hydration is missing. |
| CMP-039 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Per-turn phase indicators/live DAG is missing. |
| CMP-040 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Detail tabs and toggle is missing. |
| CMP-041 | BP-008 | investigate | TASK-002, TASK-022 | Read source, preserve this implementation; runtime-specific evidence for Step facts/checks/artifact links is missing. |
| CMP-042 | BP-002 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Shared evidence, final reply and assets is missing. |
| CMP-043 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Question input is missing. |
| CMP-044 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Send action is missing. |
| CMP-045 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Active-run cancellation is missing. |
| CMP-046 | BP-008 | investigate | TASK-002 | Read source, preserve this implementation; runtime-specific evidence for Prompt chips is missing. |
| CMP-047 | BP-009 | investigate | TASK-003 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-048 | BP-001 | investigate | TASK-003, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-049 | BP-009 | investigate | TASK-003 | Read source, preserve this implementation; runtime-specific evidence for Centre KPI figures is missing. |
| CMP-050 | BP-009 | investigate | TASK-003 | Read source, preserve this implementation; runtime-specific evidence for Latest run header/navigation is missing. |
| CMP-051 | BP-002 | investigate | TASK-003, TASK-024 | Read source, preserve this implementation; runtime-specific evidence for Latest result and evidence is missing. |
| CMP-052 | BP-009 | investigate | TASK-003, TASK-019 | Read source, preserve this implementation; runtime-specific evidence for Start-run form/dialog is missing. |
| CMP-053 | BP-009 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-054 | BP-001 | investigate | TASK-004, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-055 | BP-010 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Query input is missing. |
| CMP-056 | BP-010 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Status filter is missing. |
| CMP-057 | BP-010 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Refresh action is missing. |
| CMP-058 | BP-010 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Loading/error/empty/list templates is missing. |
| CMP-059 | BP-010 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Previous/next-page actions is missing. |
| CMP-060 | BP-010 | investigate | TASK-004 | Read source, preserve this implementation; runtime-specific evidence for Page/query counts is missing. |
| CMP-061 | BP-009 | investigate | TASK-005 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-062 | BP-001 | investigate | TASK-005, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-063 | BP-011 | investigate | TASK-005 | Read source, preserve this implementation; runtime-specific evidence for Query input is missing. |
| CMP-064 | BP-011 | investigate | TASK-005 | Read source, preserve this implementation; runtime-specific evidence for Domain/source filters is missing. |
| CMP-065 | BP-011 | investigate | TASK-005, TASK-018 | Read source, preserve this implementation; runtime-specific evidence for Result row and empty/error templates is missing. |
| CMP-066 | BP-011 | investigate | TASK-005 | Read source, preserve this implementation; runtime-specific evidence for Catalogue count is missing. |
| CMP-067 | BP-011 | investigate | TASK-005 | Read source, preserve this implementation; runtime-specific evidence for Pagination actions is missing. |
| CMP-068 | BP-009 | investigate | TASK-006 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-069 | BP-001 | investigate | TASK-006, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-070 | BP-012 | investigate | TASK-006, TASK-024 | Read source, preserve this implementation; runtime-specific evidence for Actual experiment/empty/error template is missing. |
| CMP-071 | BP-009 | investigate | TASK-007 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-072 | BP-001 | investigate | TASK-007, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-073 | BP-013 | investigate | TASK-007, TASK-024 | Read source, preserve this implementation; runtime-specific evidence for Current runtime/API/worker details is missing. |
| CMP-074 | BP-013 | investigate | TASK-007, TASK-030 | Read source, preserve this implementation; runtime-specific evidence for S1 implementation/production boundary is missing. |
| CMP-075 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-076 | BP-001 | investigate | TASK-008, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-077 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Run status/task/identity header is missing. |
| CMP-078 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Cost/duration/budget metrics is missing. |
| CMP-079 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Stream/connection state is missing. |
| CMP-080 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Focus view control is missing. |
| CMP-081 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Cancel action is missing. |
| CMP-082 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Mobile tab controls is missing. |
| CMP-083 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Execution DAG node/edge templates is missing. |
| CMP-084 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Event type filter is missing. |
| CMP-085 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Follow events toggle is missing. |
| CMP-086 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Timeline event/check group templates is missing. |
| CMP-087 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Step/event/attempt inspector is missing. |
| CMP-088 | BP-014 | investigate | TASK-008 | Read source, preserve this implementation; runtime-specific evidence for Proof and final result is missing. |
| CMP-089 | BP-014 | investigate | TASK-008, TASK-020 | Read source, preserve this implementation; runtime-specific evidence for Missing-ID/error/static variant is missing. |
| CMP-090 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-091 | BP-001 | investigate | TASK-009, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-092 | BP-003 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Full catalogue sphere is missing. |
| CMP-093 | BP-015 | investigate | TASK-009, TASK-032 | Read source, preserve this implementation; runtime-specific evidence for Skill query input is missing. |
| CMP-094 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Search result buttons/empty template is missing. |
| CMP-095 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Domain filter is missing. |
| CMP-096 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Relation filters is missing. |
| CMP-097 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Neighbours toggle is missing. |
| CMP-098 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Task-only toggle is missing. |
| CMP-099 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Visible/catalogue HUD is missing. |
| CMP-100 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Recorded-task panel and run link is missing. |
| CMP-101 | BP-002 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Capability report action is missing. |
| CMP-102 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Zoom actions is missing. |
| CMP-103 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Reset action is missing. |
| CMP-104 | BP-015 | investigate | TASK-009, TASK-028 | Read source, preserve this implementation; runtime-specific evidence for Rotation pause action is missing. |
| CMP-105 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Labels toggle is missing. |
| CMP-106 | BP-015 | investigate | TASK-009, TASK-028 | Read source, preserve this implementation; runtime-specific evidence for Evolved-only toggle is missing. |
| CMP-107 | BP-015 | investigate | TASK-009, TASK-028 | Read source, preserve this implementation; runtime-specific evidence for Selected node card and close is missing. |
| CMP-108 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Related skill controls is missing. |
| CMP-109 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Capability/version/resources contract is missing. |
| CMP-110 | BP-015 | investigate | TASK-009 | Read source, preserve this implementation; runtime-specific evidence for Loading/error overlay and tooltip is missing. |
| CMP-111 | BP-016 | investigate | TASK-010 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-112 | BP-001 | investigate | TASK-010, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-113 | BP-017 | investigate | TASK-010 | Read source, preserve this implementation; runtime-specific evidence for Overview graph is missing. |
| CMP-114 | BP-017 | investigate | TASK-010 | Read source, preserve this implementation; runtime-specific evidence for Domain/quality summaries is missing. |
| CMP-115 | BP-017 | investigate | TASK-010 | Read source, preserve this implementation; runtime-specific evidence for Pipeline/reference explanation is missing. |
| CMP-116 | BP-016 | investigate | TASK-011 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-117 | BP-001 | investigate | TASK-011, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-118 | BP-018 | investigate | TASK-011 | Read source, preserve this implementation; runtime-specific evidence for Scenario selector is missing. |
| CMP-119 | BP-018 | investigate | TASK-011 | Read source, preserve this implementation; runtime-specific evidence for Custom task input is missing. |
| CMP-120 | BP-018 | investigate | TASK-011 | Read source, preserve this implementation; runtime-specific evidence for Plan contrast action is missing. |
| CMP-121 | BP-018 | investigate | TASK-011 | Read source, preserve this implementation; runtime-specific evidence for Legacy demonstration action is missing. |
| CMP-122 | BP-018 | investigate | TASK-011, TASK-022, TASK-030 | Read source, preserve this implementation; runtime-specific evidence for Model-reference/plan result states is missing. |
| CMP-123 | BP-016 | investigate | TASK-012 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-124 | BP-001 | investigate | TASK-012, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-125 | BP-019 | investigate | TASK-012 | Read source, preserve this implementation; runtime-specific evidence for Skill query input is missing. |
| CMP-126 | BP-019 | investigate | TASK-012 | Read source, preserve this implementation; runtime-specific evidence for Domain filter is missing. |
| CMP-127 | BP-019 | investigate | TASK-012 | Read source, preserve this implementation; runtime-specific evidence for Skill list/count/empty/error templates is missing. |
| CMP-128 | BP-019 | investigate | TASK-012 | Read source, preserve this implementation; runtime-specific evidence for Skill contract/detail template is missing. |
| CMP-129 | BP-019 | investigate | TASK-012 | Read source, preserve this implementation; runtime-specific evidence for Catalogue pagination controls is missing. |
| CMP-130 | BP-016 | investigate | TASK-013 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-131 | BP-001 | investigate | TASK-013, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-132 | BP-020 | investigate | TASK-013 | Read source, preserve this implementation; runtime-specific evidence for Query/task/top-K inputs is missing. |
| CMP-133 | BP-020 | investigate | TASK-013 | Read source, preserve this implementation; runtime-specific evidence for Search action is missing. |
| CMP-134 | BP-020 | investigate | TASK-013 | Read source, preserve this implementation; runtime-specific evidence for Three-channel search results is missing. |
| CMP-135 | BP-020 | investigate | TASK-013 | Read source, preserve this implementation; runtime-specific evidence for Routing query input is missing. |
| CMP-136 | BP-020 | investigate | TASK-013 | Read source, preserve this implementation; runtime-specific evidence for Routing action/result is missing. |
| CMP-137 | BP-016 | investigate | TASK-014 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-138 | BP-001 | investigate | TASK-014, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-139 | BP-021 | investigate | TASK-014 | Read source, preserve this implementation; runtime-specific evidence for Task selector/input is missing. |
| CMP-140 | BP-021 | investigate | TASK-014 | Read source, preserve this implementation; runtime-specific evidence for Execution mode selector is missing. |
| CMP-141 | BP-021 | investigate | TASK-014 | Read source, preserve this implementation; runtime-specific evidence for Plan comparison action is missing. |
| CMP-142 | BP-021 | investigate | TASK-014 | Read source, preserve this implementation; runtime-specific evidence for Create real-run action is missing. |
| CMP-143 | BP-021 | investigate | TASK-014, TASK-022 | Read source, preserve this implementation; runtime-specific evidence for Status/result/model-reference states is missing. |
| CMP-144 | BP-016 | investigate | TASK-015 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-145 | BP-001 | investigate | TASK-015, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-146 | BP-022 | investigate | TASK-015 | Read source, preserve this implementation; runtime-specific evidence for Actual result/empty/error template is missing. |
| CMP-147 | BP-016 | investigate | TASK-016 | Read source, preserve this implementation; runtime-specific evidence for Page shell/navigation/status is missing. |
| CMP-148 | BP-001 | investigate | TASK-016, TASK-017 | Read source, preserve this implementation; runtime-specific evidence for Connection settings and toast is missing. |
| CMP-149 | BP-023 | investigate | TASK-016, TASK-030 | Read source, preserve this implementation; runtime-specific evidence for S1 service contract is missing. |
| CMP-150 | BP-023 | investigate | TASK-016 | Read source, preserve this implementation; runtime-specific evidence for Export action is missing. |
| CMP-151 | BP-023 | investigate | TASK-016 | Read source, preserve this implementation; runtime-specific evidence for Export result/error template is missing. |
| CMP-152 | BP-023 | investigate | TASK-016 | Read source, preserve this implementation; runtime-specific evidence for Live laboratory status is missing. |
| CMP-153 | BP-024 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-154 | BP-025 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-155 | BP-026 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-156 | BP-027 | investigate | TASK-001, TASK-031, TASK-034 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-157 | BP-028 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-158 | BP-029 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-159 | BP-030 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-160 | BP-031 | investigate | TASK-001, TASK-031 | Controller faults are covered by actual controlled DOM assertions; native dialog keyboard/focus/layout still needs homepage browser evidence. |
| CMP-161 | BP-032 | investigate | TASK-035, TASK-038, TASK-036, TASK-037 | Shared logic/source inspected; / has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-162 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /chat has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-163 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /runs#mission has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-164 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /runs#runs has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-165 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /runs#skills has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-166 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /runs#eval has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-167 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /runs#system has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-168 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /run?id=&lt;run-id&gt; has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-169 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /graph?run=&amp;skill=&amp;domain= has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-170 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#overview has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-171 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#demo has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-172 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#skills?skill= has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-173 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#search has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-174 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#run has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-175 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#results has distinct navigation/parent layout and requires its own native browser acceptance. |
| CMP-176 | BP-032 | investigate | TASK-035, TASK-038 | Shared logic/source inspected; /dashboard#adapters has distinct navigation/parent layout and requires its own native browser acceptance. |

## 问题索引

| 问题 | 级别 | 置信度 | 状态 | 页面 / 实例 |
|---|---|---|---|---|
| FND-001 Token clear/close race | P1 | confirmed | resolved | PAGE-001, PAGE-002, PAGE-003, PAGE-004, PAGE-005, PAGE-006, PAGE-007, PAGE-008, PAGE-009, PAGE-010, PAGE-011, PAGE-012, PAGE-013, PAGE-014, PAGE-015, PAGE-016, CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148 |
| FND-002 Chained skill metadata overwrites a newer query | P2 | confirmed | resolved | PAGE-005, CMP-065 |
| FND-003 Confirmed run creation misreported when storage is disabled | P2 | confirmed | resolved | PAGE-003, CMP-052 |
| FND-004 Run detail crashes before empty-state rendering with storage disabled | P2 | confirmed | resolved | PAGE-008, CMP-089 |
| FND-005 Stored sessions trust cached rendering and dynamic inline handlers | P1 | confirmed | resolved | PAGE-001, PAGE-002, CMP-019, CMP-038 |
| FND-006 Invalid model score and zero-attempt presentation | P2 | confirmed | resolved | PAGE-002, PAGE-011, PAGE-014, CMP-041, CMP-122, CMP-143 |
| FND-007 State contract events need truthful separation from reward | P2 | confirmed | resolved | PAGE-001, CMP-014 |
| FND-008 Late mission/evaluation/system/health responses overwrite newer state | P2 | confirmed | resolved | PAGE-003, PAGE-006, PAGE-007, CMP-051, CMP-070, CMP-073 |
| FND-009 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs | P1 | confirmed | fixed_unverified | PAGE-001, CMP-024 |
| FND-010 Replay load/preview stale failures can overwrite current state | P2 | confirmed | fixed_unverified | PAGE-001, CMP-010, CMP-023 |
| FND-011 Native step controls used a manual keyboard override | P3 | probable | fixed_unverified | PAGE-001, CMP-013 |
| FND-012 Sphere keyboard pause/focus state not reflected consistently | P2 | confirmed | fixed_unverified | PAGE-009, CMP-104, CMP-106, CMP-107 |
| FND-013 Global chip binding replaces injected scenario actions | P2 | confirmed | fixed_unverified | PAGE-001, CMP-018 |
| FND-014 Historical growth and S1 deployment labels overstate supported evidence | P2 | confirmed | fixed_unverified | PAGE-001, PAGE-007, PAGE-011, PAGE-016, CMP-026, CMP-030, CMP-074, CMP-122, CMP-149 |
| FND-015 Shared Product dialog async ownership, unsafe field boundaries and missing-step recovery | P1 | confirmed | resolved | PAGE-001, CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160 |
| FND-016 Graph search lacked keyboard selection | P2 | confirmed | resolved | PAGE-009, CMP-093 |
| FND-017 Mobile uniqueness cards inherited three inline columns and overflowed | P2 | confirmed | resolved | PAGE-001, CMP-026 |
| FND-018 Task input was incorrectly included in newly delivered file count | P2 | confirmed | resolved | PAGE-001, CMP-156 |
| FND-019 Frontier v7 dialog ignored centered modal margin | P2 | confirmed | resolved | PAGE-001, CMP-161 |
| FND-020 Global footer styles overrode frontier modal footer | P2 | confirmed | resolved | PAGE-001, CMP-161 |
| FND-021 Disabled frontier submit left native focus on BODY | P2 | confirmed | resolved | PAGE-001, CMP-161 |

## 任务顺序

| 任务 | 阶段 | 负责人 | 依赖 | 状态 |
|---|---|---|---|---|
| TASK-017 Token clear/close race correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-018 Chained skill metadata overwrites a newer query correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-019 Confirmed run creation misreported when storage is disabled correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-020 Run detail crashes before empty-state rendering with storage disabled correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-021 Stored sessions trust cached rendering and dynamic inline handlers correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-022 Invalid model score and zero-attempt presentation correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-023 State contract events need truthful separation from reward correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-024 Late mission/evaluation/system/health responses overwrite newer state correction and bounded regression | 1 | frontend implementation |  | verified |
| TASK-031 Verify shared Product controller fault corrections | 1 | parent frontend implementation and audit verification |  | verified |
| TASK-032 Graph search lacked keyboard selection actual browser correction | 1 | root frontend implementation / IAB QA |  | verified |
| TASK-033 Mobile uniqueness cards inherited three inline columns and overflowed actual browser correction | 1 | root frontend implementation / IAB QA |  | verified |
| TASK-034 Final local deliverable count correction | 1 | root frontend implementation and Node verification |  | verified |
| TASK-035 Verify shared frontier IIFE fault logic | 1 | root frontend implementation / IAB QA |  | verified |
| TASK-036 Repair and natively recheck v7 frontier modal/footer cascade | 1 | root frontend implementation / IAB QA |  | verified |
| TASK-037 Repair and natively recheck disabled-submit focus | 1 | root frontend implementation / IAB QA |  | verified |
| TASK-001 Executive briefing runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-002 Conversation runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-003 Mission centre runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-004 Run catalogue runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-005 Skill catalogue runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-006 Evaluation reports runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-007 Deployment information runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-008 Run detail runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-009 Spherical skill network runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-010 Developer overview runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-011 Plan contrast runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-012 Developer skill inspector runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-013 Retrieval/routing laboratory runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-014 Execution laboratory runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-015 Historical results runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-016 S1/export laboratory runtime/visual acceptance | 2 | frontend QA with runtime/browser access |  | blocked |
| TASK-025 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs browser verification | 2 | frontend QA with browser access |  | implemented |
| TASK-026 Replay load/preview stale failures can overwrite current state browser verification | 2 | frontend QA with browser access |  | implemented |
| TASK-027 Native step controls receive duplicate keyboard activation browser verification | 2 | frontend QA with browser access |  | implemented |
| TASK-028 Sphere keyboard pause/focus state not reflected consistently browser verification | 2 | frontend QA with browser access |  | implemented |
| TASK-029 Global chip binding replaces injected scenario actions browser verification | 2 | frontend QA with browser access |  | implemented |
| TASK-030 Historical growth and S1 deployment labels overstate supported evidence browser verification | 2 | frontend QA with browser access |  | implemented |
| TASK-038 Complete frontier integration in all sixteen parent views | 2 | frontend QA with target browser and S1 environment |  | blocked |

## 发布门槛

| 门槛 | 必需 | 状态 | 证据 / 理由 |
|---|---|---|---|
| Core journey and error recovery | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Object/tenant authorization | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Critical accessibility | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Data consistency | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Production build/deployment | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Measured performance budget | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Observability | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| Release and recovery | True | blocked |  Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |

## 缺口


## 下一步

- Execute all remaining full-route SCN assertions without promoting partial viewport checks to full coverage.
- Verify 200% zoom, screen reader, reduced-motion actual OS/browser setting, all 16 view full-page/error states, browser network fault injection, S1 production integration, performance budget.
- Recheck any source changed after the recorded IAB asset version; source SHA-256 does not identify deployment by itself.
