# 外部项目接入契约 v1 · Porga 0.4

状态：已实现的单人本地 Early Alpha 接入层。独立项目作为使用方安装 Porga，
保留自己的资料、业务规则、状态与成果。接入验证使用合成资料，Owner 授权仍由使用方管理。
付费模型和 24 小时调度不属于本次验证范围。

## 1. 软件、业务、数据与运行边界

Porga 包拥有通用执行、组织、预算、验证和提案机制；业务项目拥有目标、资料、领域
验收、运行库、成果和最终决定。框架不硬编码某个项目路径或业务规则。

```text
独立业务项目/
  porga.project.json      # 项目显式选择的配置；不是可执行脚本
  principles.txt          # 获准使用的资料，可放入专门的 evidence/ 目录
  .porga/                 # 此项目自己的 SQLite、锁、备份和内部报告；禁止提交
  porga-results/          # 显式导出的成果；默认不提交
```

项目根目录固定为配置文件的父目录。路径相对于该目录，和启动命令的工作目录无关。
项目可以不含 Python 源码，通过已安装包的 CLI 使用；Python 应用通过公开 SDK 调用。
安装、接入、授权、执行和接受成果是不同动作，安装不会启动后台进程。

## 2. 配置与权限

真实格式见 `examples/external-project/porga.project.json`，源模型为
`ExternalProjectSpec`，生成 Schema 为 `protocols/ExternalProjectSpec.schema.json`。
拒绝未知字段和未知协议版本；不从配置加载 Python 模块、Shell 或任意解析器。

| 字段 | 规则 |
|---|---|
| schema_version | 字符串 "1" |
| project_key | 项目内稳定标识，和规范化根目录共同确定状态所有者 |
| porga_version | 精确的软件版本；当前为 0.4.0，安装版本不匹配则拒绝 |
| state_dir / output_dir | 相对路径，默认 .porga / porga-results；互不包含 |
| sources | 1–8 个显式文件，包含 id、title、path、原始字节 SHA-256；不递归扫描 |
| goal / deliverable | 目标，以及 research_report 或 evidence_audit |
| success_criteria / non_goals | Owner 需要审阅的验收标准和排除事项 |
| classification | 默认 private；public_synthetic 必须由使用方如实声明 |
| egress | 默认 deny；只有明确声明 openai 才允许配置在线模式 |
| mode | 默认 mock；openai 必须同时声明外发并给出正数预算 |
| max_usd / max_calls | 每次运行上限；与宿主设置取较小值，不是项目生命周期总预算 |
| require_all_sources | 默认 true；确定性检查全部来源覆盖 |

文件适配器 v1 只接受 UTF-8 文本、Markdown、JSON 的完整小文件：每项不超过 16000
字节，解码后的证据文本长度为 8–4000 字符。大文档、HTML、DOCX 和整库需要先由
使用方准备经过审阅的证据摘录，不能截断后假称全文覆盖。JSON 作为证据文本处理。
文件摘要可用 PowerShell `Get-FileHash -Algorithm SHA256` 取得，再转为小写填入。

拒绝绝对路径、..、驱动器、UNC、设备名、备用数据流、符号链接、Windows 目录联接、
硬链接，以及 .env、.git、.venv 等内部路径。禁止将运行库或输出目录作为来源。
不自动修改项目 .gitignore；示例已提供默认忽略规则，使用方需覆盖自定义目录。

## 3. 外发与持久化

私有分类本身不允许外发。在线运行要求同时满足：

1. 配置明确 egress=openai、mode=openai、正数预算。
2. Owner 审阅完整预览；授权绑定目标、资料快照、分类、路径、版本、费用及外发设置。
3. 授权时显式传入 allow_openai=True，或 CLI 的 --allow-openai --confirm。
4. 本机提供 API Key、模型和价格。框架不会创建或购买额度。

