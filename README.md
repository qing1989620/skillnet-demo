# SkillNet / S1 · 科研能力生态

把科研方法与交付工具组织成 Agent 可检索、可执行、可验证的技能网络，让执行经验先接受独立检验，再决定是否沉淀为能力。

这是面向立理 S1 的独立服务原型，提供技能发现、依赖编排、受预算约束的运行、产物验收和技能进化。已交付可运行的服务客户端与契约测试；**与 S1 线上系统的联调尚未完成**。接入边界见 [S1 接入说明](docs/s1-integration.md)。

**[产品说明](docs/product-guide.md)**：产品定位、业务价值、核心能力、应用场景与 S1 协同方式。环境配置、页面操作及工程验证见 **[技术部署与操作说明](docs/technical-operations.md)**。

**完整交付版：`2026.10.13-complete.15`。** [正式 PDF](docs/SkillNet-S1-产品说明.pdf) 与全部前后端、技能资源和部署文件一起维护。全新克隆后先运行 `python tools/verify_delivery.py --strict-runtime`，确认文件 SHA-256 清单一致，再启动服务。安装版本、旧服务排查和交付范围见 [完整交付核验](docs/delivery-parity.md)。

**10 月 13 日：产品总览与正式文档更新。** 界面预览已同步当前内核实验室和球体能力网络；交付依据按能力资产、真实产物、经验准入和工程验证组织。产品说明与技术操作文档分别维护，页面更新及断点观察见 [本次界面核验](docs/frontend-audit/delivery-ui-review.md)。

## 一次科研任务，留下可交付、可复核、可积累的资产

**10 月 12 日：状态契约进入真实执行。** 执行前冻结条件并核验真实输入，失败/未知阻断代码生成；执行后检查效果、独立复算并核对交付字节。11 类反例探针实际启动 39 次 Python；真实科研任务经过三次问题定位后达到 20/20 独立检查，正式策略未更新、未发奖。全站异步鲁棒性和双尺寸浏览器验收同步完善，保留球体与七阶段。见 [本轮实现、完整失败记录与边界](docs/state-kernel-delivery.md) 和 [前端审计](docs/frontend-audit/review.md)。

本项目以成熟技能生态为基础，为 S1 提供方法发现、真实执行、独立结果范围与候选经验治理。全面审查、自我评价、生态对照和当前边界见 [产品生态审查](docs/ecosystem-review.md)，核心职责与不变量见 [架构审查](docs/architecture-review.md)。

默认回放已切换为状态契约科研复核（10 月 12 日最终记录）：三步完成，五个真实文件与冻结输入，20/20 独立检查，费用 ¥0.2048；识别样本泄漏并重算留出集指标。新增 S1 证据包 HTTP/SDK 契约，以及 1,769 个社区技能包、10,898 个资源文件的按需读取与指纹核验。候选仍需十二门准入，本次正式网络更新为 0。经营分析、追问、历史回放、背景与星图均保留。

**10 月 13 日：真实联网与隔离方法补充。** 宿主搜索公开来源，冻结 URL、HTTP、时间、正文与快照指纹；人物任务先通过身份门，再进入著作分析。本地方法不足时可发现最多两个有许可、固定提交的在线 Skill，作为运行级方法参考。前端与 S1 证据包呈现来源和核验结果；禁网、未知与失败保持可见。见 [联网研究与实测](docs/web-research.md)。

**技能自检索是任务入口。** 从问题筛选少量有用 Skill，允许少选与空选；编排复用同轮候选池。前端显式呈现推荐、采用理由和实际参与，S1 证据包同步保留。首页流动背景和表面体系延续到页尾。本轮行为核验、真实探针与视觉验收缺口见 [检索与整页呈现复核](docs/retrieval-and-presentation-review.md)。

**能力球体与状态变化。** 首页、内核现场和完整星图共用可旋转的真实技能球体，保留七阶段与执行 DAG。节点可查看适用条件和失效边界；结果区直接连接实际输入、登记产物与独立检查。新增只读能力报告及 S1 SDK 摘要核验，展示证据缺口，不把一次任务当成因果认证。研究对照、实测与视觉验收边界见 [能力球体复核](docs/capability-sphere-review.md)。

## 本轮升级：1,769 个独立社区 Skill

全新拉取仓库的交付基线为 **1,881 个 Skill**：76 个种子、1,769 个 GitHub 社区 Skill、36 个已有演化 Skill。本机后续运行曾积累至 1,881 个，历史截图与报告保留拍摄时读数；当前运行规模以 API 为准。社区包按正文去重，保留原文、资源、许可证、固定提交与哈希；Stars 属于来源仓库，导入不等于执行认证。

六页面优化、千级星图与分页、真实文件依赖、验收修复、跨轮文件版本、候选治理、语义检索、签名身份和独立 worker 的实现与证据见 [本轮交付说明](docs/scale-upgrade.md)；来源见 [锁定清单](config/skill_sources.json)。完整在线经营任务和同文件追问已通过独立核验；Linux Docker 实机验证通过。四组学习前后配对未测出增益，候选保持隔离；S1 线上联调仍待真实接口与环境配置。

