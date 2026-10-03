# SkillNet-S1 · UI 参考库（100+ 优秀作品 / 规范 / 研究）

> 用途：为 SkillNet-S1 的界面精修提供**可对照的真实参考**。每条注明来源与**可学要点**，
> 不做泛泛罗列。检索时间：2026-10。检索源：Awwwards / iF Design / Product Hunt /
> Dribbble & Behance 榜单 / 设计日报 / AdminLTE & Orbix 等 2026 年度 SaaS 面板评测 /
> AI 产品设计系统指南。

---

## A. AI-native 产品（对话 + 画布 / Agent 动作流 / 记忆与溯源）· 24 条

| # | 作品 | 可学要点 |
|---|---|---|
| 1 | Claude（Artifacts） | 对话与画布并排：会话负责意图，画布承载产物，双向同步 |
| 2 | ChatGPT（Memory / 工具调用卡） | 工具调用用结构化卡片而非文本；记忆可视化（看到了什么/忘了什么） |
| 3 | Cursor（Agent 动作流） | 计划 → 步骤 → 工具调用 → 中间输出，全部以命名动作流呈现，不用 spinner |
| 4 | Perplexity（引用芯片 / 置信度） | 内联引用芯片 + hover 预览；答案可溯源到来源 |
| 5 | Linear AI / Linear Asks | AI 继承产品既有 comment 基元，因此看起来"原生"而非外挂；单快捷键唤起命令栏 |
| 6 | Notion AI | 多模态输入槽（文件/语音/文本同一入口）；AI 输出用设计好的组件呈现 |
| 7 | Raycast | 命令栏 + 自然语言混合输入；极简结果列表与键盘优先 |
| 8 | Attio "Ask" | AI 摘要作为**一等公民组件**嵌在记录视图里，不是浮层聊天 |
| 9 | Cursor / Lovable / Bolt | 对话 ↔ 实时预览的画布模式；用户可直编画布 |
| 10 | Hex | 笔记本即看板；AI 写查询，输出 UI 用克制图表 + 大量留白 |
| 11 | Vercel Observability | 摘要卡替代图表墙；AI 生成洞察卡 |
| 12 | Datadog | 10 秒内得到洞察的信息层级（时间轴 + 事件流聚合） |
| 13 | Amplitude | 连接数据源即出有意义的默认视图（opinionated defaults） |
| 14 | Intercom | 决策支持型布局：结论先行、动作其次 |
| 15 | PostHog | 洞察卡一卡一问、标题即结论；高密度仍可读 |
| 16 | Figma（Make / 悬停预览） | 上下文悬停预览：悬停功能名在相邻格显示实时预览 |
| 17 | Superhuman / Arc | 建议式 UI：主动推荐下一步动作，但保留退出路径 |
| 18 | Oryzo AI（Awwwards SOTD） | AI 产品的克制视觉：留白 + 单一强调色 |
| 19 | Kris Anfalova · AI CFO Platform | 编辑式 SaaS：衬线标题 + 温暖中性色，让复杂数据可亲 |
| 20 | Trip.com · Trip for Everyone（iF 2026） | 无障碍优先：高对比色系统 + 可缩放字体层级 + 简化交互 |
| 21 | REasy / Vekta / Legitify（Product Hunt） | 降低执行摩擦的产品结构：一步直达结果 |
| 22 | Google Gemini（会话侧栏） | 会话历史只记问题，点击展开详情 |
| 23 | Apple Intelligence（系统级 AI） | AI 能力隐入画布，仅在相关时浮现，永远有手动退路 |
| 24 | Sierra / Decagon（客服 Agent） | 会话式操作的"审批门"（approve / reject）与撤销 |

## B. 开发者工具 / 控制台（密度、克制、状态语义）· 18 条