实际模型输入包含目标、证据、验收条件、排除事项和各阶段结果；在线模式使用既有官方
OpenAI 接口。禁止外发只约束本框架的模型路径，不是整台电脑的网络隔离或操作系统权限。
所有模型 Agent 仍只有原有受限工具；公开 SDK 中的审批方法只能由可信宿主/Owner 调用，
不能注册成模型工具。任意运行 Python 的本机操作者仍是可信主体。

来源原文保留在业务项目。运行库还会保存获准证据副本、章程、来源摘要、成果和决定，
导出的 snapshot.json 也含证据与本地路径，均属于业务项目数据。没有默认加密、共享、
平台记忆晋升或上传 GitHub。包隔离不等于数据不会复制，也不等于密码学防篡改。

## 4. CLI 接入与授权

以下是在 0.4.0 中可运行的离线示例。先在仓库根目录打开 PowerShell，使用已安装
Porga 0.4.0 的 Python。示例清单固定为 `mock`、禁止外发、模型费用上限为 0。
逐段执行，命令返回非零退出码时先处理错误。

```powershell
$porgaExample = (Resolve-Path 'examples/external-project').Path
$porgaTrial = Join-Path ([IO.Path]::GetTempPath()) ("porga-trial-" + [guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath $porgaExample -Destination $porgaTrial -Recurse
$porgaManifest = Join-Path $porgaTrial 'porga.project.json'
python -m porga external preview --manifest $porgaManifest
$porgaDraft = python -m porga external attach --manifest $porgaManifest | ConvertFrom-Json
python -m porga external inspect --manifest $porgaManifest
```

preview 返回完整待审快照，不创建状态，也不查询既有授权；使用 inspect 查看实际状态。
attach 幂等保存草案，不授予执行权；同身份的配置/证据变更会追加未授权版本。
核对目标、来源、预算、外发设置和草案摘要后，由 Owner 确认本次合成试用。

```powershell
python -m porga external authorize --manifest $porgaManifest --digest $porgaDraft.digest --actor owner --note "Reviewed the synthetic trial scope" --confirm
$porgaRun = python -m porga external run --manifest $porgaManifest --request-key first-task | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $porgaRun.validation_passed) { throw 'Trial did not pass verification.' }
$porgaReport = python -m porga external report $porgaRun.run_id --manifest $porgaManifest | ConvertFrom-Json
Get-Content -LiteralPath $porgaReport.report
```

预期每个来源都有可定位的引文，状态保存在试用目录的 `.porga`，报告和快照位于
`porga-results` 的独立子目录。核对实际报告和章程中的条件，再接受成果。

```powershell
python -m porga external accept $porgaRun.run_id --manifest $porgaManifest --actor owner --note "Reviewed the report against the charter" --confirm
```

预期结果为 `owner_accepted`。再次运行同一请求键可核对返回的运行 ID；
每次导出有独立目录。成果接受与进化提案的决定分别记录。

external 命令不隐式加载当前目录 .env，不接受全局 --data-dir，也不采用 PORGA_DATA_DIR
或 PORGA_MODE 覆盖项目边界。只有 run 读取模型、价格和资源限制环境变量；API Key
由既有运行时读取进程环境。查看和取消不依赖模型配置。

## 5. 公开 Python API

```python
from porga.api import ProjectClient, RunOptions

client = ProjectClient("/absolute/path/to/project/porga.project.json")
preview = client.preview()
draft = client.attach()
# Owner 审阅后由宿主显式调用，禁止接到 Agent 工具列表：
client.authorize(draft["digest"], actor="owner", note="已审阅")
result = await client.run(options=RunOptions(), request_key="first-task")
snapshot = client.inspect_run(result["run_id"])
files = client.export(result["run_id"])
```

另有 inspect、accept、decide、cancel、recover、resume、health、backup 方法。
decide 始终不部署。RunOptions 只提供模型、价格和宿主资源上限，不允许覆写路径或模式。
SDK 不要求使用方导入内部 Store/SQLite。API v1 仍为实验版，消费项目必须精确锁版本。
领域解析与规则留在使用方；本版不提供动态插件加载或任意项目代码执行。