**10 月 9 日：修正“问一次就优化网络”的错误假设。** 方案模型评分不再作为共享奖励；实际结果需要执行前冻结的独立判据，无法判断就保留未知。单次经验只做影子预演，正式权重不更新；候选晋级需要预注册的完整留出评测。两次真实任务同为 8 分，却分别得到“已测范围通过”与“未知”，正式参数指纹始终一致。机制、边界与原始证据见 [凭什么判断结果与学习增益](docs/outcome-evidence.md)。

**10 月 10 日：十二道门全部通过，才给提升奖励。** 奖励规则与阈值提前冻结，后端逐门核验真实产物、技能版本、公平留出对照、无退步和可靠增益；任何失败或未知都会拦截。全部通过后，只给被验证版本写入有上限的积分和唯一凭证。前端可展开每道门的约束、证据与原因；机制与真实实测见 [十二门奖励准入](docs/reward-gates.md)。

完整默认安装已包含本机同版多语言语义模型。首次启动从仓库携带的模型包恢复，不访问模型下载网站；可手动修复：

~~~bash
python -m pip install -r requirements-semantic.txt
python tools/setup_semantic_model.py
~~~

普通 clone 包含约 85 MB 模型包，无需 Git LFS；逐文件校验与本机相同的固定版本和 SHA-256。默认 `/api/health` 应显示 `encoder.kind=dense-onnx`。显式选择词法模式或缺失推理依赖时保留可见回退，见 [模型资产说明](assets/semantic/README.md)。

## 启动与使用

需要 **Python 3.11+**。Windows 双击 **start.bat**；macOS / Linux 执行 **bash start.sh**。也可以手动启动：

~~~bash
python -m pip install -r requirements.txt
python run.py --no-browser
~~~

打开 **http://127.0.0.1:8848**，可以浏览球体能力网络、检索技能、发起任务及检查历史记录。公开科研与经营任务支持阶段回放、文件预览和独立检查；回放不新增模型调用。详细配置与操作见 [技术部署与操作说明](docs/technical-operations.md)，历史版本的截图和验证记录见 [全产品优化与验收](docs/full-product-upgrade.md)。

| 页面 | 地址 |
|---|---|
| 产品总览 | / |
| 独立对话工作台 | /chat |
| 交互式技能网络 | /graph |
| 运行中心 | /runs |
| 执行回放 | /run?id=<run_id> |
| 内核实验室（七个功能页） | /dashboard |
| API 文档 | /docs |
| 接入能力清单 | /api/integrations/s1 |

产品总览、技能详情、冻结实验与历史回放无需模型密钥。完整面板支持无模型的 BM25 / Hybrid 检索。需要真实执行与进化时，把 **.env.example** 复制为 **.env** 并配置 **DEEPSEEK_API_KEY**，然后重启服务。不要把 .env 上传到仓库。

## 访问与运行边界

本机演示默认无需访问令牌。监听非本机地址时，run.py 要求配置 **SKILLNET_TOKEN**。调用付费或写入接口时传 **X-SkillNet-Token**，也支持 Bearer 认证；浏览器的「连接设置」可以保存令牌到当前标签页会话，并通过只读接口验证。

~~~bash
# 先在环境中配置 SKILLNET_TOKEN，再启动内网监听
python run.py --host 0.0.0.0 --no-browser
~~~

Fabric 重排会调用模型，因此同样需要令牌保护。公开健康接口不返回密钥；响应提供 X-Request-ID 便于追踪错误。

默认同时运行最多 4 个后台任务，超过上限返回 **429** 与 **Retry-After**。可用 SKILLNET_MAX_ACTIVE_RUNS 调整；每个 Run 都有独立费用、调用数和时间预算。取消与预算检查覆盖检索、编排、执行、验收和收尾阶段；已发出的模型请求或正在执行的子进程会在检查点结束后停止后续步骤。费用预算按服务返回的 usage 核算，在途的并行模型请求可能小幅超限。

默认使用 API 进程内线程与宿主子进程；可启用 **单主机 SQLite 持久化队列 + 一个独立 worker**，API 重启与执行互不绑定。签名身份提供租户/用户/项目范围检查。可选 Docker 执行模式禁止网络、限制资源并在 Docker 不可用时拒绝降级；Linux CI 的 [实际容器验证](out/docker-smoke.json) 已通过，Windows Docker 未验证。Linux worker 使用拥有共享工作目录的非 root 账号。宿主子进程仅适用于受控演示。详细方案见 [接入文档](docs/s1-integration.md) 与 [交付说明](docs/release-0.8.md)。

## 核心能力

