# Porga 本地运行与人工审批

Porga（Self-Evolving Agent Organization System）的 v0.4 是单人本地试运行版 / Early Alpha。
当前交付使用 Python 3.11 和 OpenAI Agents SDK；默认 mock 模式不需要 API Key。
已有中断恢复、重复提交防重、持久化预算、备份还原和报告导出，详见
[本地试运行手册](operations.zh-CN.md)。真实在线任务质量尚未完成生产验收。

新项目请先走 [项目接管与验收流程](m1-projects.zh-CN.md)：保存目标/验收/边界/资料/预算，
回答缺失项，明确授权后运行。研究报告与证据审计使用不同受限角色。
原来的 demo/run 保留为内核演练入口，不代表已经完成项目章程授权。

外部业务项目推荐使用 [外部项目接入契约](external-project-contract.zh-CN.md)：安装独立包，
保留项目原位置，使用自己的配置、运行库与成果目录。默认私有分类、禁止外发；
声明私有资料不等于同意发送给模型服务。当前仅用合成外部项目完成验收。

## 运行

在 Porga 项目目录打开 PowerShell，执行：

```powershell
.\.venv\Scripts\python.exe -m porga doctor
.\.venv\Scripts\python.exe -m porga demo --mode mock
.\.venv\Scripts\python.exe -m porga status
```

首次交付已经安装 `.venv`。将来在另一台电脑拉取代码后，需要先安装依赖：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c requirements.lock.txt -e ".[dev]"
```

安装依赖需要联网，安装后 mock 演示与测试可以断网运行。GitHub 只同步代码，
不自动同步两台电脑的任务数据库、密钥和聊天记录。

## 查看成果并决定

演示会返回 `run_id`、`proposal_id`、验证结果和调用计量。将下面的占位内容替换
为实际返回值，即可查看完整证据、研究报告、QA、验证项、提案和审计事件：

```powershell
.\.venv\Scripts\python.exe -m porga inspect RUN_ID
```

人工检查后，可以批准或拒绝：

```powershell
.\.venv\Scripts\python.exe -m porga approve PROPOSAL_ID --actor owner --note "已核对证据，同意开展后续评估" --confirm
.\.venv\Scripts\python.exe -m porga reject PROPOSAL_ID --actor owner --note "需要补充证据" --confirm
```

每个提案只能决定一次。验证失败的提案不能批准。v0.1 的批准只是持久化人工决定，
不会自动修改代码、权限、组织模板或部署。真正的自进化还需要后续的独立对照评估
与可回滚发布机制；演示成功不代表已经证明某次改进有效。

## 自定义任务与测试

复制并编辑 `examples/project.json`，只放你有权使用的公开或合成材料：

```powershell
.\.venv\Scripts\python.exe -m porga run --mode mock --project examples/project.json
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
```

mock 模型返回固定、可重复的演示结果，但 Chief、Research、QA 及工具调用确实经过
Agents SDK 的 Agent/Runner。Research 只能读取任务证据，QA 无工具权限，内核检查
引用来源与原文一致性，并执行预算限制。它不会联网搜索或自动形成真实市场结论。

## 在线模式

将 `.env.example` 复制为 `.env`，在本地填写 API Key、可用模型，以及该模型当前
每百万输入/输出 Token 的美元价格。价格由你维护，程序不猜测。然后显式运行：

```powershell
.\.venv\Scripts\python.exe -m porga run --mode openai --project examples/project.json
```

在线模式会向 OpenAI API 发送目标、证据和生成的内容，可能产生费用。当前未配置
API Key，因此交付验证只使用离线模型和内存 HTTP 模拟，未进行真实付费调用。

`.env`、`.venv` 和 `.porga` 数据库均不进入 Git。SDK 远端追踪关闭，审计只记录
必要元数据；本地数据库仍保存完整任务与成果，应按自己的数据策略保护。

## 源码与项目数据

源码同步需获得所有者授权。公开范围与许可证需另行决定。本地数据库、私有资料、
密钥和虚拟环境不随代码同步。
