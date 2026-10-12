# 前端审计与修复记录

基线：`af07f453edf24a38782b4250e07f2d5fa0775416 + reviewed worktree (see source-manifest.json)`；时间：2026-10-12T06:54:39.746192+00:00。

使用用户指定的 BadbotAI/BadGoods「前端审查助手」，提交 76d20b19c8b2a6513d1516d42fdcc42a2b8c394f，按 full/implement 执行。第三方技能仅用于审查，未纳入项目提交；其 LICENSE-NOTICE 未授予开源或商业再分发许可。

范围是 6 个 HTML 文档、16 个独立视图、31 个实际实现定义、160 个逻辑组件实例。重复记录按同一路由、模板和交互契约登记；不同条件分支与控制责任列在 locator/variant 中，装饰包装归属最近实例。源码已读；真实 IAB 已核验六个文档入口及指定交互，尚未完成十六个视图及条件分支的运行导航核对，因此发现状态仍为 limited。

已执行八项 Node 检查，均退出 0；21 个明确的 Node/controlled DOM 场景通过。另合并 root 真实 IAB 的 12 个双尺寸首屏检查和 4 个具体布局/键盘/回放场景，以及 2 个浏览器发现的修复复验。16 个全视图验收场景仍 blocked，6 组较广的源码修复仍 fixed_unverified。不能宣布全站或生产验收通过。

主要修复包括：连接候选令牌的提交与清除时序；跨多次 await 的检索结果所有权；可选元数据故障隔离；不可用 storage 的创建/详情恢复；会话缓存数据白名单；文件/技能预览的代际所有权和动态名称转义；共享演示按钮的绑定边界；球体暂停状态及选择焦点；无效模型评分/0 次尝试/资产增长文案；状态契约事件的声明、阻断和效果展示。

按范围列出的所有实例都有蓝图、处置与补证任务。全视图八维检查未完成项保持 blocked；实际观察到的有限交互与首屏检查单列 passed，源码可追溯性不能代替实际交互。待浏览器核验不是已经复现的缺陷，也不是授权接受的风险。

## 索引

- [机器台账](audit.json) 与 [生成的覆盖索引](coverage.md)
- [问题与修复](findings.md)
- [组件契约](components.md)
- [逐页报告](pages/PAGE-001.md)（其余 PAGE 同目录）
- [实施与补证任务](refactor-plan.md)
- [验收交接](verification-handoff.md)
- [实际命令结果](verification.log) 与 [源码指纹](source-manifest.json)

## 发布判断

目前可交付已审查的源码改进与可重现逻辑证据。发布条件未满足：核心浏览器旅程、身份/租户隔离、焦点/辅助技术、数据一致性、实际生产部署、性能预算、可观测性与恢复仍需补证；S1 服务合同存在不等于线上接入已经验收。

## 真实浏览器的有限证据

[记录](browser-observations.json) 包含六个入口的 1440×900 与 390×844 首屏，均无水平溢出；首页背景连续与手机单列、真实七阶段回放暂停/End、球体 Enter/Escape/Space 焦点同步、手机抽屉 Escape 焦点已观察。截图已保存在 [screenshots/](screenshots/)。未检查：200% zoom, screen reader, reduced-motion actual OS/browser setting, all 16 view full-page/error states, browser network fault injection, S1 production integration, performance budget。这些事实不使 16 个全视图场景自动通过。

## 最后一次局部修复与版本

FND-018：任务输入与跨轮输入从新增交付计数中排除，仍保留输入证据；SCN-053 的混合来源 fixture 断言已实际通过。该局部修复验证时源码为 v20261012.5 / contract.5；最终状态内核直接呈现快照为 v20261012.6 / contract.6；历史双尺寸/交互浏览器记录仍为 v2，[交付面板截图](screenshots/state-kernel-delivery-v4.jpg) 为当时 v4（5 个交付、20/20 限定检查、4/12 奖励门、正式排序未自动更新）。不把历史截图或最终源码指纹当作全站 v5 部署验收。

最终 v6 的局部 UI 观察见 [final-ui-observations.json](final-ui-observations.json)：首页直接展现逐步准入/效果与真实回放计数，手机和桌面宽度无溢出；实验页可见 39 进程、33→6 次代码调用、违规执行 24→0、两组有效输出均 5/6。它只补充实际呈现证据，不改变未检查项或全站门槛。
