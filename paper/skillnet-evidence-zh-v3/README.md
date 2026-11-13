# SkillNet中文论文v3：社区工具修复与外部轨迹验证

本文面向学位研究、汇报和导师审阅，未经独立同行评审。保留v2全部正负结果，新增355次社区原始/修复CLI执行、259次DeepSeek API尝试及明确的402中断，47篇研究论文、4份数据和1个软件引用。

首先阅读 `成果说明_先读这里.md`。正文第3.7节为最小修复方法，实验第5.8节起介绍原始CLI与外部轨迹，第6节开头三小节给出新增实测、评审负结果和自然工具联合回放。

从本目录运行 `./build.ps1` 编译官方CAS双栏中文论文，默认用户指定TeX Live目录，可用 `-TexBin` 指定其他位置。所有表图已经附带，无须重做付费实验。

在源码包根目录执行：

```powershell
python -m pip install -r requirements.txt
python -m research.skill_decision.reproduce
python -m research.skill_network.reproduce
python -m research.skill_external.reproduce
python paper/skillnet-evidence-zh-v3/reproduce.py
```

上述命令均不调用API。最后一条复核旧300次产物；新增条目复核258份HTTP200响应、402记录、355份CLI输出和探索性联合分析。完整609个提示可从固定上游源重建，见 `research/skill_external/README.md`，不会自动重试或继续计费。

原始完整第三方轨迹和技能文档不再次分发；提供材料指纹、范围索引、固定上游来源和本地重建脚本。新增单行修复副本仅在实验包内，不覆盖原始库或宣称上游已经采纳。源码、数据、许可和局限均保留，不能把构造或子契约通过当作通用质量认证。
