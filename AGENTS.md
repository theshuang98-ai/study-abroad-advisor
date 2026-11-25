# AGENTS.md

## 项目使命

主作品是一个**面向越南学生售前咨询场景的 AI 辅助工作台**。当前 MVP 收敛为：

> **基于城市维度的中国高校一年制汉语学习项目推荐工具。**

它不是全国学校自动匹配器，也不是自由问答聊天机器人。第一阶段目标是：

- 结构化收集学生背景；
- 基于目标城市高校官网项目库；
- 输出按学校档次组织的推荐表；
- 供顾问或学生做第一轮售前沟通；
- 在服务过程中持续沉淀可复用数据资产。

项目以 AI 产品经理能力展示为主、工程能力为辅，通过两周实践覆盖 LangChain、LangGraph、RAG、评估和部署。每天投入 3–5 小时，不追求无实际需求的复杂架构。

### MVP 边界

- 当前 Demo 城市：**南京**。
- 当前项目类型：**一年制汉语学习项目**。
- 输入为结构化学生背景表单，不做开放式自由问答。
- 输出为按学校梯度组织的售前推荐表，不是录取判断。
- 事实依据以高校官网为主；社群内容只用于需求发现和学生经验，不作为官方招生事实。
- 不做全国学校推荐、不做录取概率预测、不做签证/文书/网申/Offer 全流程。
- 模型优先使用 OpenAI 兼容 API；服务商、聊天模型和 Embedding 方案在使用前确认，不维护无需求的备用实现。

## 不可删除的技术验收

1. **LangChain**：真实用于模型、工具、Structured Output 项目抽取、Embedding 或 Retriever，不能只安装依赖。
2. **LangGraph**：Streamlit 调用编译后的 StateGraph，包含条件澄清、检索、证据校验、人工确认和报告；SQLite Checkpoint 与 `interrupt` 恢复必须有测试。
3. **RAG**：必须完成官网资料解析、分块、向量化、Metadata 过滤、检索和引用回答。结构化条件筛选不等于 RAG。
4. 回答关键项目事实时返回原文证据、来源 URL、招生季和采集日期；无证据时明确说不知道。
5. 至少 20 条去标识化评估样本，覆盖抽取、检索、对比、缺失信息、过期或冲突信息。所有指标必须来自实测。

## 当前项目里程碑

项目已从泛留学问答收敛为“南京高校一年制汉语项目售前推荐工作台”。基础解析、结构化抽取、证据校验、RAG 离线骨架、学生输入/推荐表 Schema、城市项目库 Schema、带确定性资格标记的最小推荐工作流、带澄清与人工确认的 LangGraph 最小工作流、城市库 Evidence 预检、离线来源快照加载和可复现南京检索评估入口均已完成；当前南京 CityPack 为 3 所 active、1 所 pending。已下载并在本机 GPU 验证 BGE-M3：torch 2.6.0+cu124、1024 维、cosine 索引；14 个南京 chunks 上 18 条查询（含 6 条越南语）的 Hit@4=1.0、Complete@4=17/18、平均延迟 57.4ms、P95 102.3ms。全量 116 项测试与 Ruff 通过。DeepSeek 已接入结构化抽取和引用回答，引用必须命中 chunk 原文，无证据时拒答；18 条回答评估为引用命中 18/18、引用完整 17/18、拒答正确 2/2、0 错误，平均生成延迟 2.2s。LangGraph 检索节点已验证可注入真实 Chroma；Streamlit 本地 Demo 已完成，Docker 与 CI 尚未完成。

## 文档分层

- `docs/product-brief.md`：产品定位与 MVP 边界。
- `docs/data-contract.md`：官网数据契约。
- `docs/schemas.md`：售前工作流输入输出契约。
- `docs/city-program-catalog.md`：城市项目库契约。
- `docs/local-embeddings.md`：本地 Embedding 运行说明。
- `docs/nanjing-university-pool.md`：南京候选学校池工作稿。

