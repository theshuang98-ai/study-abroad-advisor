# study-abroad-advisor

南京高校一年制汉语项目售前推荐工作台。

面向越南学生的售前咨询场景：结构化收集学生背景，基于城市高校官网项目库，输出按学校档次组织的推荐表；每条关键事实保留官网证据、招生季和采集日期。

本工具不是全国自动择校器，不是自由问答机器人，也不做录取概率判断。当前 Demo 城市只有南京。

## 当前能力

- 官网 HTML/PDF 解析，保留标题与来源快照。
- LangChain Structured Output 抽取 Program/Evidence，配合确定性校验。
- 南京 CityPack：5 所 active；河海大学项目数据标记为 stale。
- 本地 BGE-M3 + Chroma cosine 检索，支持大学 Metadata 过滤。
- 20 条南京检索评估（含 6 条越南语），可复现入口 `src/study_abroad/nanjing_eval.py`。
- 确定性推荐表生成：按学校档次分组，预算超限、语言成绩不足、招生季不符等确定性标记。
- LangGraph 最小工作流：缺字段澄清、检索节点（可注入真实 Chroma）、证据检查、人工确认、SQLite Checkpoint 恢复。
- DeepSeek 引用回答：只用检索证据作答，引用必须命中 chunk 原文；无证据时明确拒答；20 条回答评估见下。
- Streamlit 工作台：学生表单 → 推荐表 → 人工确认 → 带引用问答。
- 116 项自动化测试，Ruff 通过。

## 检索实测

```text
样本：7 个官网来源，27 个 chunks（5 Program + 22 Source）
查询：20 条（中文 13、英文 1、越南语 6）
Hit@4        = 1.0
Complete@4   = 19/20
平均延迟     = 63.8ms
P95 延迟     = 67.9ms
```

6 条越南语查询全部 Hit@4 且 Complete@4。唯一未完整案例仍是东南大学“学历要求与学制”问题：需要两个来源，Top-4 只召回一个。

延迟是单机单次运行结果，受 GPU 状态影响；20 条混合语言查询与早期 12 条中文基线不可直接比较。

该结果只代表当前小样本，不能外推为完整南京库或生产质量。

## 回答实测

使用 DeepSeek 对同一批 20 条问题生成带引用回答，结构或引用无效时最多重试一次：

```text
Citation Hit        = 20/20
Citation Complete   = 19/20
Refusal Correct     = 19/20
Errors              = 0
平均生成延迟        = 2.49s
P95 生成延迟        = 4.06s
```

未完整案例：东南大学“学历要求与学制”正确拒答，但只引用收费页。另有 1 条越南语秋季申请题被误判证据不足。拒答样本只有 2 条，不能代表完整可靠性。

## 架构

```text
官网 HTML / PDF
  -> 解析与来源快照
  -> Program / Evidence 抽取（LangChain Structured Output）
  -> 确定性校验
  -> 南京 CityPack + 来源清单
  -> Program chunks + 官网正文 chunks
  -> 本地 BGE-M3 Embedding
  -> Chroma（cosine + Metadata 过滤）
  -> 检索评估
  -> LangGraph 工作流（澄清 / 证据检查 / 人工确认 / SQLite）
  -> 确定性推荐表
  -> 引用回答（DeepSeek，证据不足时拒答）
  -> Streamlit 演示
```

## 目录

```text
src/study_abroad/     应用代码
tests/                自动化测试
data/                 可上传的结构化数据与来源清单
evals/                检索评估样本
docs/                 产品、数据契约与运行说明
.local/               模型、原始网页、向量库、临时产物（不上传）
```

## 快速开始

要求：Python 3.11、uv。

```powershell
uv sync --group dev
uv run pytest
uv run ruff check .
```

主环境不安装 torch，保持测试轻量。本地 Embedding 的隔离环境与模型加载方式见 `docs/local-embeddings.md`。

### DeepSeek 配置