## 6. 版本、恢复与兼容

语义配置和完整证据快照进入摘要；仅改变 JSON 排版不会改变语义摘要。源文件摘要按
原始字节计算。文件、配置或授权范围变化后，旧授权不能启动新工作。授权、开始执行
及恢复时重新核对真实文件和边界；运行中使用已批准快照，不实时跟随文件编辑。
运行中撤销请使用 cancel；已经发出的模型请求可能继续计费。

每个状态库只绑定一个根目录和 project_key，拒绝借用另一项目的运行 ID 或克隆数据库。
移动项目根目录、跨机器迁移或更改状态目录不自动继承授权；v1 暂不提供迁移向导。
旧任务历史检查只依据持久快照，不因源文件后来变化而判为历史损坏。
如果旧任务所需配置已改变，恢复会停止，需要恢复原批准快照或另建经授权的新任务。
不重置旧预算，未知在线请求恢复仍需 allow_replay。

数据库 user_version=3 为兼容屏障，防止旧代码误操作含外部/私有章程的数据。
v0.3 升级前生成 pre-v0.4.sqlite3；不删除原记录。回退使用旧代码和升级前快照的
独立副本。旧 0.3 章程继续可读；外部绑定章程使用 0.4，组织角色协议未扩大。
损坏配置时可通过旧的显式 --data-dir cancel/recover/health 入口执行应急操作。

日预算目前按同一数据目录累计，各外部项目分库后没有跨项目总额协调；需要账户侧
用量管理。24 小时 Worker、持久队列、共享服务、知识/Skill 晋升和可回滚采用仍属后续阶段。

## 7. 安装包验收

Community 发行包通过 [GitHub Releases](https://github.com/Petron1987/Porga-public/releases)
分发。使用已核对的 wheel 和锁定依赖安装，并在项目清单中固定版本。
构建命令为 `python -m pip wheel --no-deps --wheel-dir dist .`。
`python scripts/check_external_consumer.py dist` 会将本地 wheel 安装到临时独立目录，
通过 SDK 和 CLI 完成合成资料闭环，验证运行库、成果与源码目录分离。它只为临时
合成测试数据生成授权记录，不授权真实项目。测试复用当前环境的依赖，不代表已在
全新机器或真实在线模型上完成验收。

## 8. 0.5 轻量启用的验收草案

0.5 从使用方选定目录、明确启用开始，目标是产出候选清单和章程草案。上述 0.4 流程
提供对照。未来命令、文件字段与兼容政策在实现时确认，本节仅列验收用例。

| 用例 | 输入与动作 | 通过条件 |
|---|---|---|
| A05-01 首次启用 | 在无 Git、无完整项目说明的独立目录中放入少量合成材料 | 只有明确启用后才读取批准范围，展示候选来源、拟写路径、证据缺口和少量关键问题 |
| A05-02 文件边界 | 混入未授权子目录、忽略文件、链接、未知格式和超限文本 | 拒绝越界读取，分别报告未处理和部分覆盖，源文件保持不变 |
| A05-03 重复与修订 | 对同一输入重复启用，再改变一项证据或预算 | 相同输入复用草案，变更生成待审版本；旧授权无法启动新修订 |
| A05-04 启用到导出 | 在 Owner 核对具体草案后，完成一次 mock 任务和成果核对 | 有章程摘要、运行 ID、来源覆盖结果、导出位置和单独的人工接受记录 |
| A05-05 接入 Skill | 用支持该格式的宿主调用已验证的 SDK/CLI 路径 | 结果和直接调用一致；待授权、校验失败和不支持的宿主有明确提示 |

保存测试输入摘要、前后文件清单、状态转换和调用计数。无有效授权或外发同意时，
在发起模型调用前停止。接入 Skill 可以解释流程和提交已授权任务，授权和接受由可信
Owner 路径办理。团队选择的验收见[项目启动设计](architecture/project-genesis.zh-CN.md)。