| # | 作品 | 可学要点 |
|---|---|---|
| 25 | Linear | 暗色优先、静默 chrome、色仅用于状态；一次只展示一层细节 |
| 26 | Vercel Dashboard | 近乎单色系统：层级只靠间距与字重；状态色因此格外醒目 |
| 27 | Stripe Dashboard | 表格即主界面：右对齐数字、等宽数字（tabular figures）、弱网格线 |
| 28 | Supabase | 复杂控制台的清晰寻路：一套模板承载多种工具 |
| 29 | Retool | 组件网格语法：表格强默认值、主操作显眼、表单贴着它编辑的数据 |
| 30 | Plausible | 单页看板、无侧栏：任务足够窄时敢于打破惯例 |
| 31 | Grafana 11 | 深色数据界面中的可读性：网格与单位体系 |
| 32 | Sentry | 异常信息的层级化：摘要 → 事件流 → 堆栈 |
| 33 | GitHub Actions 视图 | 运行（run）为单位的可追溯记录：每步日志 + 状态 + 时长 |
| 34 | Railway / Render | 部署时间线：步骤化状态与实时日志并存 |
| 35 | Fly.io | 极简信息密度下的运维面板 |
| 36 | Cloudflare Dashboard | 分层披露：总览指标 → 下钻明细 |
| 37 | Postman | 请求/响应双栏与工具栏密度控制 |
| 38 | JetBrains Fleet / IntelliJ New UI | 编辑器周边 chrome 的收敛（状态栏、工具窗口） |
| 39 | Warp 终端 | 命令块（block）作为一等对象：每块独立状态与可复用 |
| 40 | TablePlus / DBeaver | 数据表交互：列宽、粘性表头、行内编辑反馈 |
| 41 | npm / pnpm 站点 | 包详情页的信息层次与引用芯片 |
| 42 | Chrome DevTools 2026 | 审计面板：性能/覆盖率的时间轴可视化 |

## C. 数据产品 / 看板（表格、图表、指标节奏）· 20 条

| # | 作品 | 可学要点 |
|---|---|---|
| 43 | Stripe Reporting | 图表是摘要、表格是事实；英雄指标只有一个 |
| 44 | Mercury | 编辑式排版 + 克制色彩，让金融数据显"贵" |
| 45 | Mixpanel | 渐进披露：先结论，再下钻 |
| 46 | HubSpot | 利益相关者报告：把结论做成可分享的组件 |
| 47 | Salesforce Lightning 2026 | 强默认值 + 可定制，避免"空着的高级感" |
| 48 | Looker Studio | 卡片与网格的呼吸节奏 |
| 49 | Tableau Pulse | 指标摘要卡：一个指标 = 一句结论 + 一个趋势 + 一个异常 |
| 50 | Observable | 数据叙事：文字与图表交替、可交互的图 |
| 51 | Recharts / Tremor 示例库 | 图表样式规范：轴线弱化、网格淡、色板受限 |
| 52 | D3 Gallery | 定制可视化的克制原则 |
| 53 | ECharts 官方案例 | 中文数据界面在深/浅色下的可读性 |
| 54 | Our World in Data | 长图 + 注释式图表（annotation-first） |
| 55 | Financial Times Visual Vocabulary | 按数据形状选图表（趋势/比较/分布/关系） |
| 56 | NYT 数据新闻 | 引导式滚动（scroll-driven）与数字滚动计数 |
| 57 | Pudding.cool | 叙事节奏中的留白与停顿 |
| 58 | DefiLlama | 高密度金融数据表在暗色下的可扫描性 |
| 59 | Wikipedia 数据表（Mobile） | 窄屏表格的降级与横向滚动体验 |
| 60 | Kaggle 数据集页 | 数据预览：前 N 行 + 类型 + 缺失率 |
| 61 | Datasette | 表格即产品：可分享的筛选与分页 |
| 62 | Retool 报表模板 | 打印/导出为 PDF 的版式考虑 |

## D. 设计系统 / 规范与工程化（token、组件、无障碍）· 22 条

| # | 参考 | 可学要点 |
|---|---|---|
| 63 | Material 3 Expressive | 动效作为结构元素；情感化形变有时间曲线规范 |
| 64 | Apple HIG（2026 版） | 深度、层级与玻璃材质的克制使用（仅 chrome，不上内容） |
| 65 | shadcn/ui | 组件原语 + 语义 token 的工程化落地方式 |
| 66 | Radix Primitives | 无障碍交互原语（focus 管理、键盘可达） |
| 67 | Tailwind v4（@theme） | token 单一来源，替代散落的自定义类 |
| 68 | Open Props / CSS 变量体系 | 用 CSS 变量表达完整设计尺度 |
| 69 | IBM Carbon | 数据密集型产品的网格与表格规范 |
| 70 | Atlassian Design System | 状态色语义与密度切换（comfortable/compact） |
| 71 | Shopify Polaris | 后台产品的表格、空态、错误态范式 |
| 72 | Ant Design 5（Token） | 中文后台的排版与表格密度基线 |
| 73 | GitLab Pajamas | 单一数据源的设计 token 与暗色模式 |
| 74 | Salesforce Lightning DS | 复杂产品的组件分类法 |
| 75 | Microsoft Fluent 2 | 状态、动效与无障碍的系统化 |
| 76 | Adobe Spectrum | 色彩对比与可访问性量化标准 |
| 77 | WCAG 2.2（AA/AAA） | 4.5:1 对比度、focus 可见、目标尺寸 ≥24px |
| 78 | Nielsen Norman Group（F 型扫描） | 关键指标左上、次要向右、细节向下 |
| 79 | 8pt Grid / Baseline Grid | 间距节奏的统一 |
| 80 | Tabular Figures 规范 | 数字等宽对齐（表格/指标） |
| 81 | Vercel Geist / Geist Mono | 开发者产品的字体双栈（无衬线 + 等宽） |
| 82 | Inter / Source Han Sans | 中英混排的可读性基线 |
| 83 | Skeleton 设计规范（Contentful/Polaris） | 骨架屏的时长与形状匹配原则 |
| 84 | Empty State Pattern（NN/g） | 空态作为"80% 感知精致度"的来源 |

