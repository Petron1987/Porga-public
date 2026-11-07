# 领域对象与协议演进 · A1 设计

以下是未来领域协议草案，不是当前 `src/porga/protocols.py` 已接受的输入。
同名对象需要版本迁移；不得将新增字段直接塞入当前拒绝额外字段的运行协议。

## 1. 身份、作用域和版本

统一身份关系：Workspace -> Project -> OrganizationRevision -> AgentBinding -> Task -> Attempt。
单人本地 Workspace 只有一个可信 Owner；不能把这个假设直接搬进多人服务。

每个持久对象至少包含 id、schema_version、revision、created_at、created_by、所属
workspace/project、数据敏感度与 provenance 引用。原始事件时间以 UTC 存储，界面按用户
时区展示。策略/预算日界线是显式配置，不能因显示时区变化悄悄改变。

分别维护软件版本、数据库迁移版本、协议版本、Agent/Skill 版本、组织修订、政策版本、
评估集版本和发布 ID。v0.2 不表示 P2 阶段，也不意味着组织已经进化两次。

## 2. Project 与 Project Charter

| 对象 | 目标字段 | 核心约束 |
|---|---|---|
| ProjectSpec/Charter | 目标、非目标、成功标准、预算/风险边界、数据范围、假设、里程碑、停止条件、Owner | Chief 可起草；不能自行扩大最终目标或资源 |
| BusinessModel | 利益相关方、价值链、假设、证据缺口、待验证预测 | 假设不能混为已验证事实 |
| ProjectRevision | 章程摘要、版本/哈希、适用政策、审批/生效时间 | 变更后旧任务保留旧版本；越界变更重新授权 |
| Blueprint | 领域约束、角色/Skill 建议、示例任务、验收与合成数据 | 不包含真实凭据/客户数据，也不能增加平台权限 |

Project Genesis 输出缺口和待决项；当关键成功标准或风险边界缺失时，集中请求决定，
不通过虚构约束让任务表面继续。日常执行细节尽量在已批准边界内自主处理。
完整交互见 [项目启动与目标验收](project-genesis.zh-CN.md)：复用有效资料、集中澄清、
确认章程，再启动；IntakeSession、QuestionBatch、EscalationRecord 和 AcceptanceRecord
记录问题来源、必要决定和最终接受，不能把未回复或模型自评当作 Owner 批准。

## 3. Capability、Agent 和 Organization

| 对象 | 目标字段 | 不变量 |
|---|---|---|
| CapabilitySpec | 标准输入输出、工具依赖、适用任务、验证方式、费用估算 | 描述能力需求，不直接授予工具 |
| AgentDefinition | purpose、输入输出 schema、模型配置引用、Prompt/Skill 版本、能力、评估/退役条件 | 版本不可变，凭据只引用不嵌入 |
| AgentBinding | AgentDefinition 版本、项目、角色任务范围、权限交集、资源限额、临时/持久类型 | 实际权限为平台/项目/角色/任务政策的交集 |
| OrganizationRevision | 角色绑定、职责边界、协作图、预期成本、基线版本和变更理由 | 至少满足能力覆盖和独立验证；不能用更多角色掩盖职责重叠 |
| AgentExecution | Binding/Release 引用、Task/Attempt、实际用量、状态 | 定义与执行实例分离；运行时不得跟随活动配置漂移 |

候选定义生命周期：draft -> candidate -> evaluated -> active -> deprecated -> retired -> archived。
评估不通过保留证据；deprecated 禁止新绑定但允许旧执行排空。归档保留 lineage，
不删除历史成果的可追溯版本。被撤销权限应立即阻止后续敏感动作，即使任务仍固定旧版本。

## 4. Task Graph、Attempt 与 Artifact

| 对象 | 必需内容 | 约束 |
|---|---|---|
| TaskGraph | 目标、节点、依赖、验收、预算、超时、最大迭代数、版本 | 单轮任务图采用 DAG；循环由显式有界工作流轮次表达 |
| Task | 输入引用、所需能力、分配角色、依赖、优先级、幂等键、acceptance_spec | completed 只表示执行交付，accepted 另由验证表达 |
| Attempt | attempt_no、Worker/lease/fencing token、开始/心跳/截止、版本快照、错误类别 | 重试不覆盖旧 Attempt；过期 Worker 不能提交新结果 |
| ArtifactManifest | 内容哈希、媒体类型、schema、生产者、输入/工具回执、版本、数据级别 | 内容和 manifest 分别可校验；hash 不是可信身份认证 |
| VerificationRecord | 被测 artifact/版本、规则/评估集版本、检查结果、证据、验证者 | 结果绑定精确内容；内容变化后验证不继续有效 |

Task 的 ready/leased/running/awaiting_action/reconciling/completed/cancelled/dead_letter 是
调度状态；成果 accepted/rejected/quarantined 是验证状态，二者分开。
当前 TaskSpec 的 completed/failed 不直接映射为业务成功，应通过迁移明确旧语义。

## 5. 知识、实验与采用对象

外部学习另有 ResearchWatchSpec、SourceRecord、ContentCoverage、ClaimRecord、
DistillationBrief、ImprovementHypothesis 草案，字段与边界见
[外部发现与蒸馏](external-learning.zh-CN.md)。其中来源覆盖度和作者自述状态不可省略，
这些对象进入现有知识/实验/采用链，不另设自批准权限。

