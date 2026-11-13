# 证据约束技能判别器 v1

成果入口：[中文方法与实测报告](METHOD_REPORT_ZH.md)。
这是已经实现并运行的规则＋产物验收方法，输出具体缺陷、来源和已测能力边界；没有训练神经质量分类器。
本阶段新增API调用与费用均为0，适用于学位论文、课题汇报和导师审阅。

## 直接演示

在项目根目录和现有研究 Python 环境运行：

```powershell
& '..\.venv-skill-quality\Scripts\python.exe' -X utf8 -m research.skill_decision.demo
```

或者运行 `research/skill_decision/demo.ps1`；可用 `-Python` 指定 Python 3.11/3.12。
演示读取已记录结果并先离线复核，不调用API、不重新执行社区脚本。
所需离线运行库是 pydantic（项目现有环境已安装），见 `requirements.txt`。

扫描本地技能包：

```powershell
python -m research.skill_decision.cli scan seed/community/skills/gh-claude-senior-ml-engineer-9b50c5
python -m research.skill_decision.cli scan 你的技能包目录 --manifest 可选的文件哈希清单.json
```

扫描器只读受限文本、解析AST，绝不导入被扫描包。没有可信上游清单时，当前快照不代表来源认证。
通用扫描器目前提取主 `SKILL.md` 的字面Python示例；冻结D1批量审查另外解析全部登记Markdown。
动态解析器、复杂依赖与未覆盖的行为保持未知。无脚本的咨询技能不会被直接判差。

## 已完成实验

- 自建60个父配置×10个版本=600例，40/20父配置隔离。测试侧140个已知机械缺陷全部检出，40个无害对照零误报；另20个范围未知例不自动放行。
- 自编12个实现，三个任务族，每个24个输入，共288次实际产物执行；完整方法保留3个正确实现、识别9个缺陷实现。
- 冻结D1真实社区包200个：1个包含3条明确接口冲突，199个缺少充分行为证据。
- 原项目文档均分、只看参数名、标准库接口参照、静态门控与去掉各层的消融全部保留。

这些是构造诊断和只读真实应用，不能写成真实社区整体质量准确率100%。
原项目文档分是启发式排序先验；“≥0.8即可接受”是本轮固定对照适配，不是生产策略，也不是发表版SkillNet/SkillCT复现。

## 数据与复算

`results/diagnostic-v3/` 是最终构造实验，含600个自建输入包版本、72个行为输入、288份真实产物、
4896条方法决定、回执、汇总、首个结果前冻结的方案和源码快照。
`results/natural-v3/` 是200个真实包的诊断。只发布元数据和必要证据窗口，不重新分发完整第三方包。
首轮v1结果另行保留；v2在本机不可覆盖目录。最终v3修正精确输入范围、完整观察计数和Windows源码字节一致性。

```powershell
python -m research.skill_decision.reproduce
python -m pytest research/skill_decision/tests -q
```

复算不执行程序，只核对指纹、重新做静态判断与产物验收。新执行实验必须选择新ID：

```powershell
python -m research.skill_decision.benchmark --output out/research/skill-decision/NEW-ID
```

本地执行器只允许运行本项目自编白名单源码，环境不继承API密钥；它不是不可信代码沙箱。
Linux Docker复现使用相同固定测试，关闭网络、只读挂载、非root及资源限额；不重复增加独立样本数。
本仓库为公开仓库，常规标准GitHub托管runner按[官方说明](https://docs.github.com/en/billing/concepts/product-billing/github-actions)免费。
本阶段新增工作流不上传持久化实验产物、不增加缓存，紧凑结果写入作业日志。

## 方法与证据的边界

包指纹、任务类型、逐输入哈希及独立产物记录共同界定已测范围。
同任务类型的新输入没有登记证据时仍返回超范围；不把未验证解释为不能完成。
运行器内部登记的回执ID是信任入口，任意用户提交的成功JSON不会被默认信任。
主机和运行器本身并非本方法能够认证的安全边界。

继承组件来自本仓库提交 `216c93e763357017e318bb324349ff05a88357a3`：
`research/skill_study/cli_contracts.py`、`package_audit.py`、`research/skill_quality/manifest.py`、
`schemas.py` 及 `skillnet/schema.py`。原冻结研究源码没有修改。
完整语义质量金标准、跨来源外部验证和一般化能力区间仍待建立。