- Day 2 已确定复旦大学、浙江大学、厦门大学，记录 6 个 2027 入学季官方来源，并编写 10 个带人工答案的评估案例。
- Day 3 已完成 HTML/PDF 统一解析入口、19 项解析测试和 1 项标题事实回归测试；全量 20 项测试与 Ruff 通过，6 份真实来源 JSON 已写入 `.local/runtime/ingested/`。
- 网页标题会与正文一起保留，避免编号学费等事实被误判为空标题后丢失；复旦目录表格错列和指南字符编码风险已记录，后续不得绕过人工复核。
- 产品说明位于 `docs/product-brief.md`，输入输出 Schema 位于 `docs/schemas.md`，城市项目库契约位于 `docs/city-program-catalog.md`，南京候选学校池工作稿位于 `docs/nanjing-university-pool.md`，数据契约位于 `docs/data-contract.md`，来源清单位于 `data/source_manifest.json`，评估案例位于 `evals/cases.json`。
- 原始 PDF 与学习笔记只保存在 `.local/`，不上传 GitHub。
- 已验证 Python 3.11.8、LangChain 1.5.0、LangGraph 1.2.22、LangChain-OpenAI 1.8.0、pytest 和 Ruff。
- 使用 uv 0.11.23；`python` 不在 PATH，统一使用 `uv run` 或 `py -3.11`。
- Agent Reach 已升级到 1.6.1。YouTube 和 B站上游依赖安装失败，不自动重试。
- GitHub CLI 已登录 `theshuang98-ai`。远程仓库尚未创建，名称和创建操作由主 Session 与用户另行确认。
- Day 4 已交付 Program/Evidence Schema、确定性校验、LangChain Structured Output、多来源批量集成和 `data/programs.json` 中 10 条复核记录（7 条 `verified`、3 条语言要求待确认的 `partial`）；全量 56 项测试与 Ruff 通过。相关来源正文已进入模型 Prompt，金额以 JSON 数字输出。真实模型服务商与 Embedding 方案仍未配置，下一技术里程碑是可测试的 RAG 问答。

项目级里程碑只由主 Session 在阶段变化时更新，不在这里记录各 Session 的临时进度。

## 两周交付路线

1. Day 1–2：环境、工程治理、产品定义、来源清单、数据契约和首批评估问题。
2. Day 3–4：官网解析、来源元数据、Pydantic 项目抽取和确定性校验。
3. Day 5：RAG 分块、Chroma 索引、Metadata 过滤和假 Embedding 基线。
4. Day 6：对齐新 MVP，定义南京高校一年制汉语项目库与学生输入 Schema，并形成推荐表输出契约。
5. Day 7–8：构建南京城市包数据、真实 Embedding 选型、跨语言检索评估、推荐表生成链路。
6. Day 9–11：LangGraph 售前工作流、缺失信息追问、推荐表生成、人工确认与状态恢复。
7. Day 12–14：Streamlit 演示界面、异常状态、Docker、CI、架构文档、模拟面试和项目复盘。

## 多 Session 启动与协作

每个新 Session 必须：

1. 阅读根目录 `AGENTS.md` 和相关代码，不假设自己拥有全部文件写权限。
2. 创建 `.local/sessions/<日期>-<任务>/GUIDE.md`，记录任务、允许修改、禁止修改、依赖条件、当前步骤、验收命令、临时文件和交接状态。
3. 查看其他活跃 Session 的 GUIDE，确认没有写入路径冲突。
4. 只修改自己声明的 Write Set。需要扩大范围时先更新 GUIDE，并在涉及共享文件或其他 Session 文件时请求用户确认。
5. 在阶段结束或交接时更新自己的 GUIDE，不修改其他 Session 的文档。

主 Session 负责 `AGENTS.md`、`.gitignore`、README、依赖文件和项目级里程碑。其他 Session 默认只读这些共享文件。两个 Session 不得同时拥有同一个写入路径；冲突时停止并请求协调。

## 小步修改规则

