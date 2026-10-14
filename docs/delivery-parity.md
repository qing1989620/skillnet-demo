# 完整交付与一致性核验

交付版：`2026.10.14-complete.21`。日期：2026-10-14。

19 版补入个人能力网络的前后端、可预览的训练候选、四组预训练／微调检查点及完整复现脚本。克隆后无需重新训练即可对照排序；候选仍受十二门约束，发布文件不代表自动晋级。首轮正负实验见 [研究报告](learned-network-research.md)，数值资产与来源见 [模型卡](../data/network-model/MODEL_CARD.md)。正式 PDF 保留先前产品说明，新增研究功能与验证边界以本页及研究报告为准。

20 版补入第二轮继续训练证据与全部六组候选、个人作用范围保护、候选报告／权重版本绑定及页面配置恢复。`/api/personal` 的 `model_candidates.v2.available=true`、`evidence_bindings.v2.verified=true`，模型为 `network-b747f23c038d5521`。两轮候选都只作研究对照；完整新结果见 [继续训练与作用范围](continual-routing-research.md)。个人原始问答和个人支持向量继续保留在本机，不随克隆上传。

21 版补入条件收益与失败边界的两轮冻结研究、80 道封存任务、48 次真实 API 对照、全部物理证据和 `/utility` 前后端。研究摘要见 [条件收益与失败边界](conditional-utility-research.md)。克隆后运行 `python tools/verify_conditional_evidence.py` 可离线复核 2,684 次真实程序的产物，不需要重训或消耗 API 额度。正式路由与奖励不因研究结果自动更新。

## 本次纠正的问题

此前前后端源码已经进入 main，但新 PDF 尚未入库，交付技能快照为 1,876，与本机的 1,881 不同。旧快速开始仍写着 98 个技能，三个 PDF 入口和打包白名单也停留在早期内容。因而“源码已推送”不能代表整个交付与本机产品一致。

本次同步技能库正文及统计快照，补入正式 PDF，统一旧 PDF 路径，更新快速开始和完整打包方式，并增加逐文件 SHA-256 清单。历史提交中的浏览器临时目录退出版本控制，本机文件保留。启动脚本固定进入自己的项目目录，在端口绑定成功后才等待本进程健康状态并打开浏览器，避免新服务启动失败后误看旧服务。

## 交付范围

| 内容 | GitHub main 与交付包 |
|---|---|
| 前端 | 所有页面、JavaScript、CSS、球体组件、图片与当前界面预览 |
| 后端 | 服务入口、完整 skillnet 库、检索、执行、联网、候选门控及 S1 SDK |
| 技能资产 | 76 个种子、1,769 个社区 Skill、36 个已有演化，共 1,881 个；10,898 个社区资源文件 |
| 文档 | 正式产品 PDF / Markdown、技术部署、接入契约与研究证据 |
| 语义模型 | 与本机相同的固定 ONNX 模型包，首次启动离线展开，逐文件校验；默认 CPU 稠密语义检索 |
| 工程 | 测试、验证工具、依赖声明、Docker、worker 与 GitHub Actions |
| 公开回放 | 已登记公开案例及补入的公开模拟、Crossref 核验记录与产物，保留失败/部分完成状态 |

`config/delivery-manifest.json` 记录交付文件的路径、长度和 SHA-256，`config/delivery.json` 记录发布标识与清单摘要。默认核验跳过允许持续变化的 `data/library.json`；`--strict-runtime` 同时检查其初始字节。运行日志、自检输出与进程环境属于可变状态。

公开仓库不包括 `.env`、服务令牌、模型缓存、私有任务原始问答、临时数据库和进程锁。它们不是缺失的前后端组件。新电脑使用自己的模型密钥；S1 生产账号、权限和附件系统仍需实际联调。完整产品一致性与个人运行历史一致性分别核对，不能将后者自动当作公开资料。

## 全新克隆验收

```bash
git clone --branch main https://github.com/qing1989620/skillnet-demo.git skillnet-demo-complete
cd skillnet-demo-complete
python tools/verify_delivery.py --strict-runtime
python -m pip install -r requirements.txt
python run.py --version
python run.py --no-browser
```

校验应显示 `ok: true`、`differences: []` 和本页的发布标识。`/api/health` 应显示首页版本 `2026-10-14.complete.21`、1,881 个初始技能，`encoder.kind=dense-onnx`，以及 `distribution.release / git_commit / source_tree_sha256`。`/api/personal` 的 `model.available=true`，候选模型为 `network-b9e7622390ddc716`；它保持隔离对照。Git 克隆的提交还应与 `git ls-remote origin refs/heads/main` 相同。

若 8848 已被旧服务占用，新启动会明确退出；先关闭旧服务，或运行 `python run.py --port 9000 --no-browser`，然后打开 9000。浏览器“连接设置”若曾指定其他服务器，也需核对连接目标。

已有目录先检查 `git status` 与当前分支；不要使用 `reset --hard` 覆盖自己的任务或密钥。需要核验完整初始产品时，优先使用上面的新目录安装。

## 完整交付包与 PDF

```bash
python tools/package_deliverable.py --output ../SkillNet-S1-Demo.zip
```

打包工具只读取已经核验的同一份清单，不再用手写目录白名单遗漏组件，也不递归带入本机秘密和缓存。解压后可运行相同校验命令；GitHub 下载 ZIP 没有 `.git`，此时 `git_commit` 为 null，仍能用清单摘要确定产品版本。

正式文档为 [产品说明 PDF](SkillNet-S1-产品说明.pdf)。`docs/SkillNet-S1-guide.pdf`、`docs/SkillNet-S1-交付报告.pdf`、`report/SkillNet-S1-report.pdf` 与 `output/pdf/SkillNet-S1-产品说明.pdf` 是同版 PDF 的兼容路径，内容哈希一致。

## 多行问题与结构化数据

完整实机录像前发现首页的单行输入会删除示例 CSV 换行，真实效果契约阻断了错误输入产生的结果。17 版将任务输入改为多行文本框，保留完整示例与粘贴数据；Enter 提交，Shift+Enter 换行，输入法选字不提交。重新通过真实前端入口执行科研复核并核验产物。

## 连续追问与输入继承

18 版修复第三轮追问缺少原始表格的问题。明确引用前文且没有指定 artifact_refs 时，从最近三轮已授权运行中合并文件；相同逻辑名取最近版本，最多携带 16 个文件。跨轮输入可以继续继承，历史前缀不再无限增长。显式指定版本仍优先；每个来源的身份范围、登记 SHA 和物理字节均重新核验，缺失或篡改拒绝入队。失败的最新一轮不会遮蔽较早的有效上下文文件。新增真实 HTTP 边界回归覆盖五轮继承、新版本覆盖、失败后继续引用、篡改拦截与较早上下文越权拒绝。

20 版发布冻结从 Git 索引读取 `data/library.json` 的公开初始快照，避免把本机服务刚产生的私有运行状态误作交付内容。默认核验跳过该可变文件；全新克隆仍应通过 `--strict-runtime`。