| 对象 | 必需内容 | 关键约束 |
|---|---|---|
| MemoryRecord | 六类知识之一、项目/平台范围、来源链、适用条件、可信度、验证/有效期、版本 | 向量召回不能绕过访问范围和过期规则 |
| SkillPackage | 能力/输入输出、Prompt/声明式流程/工具引用、测试、所需权限、版本 | 不允许下载任意代码作为“Skill 晋升” |
| EvolutionProposal | 假设、问题证据、基线版本、候选差异、风险、范围、预期收益和停止条件 | 不能只给一段建议文案，也不授予采用权限 |
| ExperimentPlan | 基线/候选、开发集/留出集版本、指标、硬门禁、预算、对照方式 | 在结果出现前冻结验收和数据划分 |
| ExperimentResult | 案例级结果、失败/未知、费用/耗时、版本、可复现工件 | 单次自评或固定假数据不能证明改进有效 |
| ApprovalRecord | 行为/资源范围、候选及证据摘要、政策版本、批准者、有效期/撤销 | 所批准内容与执行内容摘要一致；变化后重新审批 |
| ReleaseManifest | Agent/Skill/组织版本、兼容协议、评估与审批、前一发布、回滚策略 | 发布是独立于批准的动作；一次项目只有一个活动发布代际 |

## 6. Commands、Events 与端口

命令是申请，事件是已持久化的事实。模型只能通过受限应用端口提交申请；不能自行
向事件总线写一条“已批准”事件来改变权限。

事件 envelope 包含 event_id、type、schema_version、workspace_id、project_id、
aggregate_id/revision、correlation_id、causation_id、occurred_at 和内容引用。
敏感原文不直接放进广播消息。命令幂等键与输入指纹绑定，复用同键异内容必须拒绝。

| 应用端口 | 输入/输出 | 调用边界 |
|---|---|---|
| ProjectService | 章程申请 -> 已批准项目修订 | Owner/受限 Chief 请求 |
| OrganizationService | 能力需求/候选 -> 校验后组织修订 | 不能自激活新版本 |
| TaskService | 有界任务图 -> Task/Attempt 状态 | Worker 提交需租约代际有效 |
| ToolGateway | 类型化动作意图 -> receipt/unknown/denied | 每次鉴权、预算与审计 |
| MemoryService | 授权 query/candidate -> 允许读取/晋升结果 | 服务端强制 scope，不接受模型自报范围 |
| EvaluationService | 冻结实验计划 -> 案例级结果/门禁 | 被测候选不能改验收 |
| ReleaseService | 已授权 manifest -> 激活/暂停/回退记录 | 绑定审批摘要及政策版本 |

实现先以 Python Protocol/应用服务为端口；没有跨进程需求时不强行建立 HTTP 微服务。

## 7. 数据演进与兼容

当前 runs/tasks/artifacts/proposals/decisions/events/reservations 保留。按里程碑逐步新增
projects、agent_definitions、organization_revisions、bindings、task_graphs、attempts、
outbox/inbox、memory_records/links、skills、experiments、approvals、releases 等对象。
旧 run 默认映射为隔离的 legacy 项目上下文；不能仅凭目标文字相似就合并数据范围。
只有 Owner 明确提供映射并通过访问检查，才可将多个历史 run 归入同一正式项目。

采用加法字段/表和显式转换器，先备份、迁移、校验，再切读写路径。旧版运行结果标记
legacy_origin，不伪造其不存在的评估、项目授权或实验历史。迁移不自动批准旧记录。

代码回滚与数据库回滚分别设计：优先使用兼容的前向迁移；不能为了切回 Agent 版本而
删除新数据列或恢复旧备份覆盖新成果。不可逆数据迁移需要单独审批和恢复演练。

## 8. 0.7 项目知识与 Skill 验收草案

以合成项目 A 的版本化文档审查为例。先保存来源快照与 `Evidence` 引用，再提出
带原文定位、适用版本和有效期的 `Fact`。独立核验后按政策激活。后续任务读取时，
服务根据可信执行上下文取得项目范围，先过滤范围、状态和有效期，再进行匹配。
`Hypothesis`、`Decision`、`Lesson` 和 `Skill` 各保留自己的证据与适用条件，
不能以某一类型的状态代替另一类型的核验。

| 用例 | 操作 | 通过条件 |
|---|---|---|
| K07-01 项目内复用 | 新任务按相同文档版本检索项目 A 已激活的事实 | 可查到来源快照、验证者、适用版本和消费该记录的任务 |
| K07-02 跨项目隔离 | 用项目 B 的身份搜索相同内容，或直接提供项目 A 的记录 ID | 查询和按 ID 读取都拒绝越界；结果、命中计数及错误不暴露项目 A 内容 |
| K07-03 来源变化 | 来源过期、被撤销或出现相互矛盾的新版本 | 阻止新任务默认使用受影响记录，可追查下游成果与 Skill；历史引用保留原版本 |
| K07-04 状态边界 | 导入原文、缺来源的判断或一条待验证假设 | 原始资料与候选可审查；没有核验和合规激活证据的记录不能作为已验证事实使用 |
| K07-05 声明式 Skill | 比较一个待评估的项目内清单方法与现有基线，再提交缺证据或额外权限的变体 | 评估与审批绑定包版本、用例和摘要；变体被拒绝，激活不扩大工具权限 |
| K07-06 旧数据迁移 | 升级一份含旧成果、旧审批和未结算预留的隔离样本 | 旧记录保留原归属和历史语义；缺失的来源或验证标为未知，预算和授权不会被重建 |
| K07-07 恢复与隔离 | 演练迁移失败、重复迁移和旧版快照恢复 | 事务失败不留下半成品；同版本复查结果一致；在兼容版本和独立数据副本中完成回退 |

默认只允许项目内复用。跨项目发布须单独审查来源、脱敏结果、权限和独立验证，
并按精确版本重新授权。记录迁移前后的协议/数据库版本、输入摘要、记录与依赖校验、
失败状态和恢复结果。知识与 Skill 的目标状态见[知识与进化设计](evolution-memory.zh-CN.md)。
