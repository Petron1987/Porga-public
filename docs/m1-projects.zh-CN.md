# v0.3：项目接管、受限组队与成果接受

这是 A1 / M1 的首个可运行切片，面向单人本地、公开或合成资料。默认离线，
尚未验收真实模型质量，不代表整个 M1 或长期自主进化系统已经完成。

## 接管前会确认什么

`project draft --goal "你的目标"` 保存草案，集中返回缺少的关键问题：

1. 交付研究报告，还是证据覆盖与缺口审计？
2. 什么结果算成功？写成可检查的验收条件。
3. 哪些事情明确不做？
4. 使用离线还是在线模型，每次运行最多允许多少次调用、多少美元？
5. 哪些公开/合成资料获准使用？

已填字段会保存，不再列为缺失字段。当前通过 CLI 返回问题和章程 JSON，
还没有聊天界面、自动采访或自行猜测关键答案。问题涉及授权时，不默认同意。
调用上限默认为 6 次，最低可配 4 次；一条正常链路使用 4 次，超限停止。
更多组织候选、多轮协作、持续调度和时间窗口管理仍在后续阶段。

## 实际操作

在项目目录打开 PowerShell。下面占位符来自上一条命令返回值，不要原样输入。

```powershell
.\.venv\Scripts\python.exe -m porga project draft --spec examples/charter-research.json
.\.venv\Scripts\python.exe -m porga project inspect PROJECT_ID
```

先查看 goal、success_criteria、non_goals、mode、max_usd、max_calls、data_scope
和全部 evidence。budget_scope 固定为 per_run：费用和调用限额按每次运行计算，
不是整个项目生命周期总额；同一数据目录另有共享每日费用上限。
修改示例后，用 `project revise PROJECT_ID --spec FILE` 追加新版本。
完整草案仍停在 `awaiting_owner_authorization`，不会自动运行。

```powershell
.\.venv\Scripts\python.exe -m porga project authorize PROJECT_ID --digest DIGEST --actor owner --note "已核对目标、边界、资料与预算" --confirm
.\.venv\Scripts\python.exe -m porga project run PROJECT_ID --mode mock --request-key my-first-project
.\.venv\Scripts\python.exe -m porga inspect RUN_ID
.\.venv\Scripts\python.exe -m porga report RUN_ID
```

授权绑定章程摘要与版本。章程修改后，新任务和最终接受均等待新版本确认。
恢复旧任务时固定旧授权与旧组织，不悄悄切换为新版本；旧成果不能替代新章程验收。
同一请求键只能复用相同项目、章程、输入和设置，不能借此跨项目复用。
预算取本地设置与已批准章程的较小值；离线项目费用记为 0，即使本机保留了在线价格。
在线授权还要求正数美元预算和明确在线模式。
当前模式是本机可信操作者模式，actor 是审计标签，不是登录认证。

## 两种实际团队

| 章程 deliverable | 受限执行者 | 工具 | 验证 |
|---|---|---|---|
| research_report | Research | 只读当前证据包 | 独立 QA + 来源/逐字引用检查 |
| evidence_audit | Evidence Auditor | 只读当前证据包 | 独立 QA + 来源/逐字引用 + 每项资料覆盖检查 |

Chief 生成结构化计划；内核核对计划与已授权交付类型，只从代码审核过的注册表创建角色。
每次运行保存独立 OrganizationRevision：角色版本、能力、权限、任务依赖与选择理由。
任务图是 Chief → Producer → QA；拒绝未知角色、工具、越权、超规模、循环依赖或缺少 QA。
模型不能添加代码、网络工具、审批工具或自定评估规则。

这是按两种交付类型选择团队的有限实现；不能声称已支持任意目标自主发明团队、
组织拆分合并、并行任务图执行或能力晋升。任务图当前是可核对的执行清单，
执行器仍是串行检查点工作流，尚不是通用任务图调度器。

成功条件和不做事项会传递给 Chief、执行者和 QA。硬门禁检查可判定的来源与覆盖，
自然语言验收条件仍需要 Owner 读成果判断。mock 的研究和 QA 输出是合成固定结果，
用于验证控制流程，不能代替真实资料分析或质量验收。

## 三个不同的人类决定

| 决定 | 命令 | 效果 |
|---|---|---|
| 启动授权 | project authorize | 允许按特定章程执行 |
| 成果接受 | project accept | 记录你认可这次结果，绑定章程、组织与成果摘要 |
| 进化建议审批 | approve / reject | 记录建议决定，不执行升级或发布 |

```powershell
.\.venv\Scripts\python.exe -m porga project accept PROJECT_ID --run-id RUN_ID --actor owner --note "已逐项验收，接受成果" --confirm
```

只有该项目当前已授权版本、已完成并通过验证的运行可以接受。
每个章程版本只接受一次；不满意时可先修订章程或重新执行，不能覆盖已有接受记录。
接受结果后，Evolution Proposal 仍保持待审批；批准提案也不会自动接受项目成果。
任何一项决定都不会部署变更。

## 数据升级与回退

SQLite user_version 从 1 升到 2，追加项目/章程/授权、运行绑定、组织和验收表。
旧记录、检查点、预算与决定保留；升级前写入 `pre-v0.3.sqlite3`。
旧版程序不能读取升级后的数据库。需要回退时，在单独目录使用旧版代码与升级前快照；
不要把新库直接交给旧版，也不要覆盖唯一数据副本。

`backup` / `restore` 包括全部新增记录，拒绝覆盖仅有草案的目录。
`restore` 接受当前数据库版本的备份。较旧备份应先复制到一个新的空目录，
命名为 `porga.sqlite3`，再使用新代码运行该目录的 `health` 完成升级与检查；
原备份保留。哈希可发现普通损坏，不提供针对本机数据库管理员的防篡改保证。

## 下一阶段

先用合成案例完成启动、查看和人工验收演练；再用一个有代表性的公开资料任务，
明确质量/成本通过线并由 Owner 选择是否开启在线模型。证明项目接管与交付可靠后，
继续 M2 持久任务队列、调度和恢复。外部文章/视频的定期学习、知识与 Skill 晋升、
独立对照实验、采用和回滚，仍分别属于 M2–M5。