`.env` 已被 Git 忽略，`.env.example` 提供字段模板。未引入 python-dotenv，运行前需自行注入环境变量：

```powershell
$env:DEEPSEEK_API_KEY = "<your-key>"
```

可选变量：`DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`）、`DEEPSEEK_MODEL`（默认 `deepseek-chat`）。

## Streamlit 演示

页面依赖本地 BGE-M3 与 Chroma 索引，使用 `.venv-gpu` 启动：

```powershell
$env:PYTHONPATH = "src"
.\.venv-gpu\Scripts\python.exe -m streamlit run src/study_abroad/app.py
```

页面会自动读取项目根目录 `.env`，不覆盖已有环境变量。首次检索会加载 BGE-M3，约 77 秒。

流程：填写学生背景 → 生成推荐表 → 审核或退回 → 基于官网证据提问。

## Docker

```powershell
docker build -t study-abroad-advisor .
docker run --rm -p 8501:8501 `
  -e DEEPSEEK_API_KEY="<key>" `
  -e EMBEDDING_DEVICE=cpu `
  -v "${PWD}/.local:/app/.local" `
  study-abroad-advisor
```

容器不包含模型和 Chroma 索引，需要挂载 `.local/`。容器默认使用 CPU Embedding，首次加载明显慢于本机 GPU。

## CI

`.github/workflows/ci.yml` 在 push 和 pull request 时运行：

- `uv sync --frozen --group dev`
- `uv run pytest`
- `uv run ruff check .`

CI 不调用真实模型。需要本地官网快照的索引集成测试在干净 checkout 会自动跳过；其余测试使用 fake embeddings 和临时目录。

## 复现南京检索评估

前置条件：

- 本地模型目录 `.local/models/bge-m3/`。
- 官网快照，路径由 `data/city_packs/nanjing_sources.json` 指定。
- 已配置 CUDA 的 `.venv-gpu` 环境。

入口：

```powershell
$env:PYTHONPATH = "src"
.\.venv-gpu\Scripts\python.exe -c "from study_abroad.nanjing_eval import build_nanjing_eval_index as b; b(pack_path='data/city_packs/nanjing_pack_v1.json', sources_path='data/city_packs/nanjing_sources.json', cases_path='evals/nanjing_cases.json', model_path='.local/models/bge-m3', persist_directory='.local/runtime/chroma_nanjing_bge_final', report_path='.local/runtime/eval/nanjing_retrieval_baseline.json', project_root='.', device='cuda')"
```

模型与原始网页不进入 Git。新机器需要先恢复这两类本地资产，步骤见 `docs/local-embeddings.md`。

## 数据与证据规则

- 事实只来自高校官网；社群内容不进入官方招生事实。
- 官网未说明的字段保持 `null`，不用猜测补全。
- 一个招生季对应一套事实，不跨季拼接。
- 原始网页和模型权重只保存在 `.local/`。
- 不含真实学生个人资料。
- 所有指标来自实测，不伪造准确率、延迟或成本。

## 文档

- `docs/product-brief.md`：产品定位与 MVP 边界。
- `docs/schemas.md`：学生输入与推荐表输出契约。
- `docs/city-program-catalog.md`：城市项目库契约。
- `docs/data-contract.md`：官网数据契约。
- `docs/local-embeddings.md`：本地 Embedding 与评估运行说明。
- `docs/nanjing-university-pool.md`：南京候选学校池工作稿。

## 当前边界

- LangGraph 检索节点已支持注入真实 Chroma（本地 BGE-M3 已验证）；报告文案仍是确定性模板。
- DeepSeek 已接入结构化抽取与引用回答，但尚未驱动报告文案。
- 推荐表已做预算与 HSK/雅思/托福的确定性匹配；学历要求仍是自由文本，需人工复核。
- 7 个南京来源、5 个 active 项目；河海为 2022 stale 数据，南京工业大学招生季未标注。
- Docker 与 CI 配置已加入；容器使用 CPU Embedding，未做登录与并发。
