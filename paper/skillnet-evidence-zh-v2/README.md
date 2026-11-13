# SkillNet两项方法：中文研究论文 v2

面向学位研究和导师审阅，使用官方Elsevier CAS双栏2.4、XeLaTeX与中文字体。未投稿，未经独立同行评审。

第3.6、5.5、6.1节给出技能判别器；第4、5.6–5.7、6.2–6.4节给出ECP网络方法、强对照、消融、成本与12/24组合反例。自然包研究与18个自建算子网络分开。

从本目录执行 `./build.ps1` 编译。默认用户指定的TeX Live路径，可传入 `-TexBin`。不启用shell escape，所有表图已附带。CAS本地适配包括中文/数学字体兼容、摘要关键词覆盖、研究稿页脚、ORCID空脚注与LastPage总页数；未改系统模板类。

在交付包根目录（含research和skillnet）运行：

```powershell
python -m pip install -r requirements.txt
python -m research.skill_decision.reproduce
python -m research.skill_network.reproduce
python -m research.skill_network.reproduce --execute
python paper/skillnet-evidence-zh-v2/reproduce.py
```

最后一项复核旧300次产物，所有复现均不调用模型API。可选重执行只运行固定自建worker，不接受社区代码。

原仓库的build_assets.py重建历史表，build_new_assets.py重建新增六表和三种真实数据图。源码包直接使用已附带的表图即可编译。新网络逐条记录位于research/skill_network/results，判别器记录位于research/skill_decision/results。版本和输入指纹可核查；所有重复预算、ID置换和容器复现都不增加独立任务数。

48条参考文献含44篇研究论文和4份UCI数据，不能称为48篇顶刊。来源和许可见THIRD_PARTY_NOTICES.md。成果说明_先读这里.md提供可直接汇报的方法、结果及限制。
