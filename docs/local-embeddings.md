# 本地 Embedding 方案

## 1. 当前选择

- 模型：`BAAI/bge-m3`
- 规模：约 568M 参数
- 向量维度：1024
- 最大上下文：8192 tokens
- 许可证：MIT
- 权重位置：`.local/models/bge-m3/`
- 原始权重不进入 Git

### 模型指纹（2026-11-23 下载）

- Hugging Face 仓库：`BAAI/bge-m3`
- Revision：`5617a9f61b028005a4858fdac845db406aefb181`
- 权重文件：`pytorch_model.bin`
- 文件大小：2,271,145,830 bytes
- SHA256：`B5E0CE3470ABF5EF3831AA1BD5553B486803E83251590AB7FF35A117CF6AAD38`

校验命令：

```powershell
(Get-FileHash .local/models/bge-m3/pytorch_model.bin -Algorithm SHA256).Hash
```

Revision 与哈希取自本机 Hugging Face 下载缓存。换模型或重新下载后必须同步更新。

选择原因：

- 支持中英文和多语言；
- 可本地运行，不依赖外部 Embedding API；
- 当前南京资料规模小，1024 维足够；
- 不用把公开官网资料发送给第三方；
- 面试时可讲清本地可复现和成本边界。

## 2. 本机 GPU 环境

系统 Python 3.11 已有：

```text
torch 2.6.0+cu124
CUDA 12.4
NVIDIA GeForce RTX 3060 Laptop GPU
```

项目主环境 `.venv` 不安装 torch/sentence-transformers，保持测试轻量。

重型模型依赖放在隔离环境：

```text
.venv-gpu/
```

该目录已被 `.gitignore` 忽略。

### 为什么使用独立环境

- 避免主测试环境重复下载 torch；
- 避免 torch 解压时被 Windows Defender 卡住；
- 复用本机已验证的 GPU torch；
- 不把模型依赖强加给只运行单元测试的环境。

代价：当前机器有双环境；正式部署应改为单容器或单环境，避免运维分裂。

## 3. 模型加载与评估入口

### 模型加载

```python
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name=str(model_path),
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)
```

### 南京可复现评估入口

实现位置：`src/study_abroad/nanjing_eval.py`。

输入：

- `data/city_packs/nanjing_pack_v1.json`
- `data/city_packs/nanjing_sources.json`
- `evals/nanjing_cases.json`
- `.local/models/bge-m3/`

输出：

- Chroma 索引
- 检索评估 JSON 报告

当前真实结果（18 条查询，含 6 条越南语）：

```text
Hit@4 = 1.0
Complete@4 = 17/18
平均延迟 = 57.4ms
P95 延迟 = 102.3ms
```

该入口已能重复构建南京 CityPack 检索索引，不再依赖临时脚本。

当前验证结果：

```text
torch 2.6.0+cu124
cuda_available = True
embedding_dimension = 1024
model_load_seconds ≈ 77
```

### 官网快照恢复

`data/city_packs/nanjing_sources.json` 只记录元数据与快照路径，正文保存在 `.local/sources/nanjing/`，不进入 Git。

恢复要求：

- 逐条访问清单中的 `url`，把官网正文保存为对应 `snapshot_path`。
- 不得用搜索结果页、转载页或其他招生季页面替代。
- 重新采集后必须更新 `accessed_at`，并重建索引、重跑评估。
- 恢复后校验四条快照都能加载：

```powershell
$env:PYTHONPATH = "src"
uv run python -c "from study_abroad.source_snapshots import load_catalog_sources; print(len(load_catalog_sources('data/city_packs/nanjing_sources.json', '.')))"
```

输出应为 `4`。当前未提供自动抓取脚本。

## 4. 索引配置

- 使用 cosine collection。
- 模型改变后必须重建 collection。
- 本次真实索引：14 个南京 chunks（3 个 Program chunks + 11 个官网 source chunks）。
- 18 条南京评估问题（11 中文、1 英文、6 越南语）：Hit@4 = 1.0，Complete@4 = 17/18，平均查询延迟 57.4ms，P95 102.3ms（口径来自 `src/study_abroad/nanjing_eval.py` 最终复现运行）。
- 唯一未完整案例为东南大学“缺失要求”问题，只召回了两个预期来源中的一个；这是多来源完整召回问题，不是模型不可用。
- 该结果只代表 4 个来源、3 个项目的小样本，不可外推为完整南京库或生产质量。

## 5. 已知限制

- 当前只验证 4 个来源、14 个 chunks，不是完整南京库质量。
- 评估集 18 条，跨语言覆盖仍小，需随来源扩展继续增加。
- 官网快照不进入 Git，新机器需先恢复快照才能重跑评估。
- 模型文件哈希已记录，但 transformers / sentence-transformers 版本尚未固定。
- 本地模型首次加载约 77 秒，不能把冷启动时间当成长期延迟。
- `pytorch_model.bin` 是 pickle 格式；只能加载可信来源模型。

## 6. 与 API Embedding 的比较

API 方案可减少本地运维，但会增加外部依赖、数据出境、费用和供应商锁定。当前 MVP 选本地，是为了可复现和故事完整；如果生产环境对并发、延迟或运维有更高要求，再评估托管 Embedding，不把 API 作为默认前提。
