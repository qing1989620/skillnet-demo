# 验收与交接

## 已执行

见 verification.log：八项 Node 检查退出 0。真实 IAB 首屏/指定交互证据见 browser-observations.json 与 screenshots/；没有性能/辅助技术完整验收证据。

## 已记录的浏览器范围

六个文档入口在 1440×900 与 390×844 的首屏无水平溢出；首页长页背景及手机单列、真实七阶段回放暂停/End、球体 Enter/Escape/Space 与焦点、手机抽屉 Escape 焦点有实际 IAB 记录。对应窄场景为 SCN-037—SCN-052。这些记录不代替完整视图验收。

## 必须补齐的真实场景

- 首页全部长内容与七阶段直播、拖动/倍速、问题折叠、失败/取消/未知状态；已记录的回放暂停/End 不代表所有分支。
- 手机会话历史恢复、跨轮文件及抽屉其他交互；开启/Escape/焦点回按钮已记录。
- 球体完整 Tab 路径、关系/领域/演化过滤与实际系统减少动效设置；查询 Enter、Escape 返回与 Canvas Space 同步已记录。
- 查询 A → B 及 A 迟到失败；技能元数据 500；运行创建后禁用 storage；网络中断恢复。
- 预览 A 慢 → B 快 → A 返回；关闭后 A 返回；Tab/Escape；引号文件名；不执行注入内容。
- 全部十六视图在 390×844、1440×900、200% zoom 和长内容条件；记录 console/network 和构建号。
- 真实 S1 租户签名 scope/附件/会话、Worker 恢复和 Docker 隔离，由后端/平台负责人完成。

## 门槛

| GATE | 目标 | 当前状态 |
|---|---|---|
| GATE-001 | Core journey and error recovery | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-002 | Object/tenant authorization | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-003 | Critical accessibility | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-004 | Data consistency | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-005 | Production build/deployment | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-006 | Measured performance budget | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-007 | Observability | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |
| GATE-008 | Release and recovery | blocked：Actual final-deployment evidence required; Node logic/source checks are partial evidence and cannot satisfy this production gate. |

台账校验器只检查结构、关联和声明的覆盖；不能据此证明实际软件安全或无遗漏。Third-party skill 不复制到仓库；源码指纹与运行部署身份必须独立核对。

最终局部交付计数回归：SCN-053 已通过，node tools/product_check.js 退出 0。源码 v5、历史主浏览器记录 v2、交付面板截图 v4 不混用部署身份；root 后续文档观察可补充，未检查场景仍保留。
