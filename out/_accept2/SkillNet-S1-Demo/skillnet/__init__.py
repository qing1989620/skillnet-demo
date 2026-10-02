"""SkillNet-S1：立理 S1 科研技能生态原型。

模块划分：
  schema     技能数据模型（技能卡 / 关系 / 质量评估）
  catalog    技能库构建、持久化、SKILL.md 导出
  index      BM25 + 稀疏向量索引
  retriever  混合检索与 Fabric 式路由
  bandit     LinUCB 上下文老虎机（技能选择）
  evolver    技能蒸馏 / 变异 / 交叉（技能进化）
  orchestrator 技能工作流编排
  agent      技能驱动的研究 Agent 执行器
  judge      LLM rubric 评审
  adapters   跨框架导出（Claude Code / Google ADK / OpenAI Tools）
"""

__version__ = "0.1.0"
