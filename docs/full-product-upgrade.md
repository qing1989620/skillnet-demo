# SkillNet 0.9 · 全产品优化与验收

本轮覆盖六个页面、运行中心五个视图、内核实验室七个功能页，以及导航、连接设置、技能契约、运行证据、依赖图和文件预览等公共组件。首页原有流动背景、交互星图、七阶段演示、同题对照、反馈变化和历史回放均保留。

## 页面与组件覆盖

| 页面 | 本轮改动 | 实际验收 |
|---|---|---|
| `/` 产品概览 | 保留原有首屏和汇报舞台；统一产品入口；历史实验元数据不一致时显示复核说明 | 首屏、移动端、原有七阶段与回放回归 |
| `/chat` 科研工作台 | 提问后优先展示七项内核证据、实际 DAG、验收和文件；长问题可展开；活动任务刷新后订阅同一 Run | 真实执行、执行中刷新恢复、CSV/图表预览、手机会话抽屉 |
| `/runs` 运行中心 | 运行总览、记录、技能库、实验和系统五个视图；真实统计、服务端分页与全文搜索；手机记录卡片 | 翻页、问题搜索、状态筛选、技能契约跳转、四份实验结果、系统并发状态 |
| `/run?id=…` 执行详情 | 实际依赖图、事件筛选、完整代码与尝试记录；显示输入文件来源和指纹；手机切换流程/时间线/详情 | 多根与分支 DAG、阶段筛选、语义未确认项、文件版本；点击节点自动打开手机详情，内容独立滚动 |
| `/graph` 技能星图 | 保留原有背景与星图交互；新增领域、关系和邻域筛选；完整技能契约入口；改善标签避让和手机视野 | 搜索选择技能、邻域显示 4 个节点、关闭相似关系后显示 3 个、契约跳转 |
| `/dashboard` 内核实验室 | 七个功能页统一布局；结构化技能契约；检索/路由/方案请求状态；真实完整执行入口和可编辑问题；保留研究对照、反馈变化；接入清单 | 七个手机页无根页面横向溢出；三档检索、Wiki 路由、方案盲评、完整 Run、原有研究对照、四份实验和八类导出 |
| 公共组件 | 导航与连接状态；七项内核证据；真实 DAG；安全 CSV/文本、图像、PDF 与下载入口；居中弹窗 | 桌面 1440×1000、手机 390×844；连接弹窗开关；CSV 引号/换行和危险文本回归 |

每项内核贡献都引用实际运行数据：检索采用了哪些技能、选择器记录了什么、步骤如何依赖、哪些步骤修复、程序与语义验收结果、执行账本如何更新、学习是否准入。界面没有用固定动画或预设成功数字代替真实执行。

## 后端修复

- 历史记录按任务开始时间排序，先筛选再分页；全文搜索使用完整问题。内存中的活动状态覆盖磁盘检查点，返回总数、下一页和汇总口径。
- 历史列表缓存轻量摘要，文件身份、时间或大小改变才重新读取；列表请求不重复序列化完整代码、尝试和事件。
- 上游文件复制失败会停止本步，防止模型在缺少实际输入时继续执行。只有成功复制后才登记输入来源、逻辑名和 SHA-256。
- 并行分支的同名文件按依赖距离和步骤编号确定选择顺序，避免线程完成顺序改变下游输入。
- 完整 Run 与旧研究对照都执行学习门槛。执行失败、验收不合格或只验证多步方案中的单步时，不写入正向学习奖励，也不进行技能准入。
- 两个执行入口都向修复模型提供标准错误及标准输出中的失败检查，避免有 stderr 时丢掉真正的诊断。修复要求保留验收条件，按数值与契约核对 CSV。
- 最终回复把方案盲评和产物语义复核分开，并明确尚未确认的要求。

交付树移除了 940 个可重生成的步骤尝试、字体与 Windows 缓存文件，共约 102.5 MB。本地文件全部保留；原始运行 JSON、其中的代码/尝试/事件，以及正式产物仍可回放。Git 历史没有重写。

## 真实执行证据

| 入口与记录 | 执行结果 | 程序检查 | 语义确认 | 时间 / 模型成本 |
|---|---|---|---|---|
| 工作台 `2a2cde39-20261008-083429-c54f` | 3 步完成、2 步修复、7 个文件 | 37/37 | 9/11 | 58.346 秒 / ¥0.2143 |
| 实验室 `4bafbb0c-20261008-090352-ffe8` | 3 步完成、2 步修复、5 个文件 | 33/33 | 8/11 | 52.947 秒 / ¥0.1559 |

两次都使用公开硬编码数据 A=[1,2,3,4,5]、B=[2,3,4,5,6]，仅做描述统计。已逐值核对各版本 CSV 的表头、组别、n=5、均值 3/4、样本标准差 √2.5，绝对容差 0.0001；12 个正式文件的大小与 SHA-256 均匹配。PNG/PDF 文件签名也已核对。

这两次执行均存在语义未确认项，系统如实阻止学习准入。执行完成状态不表示所有验收通过；上述成本来自模型 usage 账本，不是供应商最终账单。

