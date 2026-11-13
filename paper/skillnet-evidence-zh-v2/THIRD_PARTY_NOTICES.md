# 来源与模板说明

排版使用本机 TeX Live 中的 Elsevier CAS bundle 2.4（2024-05-04）。
官方模板类、公共样式和参考文献样式不在此数据包中重新分发。
`main.tex` 的 `Abstract` 环境对 CAS 公共实现作了本地适配，在零宽关键词覆盖盒中补入伸缩量；
另配置中文、字体兼容、作者元数据与研究稿页脚。类文件本身未修改。
CAS 文件头声明 LaTeX Project Public License 1.2 或以后版本：
<https://www.latex-project.org/lppl/>。

官方模板与使用说明：

- <https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions>
- <https://ctan.org/tex-archive/macros/latex/contrib/els-cas-templates?lang=en>

44 篇论文仅分发题录、阅读版本和本项目撰写的综述记录，不分发缓存全文。
固定第三方技能来源和提交见 `results/run-plan.json`；完整技能正文、API 请求材料、
私有账户快照、密钥和模型权重不进入压缩包。
正文关于 profiler 常量与接口的短摘录用于解释核验结果，其权利归原作者。

图表值均由随稿真实观测数据计算；借鉴的是图库示例的布局及配色思路，
没有复制其图像、科学数据或误差条定义。参考标识保留在 `figures/style-provenance.json`。
项目自有论文、代码和构造数据的后续公开许可由项目负责人决定；本文不替第三方授权。

新增网络原始数据来自UCI Machine Learning Repository，CC BY 4.0：
Iris, Fisher (1936), DOI 10.24432/C56C76；Wine, Aeberhard/Forina (1992), DOI 10.24432/C5PC7J；
WDBC, Wolberg/Mangasarian/Street/Street (1993), DOI 10.24432/C5DW2B；Banknote, Lohweg (2012), DOI 10.24432/C55P57。
官方出处、下载归档、日期及指纹保存在 `research/skill_network/results/sources-v2/sources.json`。
许可正文：https://creativecommons.org/licenses/by/4.0/ 。本研究增加归一化、目标映射及明确审计干预，
不将改造任务称为原始分类任务，也不宣称获得数据作者背书。
新增图只借鉴同组图库的点区间、二值矩阵及留白；参考图的SEM或模拟值不进入本研究结果。