1. 每轮最多创建或修改 1–2 个受控文件，包括主文档、Session 文档、锁文件、手写数据和生成锁文件。
2. 实现与对应测试优先组成一轮；文档更新单独组成一轮。超过两个文件必须拆轮。
3. 每轮先验证再进入下一轮。代码运行对应测试，依赖验证导入，数据验证 Schema 和来源完整性。
4. 运行缓存、日志、原始下载和模型输出只能写入 `.local/`。临时文件用完即删，不能把临时文件留在根目录。
5. 不提前创建空目录、空文件、抽象层或备用实现，不顺便重构无关代码。

## 开发回合输出约定

每个开发回合按以下顺序输出：

1. 当前任务：1 行。
2. 本轮修改：最多 2 个文件。
3. 验证：命令与结果；失败时只贴最短关键错误。
4. 风险或阻塞：最多 3 条，没有则写“无”。
5. 下一步：只给 1 个具体动作。

不重复项目背景，不贴完整工具输出，不展示长代码或长文档，除非用户明确要求。安全警告、不可逆操作和步骤顺序可能混淆时，使用完整句子说明。

## GitHub 与本地文件边界

根目录只保留治理文档和工程配置。按实际需要逐步使用：

- `docs/`：可上传的产品说明、架构、数据契约、运行文档和去标识化实测报告。
- `src/study_abroad/`：可上传的应用代码。
- `tests/`：可上传的自动化测试。
- `evals/`：可上传的评估代码和去标识化工程样本。
- `data/`：可上传的来源清单、Schema 和小型工程夹具，不保存原始网页或真实个人数据。
- `.local/learning/`：仅本地的课程、八股、个人学习和简历材料。
- `.local/sessions/`：仅本地的 Session 指导文档。
- `.local/sources/`：仅本地的官网 HTML/PDF、第三方内容和调研原始资料。
- `.local/runtime/`：仅本地的向量库、Checkpoint、数据库和模型输出。
- `.local/tmp/`：仅本地的临时文件，用完即删。

`.local/` 整体忽略，不上传。不得提交 `.env`、API Key、Token、Cookie、虚拟环境、缓存、日志、真实学生资料、Facebook 原始内容或第三方仓库副本。新增文件前先判断归属；不确定时先询问用户。

## 技术与测试约定

- 使用 Python 3.11 和 uv，依赖版本写入锁文件，以当前 LangChain/LangGraph 官方文档为准。
- 默认测试使用确定性假模型和 `.local/tmp/` 或 pytest 临时目录，不访问真实模型，不消耗 API 额度。
- 真实模型 Smoke Test 必须显式运行，不进入默认 CI。
- RAG 检索与生成分别评估；Agent 同时评估结果、工具调用轨迹、成本和失败路径。
- 硬性条件用确定性代码判断，模型负责抽取、语义检索和自然语言表达。
- 不伪造准确率、延迟、成本、用户量、面试真题、项目经历或官网信息。

## Git 与 GitHub 规则

任何 Git 写操作都必须先获得用户当次明确确认，包括 `git init`、`git add`、创建仓库、commit、push、分支和标签操作。不得因为用户过去同意过而自动执行下一次写操作。

只读的 `status`、`diff`、`log` 和远程仓库查询可以直接执行。提交前必须运行检查、审阅 diff、检查密钥与个人资料，并说明拟提交内容。多 Session 环境下只显式暂存本 Session 已确认的文件，不使用 `git add .`，不提交其他 Session 的修改。

## 核心参考资料

优先级：当前官方文档与迁移说明 > 高校官方来源 > 官方源码与许可证清晰的工程项目 > 社区材料。

- LangChain：https://docs.langchain.com/oss/python/langchain/overview
- LangGraph：https://docs.langchain.com/oss/python/langgraph/overview
- 官方结构化抽取模板：https://github.com/langchain-ai/data-enrichment
- 官方 RAG 模板：https://github.com/langchain-ai/retrieval-agent-template
- 官方最小图模板：https://github.com/langchain-ai/new-langgraph-project
- Streamlit、服务与测试参考：https://github.com/JoshuaC215/agent-service-toolkit

第三方模板只裁剪需要的模式，不整仓克隆或复制。README 中的旧模型和旧链接以当前官方文档为准。社区答案必须二次核验，不把示例指标当成实测结果。