- **技能契约**：能力、输入输出、执行步骤、适用条件、常见陷阱和验证清单；兼容 SKILL.md。
- **三档发现**：BM25、混合检索、关系扩展与模型重排。相关度是启发式信号，不是执行正确率。
- **依赖编排**：保留基础技能依赖；模型返回的坏边、未知技能与冲突关系被过滤或显式降级。
- **运行与验收**：后台 Run、依赖步骤、失败修复、确定性检查、语义评审、跨步产物传递和最终回复。
- **真实联网**：公开搜索、来源快照与引文绑定、身份前置门、运行级隔离技能参考；允许关闭联网，未知不当作通过。
- **能力边界研究**：有限状态规划、定向执行与重观测、独立反例及登记子集实验；结果有明确任务族与环境范围。
- **可追溯性**：原子持久化、事件序号、SSE 游标重连、运行恢复、请求级成本账本。
- **经验与准入**：任务条件化 LinUCB 影子预演、轨迹蒸馏、候选隔离与十二门版本奖励；单次任务不更新正式排序，共享保存有写锁保护。
- **跨框架使用**：标准技能目录导出；真实的 search_skills / load_skill 工具处理器实现渐进披露。

技能规模来自 API 实时读数。克隆后从 data/library.baseline.json 恢复交付基线，随后运行数据保存在 data/library.json。新运行不会覆盖历史结果。

## 接入现有 Agent

~~~python
from skillnet.integration import ClientConfig, SkillNetClient, skill_tools

with SkillNetClient(ClientConfig(base_url="http://127.0.0.1:8848")) as client:
    tools = skill_tools()
    result = client.call_tool("search_skills", {"query": "单细胞测序质控与聚类", "k": 3})
    if result["selected"]:
        contract = client.call_tool("load_skill", {"name": result["selected"][0]})
        # 把 contract 作为工具结果返回给现有 Agent。
~~~

客户端复用 HTTP 连接，校验参数，支持预算 Run、事件订阅、取消、产物大小与 SHA-256 验证，并对错误脱敏。S1 后端保存用户/项目与 Run 的权限映射，服务令牌用于服务间认证。

## 验证

~~~bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python verify.py
node tools/front_check.js
node tools/check_web.js
node tools/product_check.js
node tools/briefing_check.js
node tools/showcase_check.js
# 以下需要服务已启动
python tools/selfcheck.py
python tools/full_audit.py
~~~

GitHub Actions 在 Windows / Linux、Python 3.11 / 3.12 上执行离线回归、组件验证和前端资源检查，另有 Linux Docker 执行隔离 smoke。CI 不配置模型密钥，不运行付费实验。10 月 13 日代码本地验证为 **1,086 项 Python 测试、31 项离线自检和 12 组 Node 检查通过**；最终提交状态见 [GitHub Actions](https://github.com/qing1989620/skillnet-demo/actions)。225 项及 206 项等旧记录分别保留在 [千级技能升级](docs/scale-upgrade.md) 和 [全产品优化与验收](docs/full-product-upgrade.md)，反映当时版本。

## 容器启动

~~~bash
docker build -t skillnet-s1 .
docker run --rm -p 127.0.0.1:8848:8848 \
  --env-file .env \
  -v skillnet-data:/app/data -v skillnet-out:/app/out skillnet-s1
~~~

先在 `.env` 设置 `SKILLNET_TOKEN`。镜像使用非 root 用户并提供健康检查；首次 volume 初始化保留交付快照与实验记录。这个容器打包服务本身，生产环境仍需将代码执行放在独立的隔离环境。CI 已验证 `deploy/Dockerfile.executor` 对应的 Linux 执行容器；本节根目录服务镜像命令及 Windows Docker 仍需在目标部署环境验收。

## 代码与证据

| 位置 | 内容 |
|---|---|
| server.py | FastAPI 接口与后台运行 |
| skillnet/ | 技能、检索、编排、执行、验收、进化与接入客户端 |
| web/ | 原生 HTML / CSS / JavaScript 前端 |
| seed/skills/ | 种子技能的标准目录 |
| data/library.baseline.json | 可复现的交付技能快照 |
| out/exp*.json | 冻结的实验原始记录 |
| tasks/benchmark.json / tasks/heldout.json | 调参与冻结评估任务 |
| tests/ | 离线回归与接口契约测试 |
| docs/ | 接入、技术与研究说明 |

冻结评估集的历史结果与当前技能库规模分别展示。旧报告反映对应版本的实验，不代表本轮扩充后的在线效果；不将小样本检索差异解释为生产收益。论文与方法来源保留在 [文献笔记](docs/references.md)，既有实验记录和技术说明保留在 docs/。


### 能力边界研究与现场实验（2026-10-12）

新增有限状态组合规划、定向执行后重观测、独立反例复核及固定任务集最小登记子集实验。最终391次真实Python调用中，有效任务完成覆盖为2/16（直接执行）、2/16（仅声明规划）、16/16（重观测）；主动方法实际调用更多，结果只适用于冻结的公开模拟CSV任务族。原始失败、20种随机顺序和全部32个子集均保留。

六个页面均可打开“能力边界实验”；首页可回放进入真实问答链路的本轮科研任务（20/20独立复核）。实验没有自动更新正式技能或奖励。方法、复现命令、两轮归档修复及结论边界见[研究结果](docs/frontier-results.md)。
本轮球体交互进一步连接了领域聚焦、键盘技能搜索、有方向的关系探索、按真实步骤查看文件与核验证据，以及保留运行上下文的跨页跳转；原有背景、自检索与七阶段演示保留。[实现与验证范围](docs/exploration-interactions.md)。
