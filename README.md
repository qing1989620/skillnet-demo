# SkillNet / S1 · 科研技能中枢

把科研方法与交付工具组织成 Agent 可检索、可执行、可验证的技能网络，让执行经验沉淀为下一次任务的能力。

这是面向立理 S1 的独立服务原型，提供技能发现、依赖编排、受预算约束的运行、产物验收和技能进化。已交付可运行的服务客户端与契约测试；**与 S1 线上系统的联调尚未完成**。接入边界见 [S1 接入说明](docs/s1-integration.md)。

## 启动与演示

需要 **Python 3.11+**。Windows 双击 **start.bat**；macOS / Linux 执行 **bash start.sh**。也可以手动启动：

~~~bash
python -m pip install -r requirements.txt
python run.py --no-browser
~~~

打开 **http://127.0.0.1:8848**。建议汇报按以下路径展开：

1. **打开首屏**：保留流动墨色背景与可拖拽的真实技能星图，点击「提出问题，展开内核」。
2. **汇报模式**：让问题、阶段、真实执行 DAG、代码/输出、价值说明和费用处于同一舞台。选择「数据分析与图表」，再点击「启动能力网络」；可继续追问，刷新页面会恢复同一个 Run。
3. **真实记录回放**：不新增模型调用，可暂停、调整速度和定位时间轴。阶段证据来自持久化事件；明确标注历史回放。
4. **核对交付**：查看本次七项内核贡献、独立验收结果、CSV/图表、SHA-256 和逐步代码。完成与验收通过分别计数；文件版本按步骤保留。
5. **原有完整演示**：保留「七阶段完整演示（本页）」、同题检索与执行对照、技能反馈前后变化、文件预览和会话历史。
6. **S1 接入**：展示服务契约、客户端和逐步接入方式。

现场讲解见 [领导演示说明](docs/executive-demo.md)。六个页面、全部功能视图、后端修复和桌面/手机截图见 [全产品优化与验收](docs/full-product-upgrade.md)。

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

当前 runtime 面向**单进程、受控环境**。模型生成代码运行于宿主子进程，清除凭据环境变量并限制执行时间；这不是对抗性代码隔离。接入企业用户前，需要独立执行容器或虚拟机、网络与资源限制、S1 用户/项目权限、共享任务队列与存储。详细方案见 [接入文档](docs/s1-integration.md) 与 [交付说明](docs/release-0.8.md)。

## 核心能力

- **技能契约**：能力、输入输出、执行步骤、适用条件、常见陷阱和验证清单；兼容 SKILL.md。
- **三档发现**：BM25、混合检索、关系扩展与模型重排。相关度是启发式信号，不是执行正确率。
- **依赖编排**：保留基础技能依赖；模型返回的坏边、未知技能与冲突关系被过滤或显式降级。
- **运行与验收**：后台 Run、依赖步骤、失败修复、确定性检查、语义评审、跨步产物传递和最终回复。
- **可追溯性**：原子持久化、事件序号、SSE 游标重连、运行恢复、请求级成本账本。
- **学习与进化**：任务条件化 LinUCB、轨迹蒸馏和质量准入；共享反馈与并发保存有锁保护。
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

GitHub Actions 在 Windows / Linux、Python 3.11 / 3.12 上执行离线回归、组件验证和前端资源检查。CI 不配置模型密钥，不运行付费实验。本次 206 项回归、真实执行与浏览器证据见 [全产品优化与验收](docs/full-product-upgrade.md)；早期交付记录见 [0.8 交付说明](docs/release-0.8.md)。

## 容器启动

~~~bash
docker build -t skillnet-s1 .
docker run --rm -p 127.0.0.1:8848:8848 \
  --env-file .env -e SKILLNET_TOKEN \
  -v skillnet-data:/app/data -v skillnet-out:/app/out skillnet-s1
~~~

先设置服务令牌。镜像使用非 root 用户并提供健康检查；首次 volume 初始化保留交付快照与实验记录。这个容器打包服务本身，生产环境仍需将代码执行放在独立的隔离环境。当前机器未安装 Docker，本轮未验证镜像构建。

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