## E. 趋势研究与评奖基准 · 18 条

| # | 来源 | 可学要点 |
|---|---|---|
| 85 | Awwwards SOTD 2026 集合 | 视觉节奏、材质、交互层被单独评分（Developer Award） |
| 86 | White Desert（SOTD 2026-09） | 高完成度的滚动叙事与性能表现并存 |
| 87 | Cerebrium（SOTD 2026-09） | 极简美学 + 扎实工程栈 |
| 88 | Ruinart Digital Fresco（SOTD） | 概念完整度：媒介与信息互相强化 |
| 89 | Jasmine Gunarto（SOTD + Dev Award） | 个人作品站的双奖标准：视觉与技术并重 |
| 90 | Odd Ritual（SOTD） | 材质与视觉节奏的完整度 |
| 91 | Squarespace Foundations | 设计系统的对外表达方式 |
| 92 | Aardvark Book Club / HOBRO Digital | 编辑式排版在品牌站的应用 |
| 93 | CSS Design Awards 2026 | 交互与可用性分项评分口径 |
| 94 | Brand Impact Awards 2026 短名单 | 策略清晰度优先于视觉新奇度 |
| 95 | iF Design Award 2026 | 无障碍与包容性设计作为评审维度 |
| 96 | Red Dot / D&AD 2026 Digital | 工艺与细节标准 |
| 97 | "AI dashboard trends 2026"（AYDesign） | 七大 AI 面板趋势（对话-画布/动作流/审批撤销/摘要卡/上下文/多模态/置信度） |
| 98 | "AI product design system guide 2026"（AYDesign） | AI 产品必备 10 组件与常见遗漏率 |
| 99 | "UI Design Trends 2026"（Framer Websites） | AI 原生界面 / 可变字体 / 动效即结构 / 玻璃拟态回归 / 编辑式粗野主义 |
| 100 | "Web Design Trends 2026: What Actually Ships"（Brainy） | Bento 成熟形态、微交互即注意力控制、每个动画都要传达信息 |
| 101 | "End of UI: Agents vs Dashboard"（DEV/Forrester） | 对话式 / 审批式 / 异常看板 / 环境式四种界面范式 |
| 102 | 2026 SaaS 面板评测（AdminLTE/Orbix/Webpo） | Linear（暗色克制）/ Stripe（表格）/ Attio（AI 原生）/ Vercel（单色）四大范式 |
| 103 | Daily Design（pomodiary）2026 系列 | 每日获奖与新品扫描，用于持续跟踪 |
| 104 | Design Inspiration Daily（crew.you） | 趋势聚类：编辑式 SaaS、calm interfaces、透明 AI affordance |

---

## 差距分析：SkillNet-S1 对照结论

**已具备（保持）**：Agent 动作流（阶段条 + 逐步明细）· 工具调用卡（步骤卡）·
摘要卡替代图表墙（AI 回复 + 本次任务总结）· 空态与起始提示（chips + 引导文案）·
Agent 时间线（关键路径 + 甘特条）· 溯源（产物链接 + 验收证据 + 运行记录）·
单色克制 + 状态色语义 · 中文排版基线 · 深色沉浸星图。

**本轮补齐（按缺失率排序）**：

| 缺口 | 参考 | 落地做法 |
|---|---|---|
| 流式状态 / 骨架屏（遗漏率 55%） | #83 #2 #3 | 运行中的结果卡显示骨架线条 + 阶段进度百分比 |
| 引用芯片 citation chip（75%） | #4 #43 | AI 回复中的产物名渲染为可点击芯片（打开产物） |
| 置信度指示（85%） | #4 #12 | Run Summary 增加"检索置信度分流"与"验收通过率"两项指示器 |
| 上下文抽屉（75%） | #2 #9 | 每轮显示"带入 N 轮上下文"，可点开查看实际带入内容 |
| Token 化与数字等宽（工程化） | #63–#80 | 统一 radius/spacing/状态色为 CSS 变量；数据一律 tabular figures |
| 动效即信息（微交互） | #99 #100 | 卡片进入淡入位移、阶段状态切换过渡、hover/focus 反馈 |
