# Porga：单人本地试运行手册

v0.3 增加章程授权、两类受限团队和独立成果接受，见 [项目接管流程](m1-projects.zh-CN.md)。
以下恢复与预算规则继续适用；原 demo/run 是保留的内核演练入口。

v0.4 的外部项目使用自己的配置和状态目录，见 [外部接入契约](external-project-contract.zh-CN.md)。
升级 v0.3 数据前保留 pre-v0.4.sqlite3，数据库版本为 3；旧代码应使用升级前快照。

适用范围：一位可信任的本机用户，处理公开或合成资料。当前支持可重复的离线试运行，
在线模式的真实模型质量仍需人工验收。没有多人服务、自动代码进化或生产业务托管。

## 1. 检查与首次运行

在项目目录的 PowerShell 执行：

```powershell
.\.venv\Scripts\python.exe -m porga doctor
.\.venv\Scripts\python.exe -m porga readiness
.\.venv\Scripts\python.exe -m porga demo --mode mock --request-key my-first-trial
```

`readiness` 分别报告本地离线试运行条件和在线配置情况，不会把缺少真实模型验收的
系统标成已经投产。mock 使用真实 SDK 编排，但模型输出与 Token 数是固定演示数据。

同一个 `request-key`、任务输入、运行配置会返回原有结果，不再调用模型。修改目标
或预算后请用新 key。未完成的旧任务不会因重复提交而悄悄重跑，需要明确恢复。

## 2. 自己的第一个任务

编辑 `examples/project.json`，填写目标和证据。每条证据包含唯一 ID、标题和原文；
限制为 1–8 条、每条 8–4000 个字符，最终请求还受总输入大小限制。不要放客户资料
或内部商业数据。运行：

```powershell
.\.venv\Scripts\python.exe -m porga run --mode mock --project examples/project.json --request-key research-001
.\.venv\Scripts\python.exe -m porga status
.\.venv\Scripts\python.exe -m porga inspect RUN_ID
.\.venv\Scripts\python.exe -m porga report RUN_ID
```

`report` 在 `.porga/reports` 生成 Markdown 和完整 JSON，包含报告、QA、验证、提案、
决定及相关状态；这些运行内容不进入 Git。报告的精确引用核验不等于总结语义正确，
仍需阅读原始证据。相同任务再次导出会更新同名报告。

## 3. 人工审批

```powershell
.\.venv\Scripts\python.exe -m porga approve PROPOSAL_ID --actor owner --note "已复核证据，同意下一轮评估" --confirm
# 或拒绝：
.\.venv\Scripts\python.exe -m porga reject PROPOSAL_ID --actor owner --note "证据不足" --confirm
```

每个提案只能决定一次。批准前重新检查项目和所有成果的内容哈希与任务关联；内容被
改动或验证失败时禁止批准。批准不会修改代码、权限或部署。actor 是本地审计标记，
不是密码认证；同一个操作系统账户仍然有权编辑文件。

## 4. 中断、取消和恢复

正常错误会记录 `failed`。断电或强制退出可能留下 `running`。先确保旧进程已退出：

```powershell
.\.venv\Scripts\python.exe -m porga status
.\.venv\Scripts\python.exe -m porga recover RUN_ID
.\.venv\Scripts\python.exe -m porga resume RUN_ID
```

`recover` 只整理中断状态，不调用模型；系统锁阻止它干扰正在工作的进程。`resume`
校验并复用已经完成的 Chief/Research/QA 成果，仅重跑未完成步骤。预算和已使用调用
次数不会清零。v0.1 历史任务缺少原始预算/模型配置，保留查看与审批，不支持恢复运行。

在线未完成步骤的调用结果可能不明确，必须由人显式同意额外费用才重跑：

```powershell
.\.venv\Scripts\python.exe -m porga resume RUN_ID --allow-replay
```

未知请求的完整预留不会退回。若剩余预算不够，恢复仍会停止；应人工检查后用新 key
启动新任务，不能靠重启绕过原预算。程序没有自动对账或申请增加预算的能力。

运行时可在另一个窗口请求取消：

```powershell
.\.venv\Scripts\python.exe -m porga cancel RUN_ID
```

取消在下一次模型调用或持久化边界生效；已经发出的请求仍可能收费。进程已经崩溃
而状态为 `cancel_requested` 时，再执行 recover 完成取消。已取消任务不能 resume。

## 5. 预算与在线模式

本地 `.env` 需要明确填写可用模型、API Key、当前输入/输出价格。不要把密钥发进聊天。
先使用非常小的公开样例，并自行决定是否执行真实收费请求：

```powershell
.\.venv\Scripts\python.exe -m porga run --mode openai --project examples/project.json --request-key live-001
```

默认每次任务上限 USD 0.50，同一数据目录的每日预估上限 USD 2.00；可由所有者在
`.env` 的 `PORGA_MAX_USD`、`PORGA_DAILY_MAX_USD` 调整。每日按北京时间
UTC+08:00 的预留日期计算。费用依赖你提供的价格，不是服务商账单保证；应同时设置
API 项目费用限制。新建数据目录会建立独立预算账本，所以它不是全账户费用控制。

