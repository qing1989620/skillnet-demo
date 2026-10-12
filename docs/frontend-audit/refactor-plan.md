# 实施与补证计划

已经验证的任务是有明确断言的 Node 逻辑修复；implemented 是已改源码、待精确浏览器复验；blocked 是尚未执行的页面验收。

| TASK | 阶段 | 范围 | 状态 | 负责人 | 场景 |
|---|---|---|---|---|---|
| TASK-001 Executive briefing runtime/visual acceptance | 2 | PAGE-001, CMP-001, CMP-002, CMP-003, CMP-004, CMP-005, CMP-006, CMP-007, CMP-008, CMP-009, CMP-010, CMP-011, CMP-012, CMP-013, CMP-014, CMP-015, CMP-016, CMP-017, CMP-018, CMP-019, CMP-020, CMP-021, CMP-022, CMP-023, CMP-024, CMP-025, CMP-026, CMP-027, CMP-028, CMP-029, CMP-030, CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160 | blocked | frontend QA with runtime/browser access | SCN-001 |
| TASK-002 Conversation runtime/visual acceptance | 2 | PAGE-002, CMP-031, CMP-032, CMP-033, CMP-034, CMP-035, CMP-036, CMP-037, CMP-038, CMP-039, CMP-040, CMP-041, CMP-042, CMP-043, CMP-044, CMP-045, CMP-046 | blocked | frontend QA with runtime/browser access | SCN-002 |
| TASK-003 Mission centre runtime/visual acceptance | 2 | PAGE-003, CMP-047, CMP-048, CMP-049, CMP-050, CMP-051, CMP-052 | blocked | frontend QA with runtime/browser access | SCN-003 |
| TASK-004 Run catalogue runtime/visual acceptance | 2 | PAGE-004, CMP-053, CMP-054, CMP-055, CMP-056, CMP-057, CMP-058, CMP-059, CMP-060 | blocked | frontend QA with runtime/browser access | SCN-004 |
| TASK-005 Skill catalogue runtime/visual acceptance | 2 | PAGE-005, CMP-061, CMP-062, CMP-063, CMP-064, CMP-065, CMP-066, CMP-067 | blocked | frontend QA with runtime/browser access | SCN-005 |
| TASK-006 Evaluation reports runtime/visual acceptance | 2 | PAGE-006, CMP-068, CMP-069, CMP-070 | blocked | frontend QA with runtime/browser access | SCN-006 |
| TASK-007 Deployment information runtime/visual acceptance | 2 | PAGE-007, CMP-071, CMP-072, CMP-073, CMP-074 | blocked | frontend QA with runtime/browser access | SCN-007 |
| TASK-008 Run detail runtime/visual acceptance | 2 | PAGE-008, CMP-075, CMP-076, CMP-077, CMP-078, CMP-079, CMP-080, CMP-081, CMP-082, CMP-083, CMP-084, CMP-085, CMP-086, CMP-087, CMP-088, CMP-089 | blocked | frontend QA with runtime/browser access | SCN-008 |
| TASK-009 Spherical skill network runtime/visual acceptance | 2 | PAGE-009, CMP-090, CMP-091, CMP-092, CMP-093, CMP-094, CMP-095, CMP-096, CMP-097, CMP-098, CMP-099, CMP-100, CMP-101, CMP-102, CMP-103, CMP-104, CMP-105, CMP-106, CMP-107, CMP-108, CMP-109, CMP-110 | blocked | frontend QA with runtime/browser access | SCN-009 |
| TASK-010 Developer overview runtime/visual acceptance | 2 | PAGE-010, CMP-111, CMP-112, CMP-113, CMP-114, CMP-115 | blocked | frontend QA with runtime/browser access | SCN-010 |
| TASK-011 Plan contrast runtime/visual acceptance | 2 | PAGE-011, CMP-116, CMP-117, CMP-118, CMP-119, CMP-120, CMP-121, CMP-122 | blocked | frontend QA with runtime/browser access | SCN-011 |
| TASK-012 Developer skill inspector runtime/visual acceptance | 2 | PAGE-012, CMP-123, CMP-124, CMP-125, CMP-126, CMP-127, CMP-128, CMP-129 | blocked | frontend QA with runtime/browser access | SCN-012 |
| TASK-013 Retrieval/routing laboratory runtime/visual acceptance | 2 | PAGE-013, CMP-130, CMP-131, CMP-132, CMP-133, CMP-134, CMP-135, CMP-136 | blocked | frontend QA with runtime/browser access | SCN-013 |
| TASK-014 Execution laboratory runtime/visual acceptance | 2 | PAGE-014, CMP-137, CMP-138, CMP-139, CMP-140, CMP-141, CMP-142, CMP-143 | blocked | frontend QA with runtime/browser access | SCN-014 |
| TASK-015 Historical results runtime/visual acceptance | 2 | PAGE-015, CMP-144, CMP-145, CMP-146 | blocked | frontend QA with runtime/browser access | SCN-015 |
| TASK-016 S1/export laboratory runtime/visual acceptance | 2 | PAGE-016, CMP-147, CMP-148, CMP-149, CMP-150, CMP-151, CMP-152 | blocked | frontend QA with runtime/browser access | SCN-016 |
| TASK-017 Token clear/close race correction and bounded regression | 1 | CMP-002, CMP-032, CMP-048, CMP-054, CMP-062, CMP-069, CMP-072, CMP-076, CMP-091, CMP-112, CMP-117, CMP-124, CMP-131, CMP-138, CMP-145, CMP-148 | verified | frontend implementation | SCN-017 |
| TASK-018 Chained skill metadata overwrites a newer query correction and bounded regression | 1 | CMP-065 | verified | frontend implementation | SCN-018 |
| TASK-019 Confirmed run creation misreported when storage is disabled correction and bounded regression | 1 | CMP-052 | verified | frontend implementation | SCN-019 |
| TASK-020 Run detail crashes before empty-state rendering with storage disabled correction and bounded regression | 1 | CMP-089 | verified | frontend implementation | SCN-020 |
| TASK-021 Stored sessions trust cached rendering and dynamic inline handlers correction and bounded regression | 1 | CMP-019, CMP-038 | verified | frontend implementation | SCN-021 |
| TASK-022 Invalid model score and zero-attempt presentation correction and bounded regression | 1 | CMP-041, CMP-122, CMP-143 | verified | frontend implementation | SCN-022 |
| TASK-023 State contract events need truthful separation from reward correction and bounded regression | 1 | CMP-014 | verified | frontend implementation | SCN-023 |
| TASK-024 Late mission/evaluation/system/health responses overwrite newer state correction and bounded regression | 1 | CMP-051, CMP-070, CMP-073 | verified | frontend implementation | SCN-024 |
| TASK-025 Legacy previews interpolate dynamic filenames into JavaScript; stale requests can replace newer dialogs browser verification | 2 | CMP-024 | implemented | frontend QA with browser access | SCN-001 |
| TASK-026 Replay load/preview stale failures can overwrite current state browser verification | 2 | CMP-010, CMP-023 | implemented | frontend QA with browser access | SCN-001 |
| TASK-027 Native step controls receive duplicate keyboard activation browser verification | 2 | CMP-013 | implemented | frontend QA with browser access | SCN-001 |
| TASK-028 Sphere keyboard pause/focus state not reflected consistently browser verification | 2 | CMP-104, CMP-106, CMP-107 | implemented | frontend QA with browser access | SCN-009 |
| TASK-029 Global chip binding replaces injected scenario actions browser verification | 2 | CMP-018 | implemented | frontend QA with browser access | SCN-001 |
| TASK-030 Historical growth and S1 deployment labels overstate supported evidence browser verification | 2 | CMP-026, CMP-030, CMP-074, CMP-122, CMP-149 | implemented | frontend QA with browser access | SCN-001, SCN-007, SCN-011, SCN-016 |
| TASK-031 Verify shared Product controller fault corrections | 1 | CMP-153, CMP-154, CMP-155, CMP-156, CMP-157, CMP-158, CMP-159, CMP-160 | verified | parent frontend implementation and audit verification | SCN-025, SCN-026, SCN-027, SCN-028, SCN-029, SCN-030, SCN-031, SCN-032, SCN-033, SCN-034, SCN-035, SCN-036 |
| TASK-032 Graph search lacked keyboard selection actual browser correction | 1 | CMP-093 | verified | root frontend implementation / IAB QA | SCN-051 |
| TASK-033 Mobile uniqueness cards inherited three inline columns and overflowed actual browser correction | 1 | CMP-026 | verified | root frontend implementation / IAB QA | SCN-049 |

全部任务的真实文件、执行步骤、验收、恢复和风险见 audit.json/tasks。先完成每视图浏览器验收，再与后端负责人核对 S1/队列/Docker 的实际运行；最终提交变化后重新运行八项检查与指纹记录。

TASK-034：最终局部交付数量修复；phase 1 / verified；CMP-156；SCN-053；EV-046。过滤输入来源，保留原始证据，不扩大整页验收范围。
