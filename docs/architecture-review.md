# 系统责任与审查不变量

已拉取 [AOCI-CODE 官方仓库](https://github.com/aoci-spec/aoci-code)，审查版本 `040d020442073dbc79aa924cd7f26fba80af056d`。参考其 F/R/A/S（功能、关系、接口、不变量）方法阅读本项目。这里是人工核对的核心架构图，不是 AOCI 运行时签发的全量认知索引；仓库已有空 Code Volume 不能作为“完整索引已建立”的证据。

| 责任 | 源码与关系 | 审查中必须保住的不变量 |
|---|---|---|
| 产品与权限入口 | `server.py` → 身份、队列、检索、执行、证据 | S1 签名身份覆盖同一 Run 的查询、事件、文件、取消与证据包。 |
| 技能供给 | `schema.py` / `catalog.py` / `resources.py` → 固定来源目录与资源快照 | 社区导入不等于执行认证；读取资源不导入模块，不读取包外文件；篡改文件不交付。 |
| 任务路由 | `retriever.py` / `semantic.py` / `index.py` → `orchestrator.py` | 检索分不是成功概率；推断相似关系不是实际执行依赖；降级必须可见。 |
| 选择策略 | `bandit.py` → `assessment.py` / `reward_gates.py` | 单次反馈仅在参数副本预演，不更新正式排序；其他技能不分享结果奖励。 |
| 执行与文件流 | `pipeline.py` → `executor.py` / `contracts.py` / `sandbox.py` | 步骤依赖对应真实输入；同名输出按步骤保留；失败和预算中止不能伪装完成。 |
| 独立评价 | `assessment.py` → `scenarios.py` / `research.py` | 执行前冻结参考；独立重读实际文件；只归属到被测文件的实际生产步骤；缺证据保留未知。 |
| 候选与奖励 | `governance.py` → `promotion.py` / `reward_gates.py` | 十二门全通过、完整留出对照、版本唯一、原子积分收据；不能覆盖已有技能；晋级不自动部署排序。 |
| 持久化与恢复 | `runtime.py` / `jobs.py` / `worker.py` | 原有记录不覆写；队列租约、进程写锁；重启恢复不静默重复付费任务。 |
| S1 生态交付 | `integration.py` → `evidence.py` / `resources.py` | 后端保存服务密钥；证据包与资源摘要校验；S1 自己落实项目权限和执行授权；不得宣称线上已接通。 |
| 全过程呈现 | 六页 HTML → `product.js` / `showcase.js` / 共享 CSS | 保留背景、星图、七阶段、回放、历史、跨轮追问；每个事实对应实际实体；模型评价与独立结果分开。 |

原始运行和产物是事实来源，架构文档与界面都是它们的解释层。证据包读取时重新核对文件字节，但沿用执行时的独立评价范围，不对历史结果事后补写标准或重新评分。