任务启动时保存原预算配置，恢复不会采用后来提高的限制。每次请求先事务预留，成功
后按报告用量结算；失败/未知请求保留预留。意外超量会记录实际报告用量并终止后续工作。

## 6. 备份、还原和日常检查

```powershell
.\.venv\Scripts\python.exe -m porga health
.\.venv\Scripts\python.exe -m porga evaluate
.\.venv\Scripts\python.exe -m porga backup
```

`health` 检查 SQLite、外键、项目/成果内容哈希、检查点关联，并列出未结算预留。
它的 ok 表示数据完整性，不代表真实模型质量或生产验收通过。`evaluate` 是固定的
六种来源/引用/QA 门禁回归案例，也不代表模型业务能力。

backup 使用 SQLite 快照接口生成可校验备份，包含完整本地内容。请将需要保留的
备份另行复制到你控制的位置，并按自己的数据策略定期清理；本程序不会自动删除数据。
在新空目录中演练还原：

```powershell
.\.venv\Scripts\python.exe -m porga --data-dir .porga-restored restore BACKUP_FILE_PATH
.\.venv\Scripts\python.exe -m porga --data-dir .porga-restored health
```

还原会检查备份版本、内容、引用，并拒绝覆盖已有任务或项目草案。
升级 v0.1 数据时自动保留 `pre-v0.2.sqlite3`，升级 v0.2 时保留 `pre-v0.3.sqlite3`，
原任务和成果不删除。升级前先退出旧版运行进程。旧版备份须在新目录中由新代码
先完成升级；`restore` 接受当前数据库版本。详见 [升级与回退](m1-projects.zh-CN.md)。

## 7. 进入真实使用前的人工验收

用至少五个有代表性的公开任务检查：问题是否被正确理解、每个结论是否有证据、QA
能否拒绝不充分材料、中断恢复是否符合预期、费用是否可接受。预先写下质量/成本
通过标准，再逐个记录人工判断。当前交付没有 API Key，没有替你进行这些付费验收。
只有这部分通过后，才考虑把在线模式用于你的日常公开资料研究。

## 8. 1.0 安装、升级与发布验收草案

本节是发布候选的检查规程。1.0 的支持范围应写进每次发行的兼容性记录。逐项标记
`通过`、`失败` 或 `未运行`，附候选版本、证据和限制；标为支持的组合须有实际结果。
按[1.0 版本路径](architecture/release-path.zh-CN.md)检查依赖的里程碑。

| 用例 | 操作 | 必须留存的证据 |
|---|---|---|
| R10-01 干净安装 | 在每个拟支持的 OS/Python 组合新建隔离环境，从指定发行包安装，随后从独立项目目录执行 SDK/CLI mock 闭环 | OS、Python、包及依赖版本、包 SHA-256、实际导入路径、安装/运行退出码和成果位置 |
| R10-02 外部兼容 | 校验清单、公开 SDK 返回值、CLI 退出码及导出格式；测试错误版本、越界路径、旧授权与源文件变更 | 声明支持的清单/协议版本、兼容边界、明确拒绝结果和审批要求 |
| R10-03 升级迁移 | 在隔离测试数据上用每个声明支持的来源版本启动并生成任务、结果和预留，再按升级说明迁移 | 数据库版本、备份校验、迁移前后健康状态、历史记录和权限/预算一致性 |
| R10-04 故障与恢复 | 注入迁移失败和运行中断，按恢复说明复查状态；在独立测试数据上试回兼容版本 | 恢复命令及结果、版本绑定、未知动作/预留对账，以及新旧成果如何保全 |
| R10-05 代表任务 | 用 Owner 审阅过的任务集，预先固定验收标准、费用和停止条件 | 逐任务结果、人工接受或拒绝、质量/成本对照和未覆盖场景；记录实际运行模式 |
| R10-06 发布审查 | 核查拟发布源码、可访问的历史、发行包、许可证、日志和仓库权限 | 经审阅的文件范围、发行说明、已知限制、包摘要和 Owner 发布决定 |

兼容记录要分别列出软件版本、外部清单协议、数据库版本、SDK/CLI 契约和已测试的升级
来源。现有 0.4 清单要求软件版本精确匹配。迁移时先停止旧进程、备份并核对旧状态，
再更新包及适用清单并审阅新章程。旧授权、任务和费用预留按各自规则保留或重新核对；
历史能读不等于任务能恢复。外部状态与项目根目录绑定，演练使用在测试根目录创建的
样本，不能拿已绑定的真实库换个目录当作可用副本。规则见[外部接入契约](external-project-contract.zh-CN.md)。

回退前先区分组织/Skill 活动版本回滚和软件/数据格式回滚。前者通过兼容的活动版本切换，
后者在有兼容代码和可验证的升级前备份时演练。先冻结写入并保留升级后的数据，
再恢复至演练专用状态；后续产生的成果、费用和外部动作另行对账。

发行说明至少写明下载来源、SHA-256、支持组合、安装与升级步骤、破坏性变更、
回滚入口、已知限制和反馈方式。Owner 审阅后决定是否发布。发布执行、维护权限和
公开材料边界按[发布治理](governance.md#publication)处理。
