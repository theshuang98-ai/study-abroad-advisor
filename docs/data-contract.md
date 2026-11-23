# 官网数据契约

## 1. 通用规则

- 时间使用 ISO 8601；采集时间使用 UTC，日期格式为 `YYYY-MM-DD`。
- `null` 表示官网未说明、尚未抽取或无法确认。不得使用空字符串、`0` 或“无”代替未知。
- 空数组只表示已确认没有项目，不表示未知。
- 原始文本与规范化字段分开保存。翻译和摘要不得覆盖原始证据。
- 一个招生季对应一套事实；不得将不同招生季的学费、截止日期和要求拼成同一项目结论。
- `data/` 只保存可上传的结构化数据、短证据和来源元数据。原始文档保存在 `.local/sources/`。

## 2. Source：官方来源清单

`data/source_manifest.json` 中每条来源包含：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_id` | string | 是 | 稳定且唯一的来源标识 |
| `university` | string | 是 | 大学名称 |
| `title` | string | 是 | 官方页面或 PDF 标题 |
| `url` | string | 是 | 官方 URL，不使用搜索聚合页代替 |
| `source_type` | string | 是 | `official_webpage` 或 `official_pdf` |
| `language` | string | 是 | `zh`、`en` 或 `vi` |
| `admission_cycle` | string | 是 | 例如 `2027_entry`；官网未明确时标记 `unspecified` |
| `accessed_at` | date | 是 | 实际访问日期 |
| `published_at` | date/null | 是 | 官网明确发布日期；未知为 `null` |
| `access_status` | string | 是 | `accessible`、`inaccessible` 或 `unverified` |
| `notes` | string/null | 是 | 访问限制、时效风险或其他说明 |

来源清单不保存正文。正文、HTML 和 PDF 只进入 `.local/sources/`。

## 3. Program：学历项目记录

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `program_id` | string | 是 | 稳定且唯一的项目标识 |
| `university` | string | 是 | 大学名称 |
| `program_name_original` | string | 是 | 官网原始项目名称 |
| `degree_level` | string/null | 是 | `bachelor`、`master`、`doctor`、`non_degree`、`unknown` |
| `is_degree_program` | boolean/null | 是 | 学历项目为 `true`；未知为 `null`，不能猜测 |
| `academic_field` | string/null | 是 | 专业或学科方向 |
| `instruction_languages` | array/null | 是 | 授课语言代码数组；未知为 `null` |
| `duration_text` | string/null | 是 | 官网原始学制表述 |
| `tuition_amount` | number/null | 是 | 学费数字，不包含货币和周期 |
| `tuition_currency` | string/null | 是 | 例如 `CNY` |
| `tuition_period` | string/null | 是 | `year`、`semester`、`program` 或 `unknown` |
| `tuition_text` | string/null | 是 | 学费原始表述，便于复核数字 |
| `application_deadline` | date/null | 是 | 能明确规范化时填写 ISO 日期 |
| `deadline_text` | string/null | 是 | 截止日期原始表述或时间段 |
| `language_requirements` | array/null | 是 | 语言要求原文要点，不自行推断 |
| `academic_requirements` | array/null | 是 | 学历、成绩等要求原文要点 |
| `admission_cycle` | string | 是 | 与来源招生季一致 |
| `verification_status` | string | 是 | `verified`、`partial`、`conflicting`、`stale`、`unverified` |
| `evidence` | array | 是 | Evidence 对象数组；`verified` 项目不得为空 |
| `collected_at` | datetime | 是 | 本条记录的采集时间 |

## 4. Evidence：证据对象

每个需要证据的字段对应一条证据：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_id` | string | 必须存在于 Source 清单 |
| `field_name` | string | 该证据支持的 Program 字段 |
| `source_url` | string | 与 Source 清单一致 |
| `source_quote` | string | 支持该字段的简短原文，不使用模型改写 |
| `admission_cycle` | string | 证据所属招生季 |
| `collected_at` | datetime | 证据采集时间 |

确定性校验规则：

- `is_degree_program=true` 时，`degree_level` 必须是 `bachelor`、`master` 或 `doctor`，并存在对应证据。
- 学费数字存在时，必须同时存在货币、周期和学费证据；否则标记 `partial`。JSON 中 `tuition_amount` 必须是数字，不能序列化为字符串。
- 截止日期或原始截止日期文本存在时，必须存在对应证据。
- `language_requirements` 未知或缺少证据时不得标记 `verified`；语言要求指向其他页面或学院确认时，当前记录标记 `partial`。
- 每条 Evidence 的 `source_quote` 必须在对应来源正文中存在。一个 Program 可以引用多个官方来源，但不得把 A 来源的原文标记为 B 来源。
- 关键字段缺少证据时不得标记 `verified`。
- 证据冲突时保留冲突记录并标记 `conflicting`，不自动选择模型认为合理的值。

## 5. RAG Document 与 Chunk 元数据

向量索引属于 `.local/runtime/` 的可重建产物。每个 chunk 至少包含：

| 字段 | 说明 |
|---|---|
| `document_id` | 来源文档的稳定标识，可与 `source_id` 关联 |
| `chunk_id` | 文档内稳定且唯一的 chunk 标识 |
| `program_id` | 能明确归属时填写；通用招生资料为 `null` |
| `university` | 用于大学过滤 |
| `admission_cycle` | 用于招生季过滤 |
| `source_url` | 原始官方 URL |
| `source_quote` | 支持具体事实的原文片段 |
| `collected_at` | 原文采集时间 |
| `text` | 当前 chunk 的检索文本 |

查询可以按大学和招生季过滤。共享项目语料不按学生 `user_id` 隔离；学生个人资料不得进入公共向量索引。

## 6. 评估样本格式

`evals/cases.json` 每条样本包含：

| 字段 | 说明 |
|---|---|
| `case_id` | 唯一案例标识 |
| `category` | `hard_filter`、`retrieval`、`comparison`、`missing`、`conflict` |
| `question` | 学生问题 |
| `student_profile` | 硬条件案例所需的去标识化条件；其他案例可为 `null` |
| `expected_answer` | 人工编写的事实答案或“资料不足”结论 |
| `expected_program_ids` | 相关项目；尚无项目记录时使用预期项目键 |
| `expected_source_ids` | 答案必须使用的来源 |
| `must_not_claim` | 明确禁止出现的错误或无依据结论 |
| `notes` | 评估意图和边界说明 |

标准答案和证据由人工核对官网后填写，不让模型生成自己的标准答案。