原有研究对照还实际暴露了 CSV 类型校验失败，反馈变化为零、学习未准入。失败记录保存在 [单步失败原始证据](evidence/research-step-failure.json)，该发现推动了本轮标准输出诊断修复。

修复后重新运行研究对照，实际经历一次失败和一次成功修复，单步语义确认 4/4。该方案共 4 步，只验证了其中单步，因此仍阻止奖励与技能准入；记录见 [修复后的单步证据](evidence/research-step-repaired.json)。模型结果存在随机性，本轮验证的是诊断进入修复及学习门槛正常工作，没有把这次结果当成成功率提升实验。

完整验收数据、依赖和文件指纹见 [product-validation.json](evidence/product-validation.json)。两个公开 Run 的 JSON 与正式产物随仓库交付，可直接访问 `/run?id=上述ID`。

## 实验结果展示修复

原前端读取 `exp1_retrieval` 或 `splits.heldout`，后端实际返回 `exp1_retrieval_heldout` 等文件键，造成已有结果显示为空。现在运行中心与实验室共用一套按原始键解析的展示，恢复检索图表、方案盲评、逐轮奖励曲线和统计结论。

已定位并修复三类实验生成器将数据集硬编码为 dev 的问题，后续生成会记录实际数据集版本、划分、文件和 SHA-256。历史 `exp1_retrieval_heldout.json` 的文件名与其 `split=dev`、`dataset=dev-v1` 不一致。本轮没有改写原始结果，界面标注任务划分待复核；不能把这些数值直接作为独立测试集证明。选择策略实验的配对 bootstrap 区间包含零，结论仍为不可区分，不声称 LinUCB 优于随机。

## 验证

- 206 项 pytest 回归通过；新增覆盖历史排序/分页/缓存、复制失败、确定性输入版本、研究对照学习门槛和双通道失败诊断。
- `verify.py` 31/31 组件检查通过；本次禁用模型密钥运行。
- 已启动服务的 `selfcheck.py` 23 项通过、0 项失败。
- 前端渲染 5/5、17 段脚本与资源完整性检查通过；首页七阶段、汇报回放、公共证据/CSV/真实实验数据回归通过。
- 浏览器按页面与主要交互进行桌面和手机操作验收。截图记录具体状态，不代表所有研究任务都会成功。
- CI 在 Windows/Linux × Python 3.11/3.12 上复跑离线回归及前端检查。

## 浏览器截图

面向领导的完整内核舞台见 [汇报模式](evidence/screenshots/product-executive-stage-desktop.jpg)，提问、七阶段、实际依赖、代码/输出、价值说明与验收处于同一个视图。

| 场景 | 桌面 | 手机 |
|---|---|---|
| 原有首屏与背景 | [产品概览](evidence/screenshots/product-home-desktop.jpg) | [产品概览](evidence/screenshots/product-home-mobile.jpg) |
| 问题与内核证据 | [科研工作台](evidence/screenshots/product-chat-desktop.jpg) | [科研工作台](evidence/screenshots/product-chat-mobile.jpg) |
| 运行资产 | [运行中心](evidence/screenshots/product-center-desktop.jpg) | [运行中心](evidence/screenshots/product-center-mobile.jpg) |
| 搜索与记录 | [运行记录](evidence/screenshots/product-history-desktop.jpg) | [记录卡片](evidence/screenshots/product-history-mobile.jpg) |
| 执行详情 | [执行 DAG 与事件](evidence/screenshots/product-run-desktop.jpg) | [节点详情](evidence/screenshots/product-run-mobile.jpg) |
| 技能网络 | [技能星图](evidence/screenshots/product-graph-desktop.jpg) | [技能星图](evidence/screenshots/product-graph-mobile.jpg) |
| 内核实验室 | [概览](evidence/screenshots/product-lab-desktop.jpg) · [真实完整链](evidence/screenshots/product-lab-live-desktop.jpg) | [概览](evidence/screenshots/product-lab-mobile.jpg) |
| 历史实验 | [四份原始结果](evidence/screenshots/product-experiments-desktop.jpg) | [实验口径与表格](evidence/screenshots/product-experiments-mobile.jpg) |
| 实际交付物 | [CSV](evidence/screenshots/product-artifact-csv-desktop.jpg) · [PNG](evidence/screenshots/product-artifact-png-desktop.jpg) | 使用同一预览组件 |
| 契约与接入 | [完整技能契约](evidence/screenshots/product-skill-contract-desktop.jpg) · [S1 清单](evidence/screenshots/product-s1-desktop.jpg) | 响应式公共组件 |

## S1 接入边界

接口清单、HTTP 客户端、技能工具处理器、SSE、取消与产物校验已实现。本轮核对了本机服务和八类框架导出；S1 线上联调仍未完成。当前执行器为受控演示环境中的宿主子进程，企业部署还需要独立执行隔离、S1 用户/项目身份映射和共享任务队列。具体契约见 [S1 接入说明](s1-integration.md)。
