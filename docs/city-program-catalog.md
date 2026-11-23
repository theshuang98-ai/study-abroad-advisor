# 城市项目库契约：南京一年制汉语学习项目

## 1. 目的

本文档定义当前 MVP 的核心数据资产：**城市项目库**。

当前项目库不是全国高校库，而是围绕一个城市的学校池，结构化整理该城市目标项目类型的官网数据。当前 Demo 的范围是：

- 城市：南京
- 项目类型：一年制汉语学习项目
- 使用阶段：售前咨询

该数据资产将用于：

- 生成按学校梯度组织的推荐表；
- 支撑 RAG 检索与证据引用；
- 为后续学生案例积累与匹配升级提供基础。

---

## 2. 核心概念

## 2.1 城市包（CityPack）

一个 CityPack 表示一个城市的高校项目资料包。

示例：

- 南京 CityPack
- 成都 CityPack
- 济南 CityPack

### CityPack 的作用

- 圈定该城市的目标学校池；
- 汇总这些学校的目标项目；
- 维护城市级可复用资产；
- 支持“做一个成都的”这类复制式扩展。

---

## 2.2 学校池（UniversityPool）

某个城市下，经人工筛选进入推荐范围的学校列表。

南京示例可包括：

- 南京大学
- 东南大学
- 南京师范大学
- 南京理工大学
- 南京航空航天大学
- 河海大学

> 说明：以上是结构示例，最终学校名单应以实际运营数据为准。

### 学校池字段设计原则

- 学校顺序不代表正式排名；
- `tier_hint` 用于售前梯度组织，不等于官方排名；
- 学校是否进入池子，取决于业务运营和官网项目可用性。

---

## 2.3 项目库（ProgramCatalog）

某城市学校池下，围绕目标项目类型整理出的官网项目记录集合。

当前目标项目类型固定为：

```text
one_year_chinese_program
```

---

## 3. 顶层 Schema：CityPack

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `city_pack_id` | string | 是 | 城市包唯一标识，如 `nanjing_pack_v1` |
| `city` | string | 是 | 城市名，如 `Nanjing` |
| `country` | string | 是 | 国家，如 `China` |
| `target_program_type` | string | 是 | 当前固定为 `one_year_chinese_program` |
| `admission_cycle` | string | 是 | 招生季，如 `2027_fall` |
| `version` | string | 是 | 数据包版本，如 `v1` |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 最近更新时间 |
| `universities` | array[UniversityEntry] | 是 | 城市学校池及项目记录 |

---

## 4. UniversityEntry

表示城市包中的一所学校及其目标项目列表。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `university` | string | 是 | 学校名称 |
| `city` | string | 是 | 所在城市 |
| `tier_hint` | string | 是 | 售前梯度提示，如 `reach`、`match`、`safety` |
| `pool_status` | string | 是 | `active`、`pending`、`excluded_no_official_data`、`excluded_out_of_scope` |
| `review_flags` | array[string] | 是 | 学校级待人工处理项，如当前招生季项目页缺失 |
| `official_programs` | array[ProgramEntry] | 是 | 该校当前已整理的目标项目 |

---

## 5. ProgramEntry

表示某所学校下的一年制汉语学习项目记录。

> 该结构是售前推荐表和 RAG 检索共同依赖的项目库基础单元。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `program_id` | string | 是 | 项目唯一标识 |
| `university` | string | 是 | 学校名称 |
| `city` | string | 是 | 所在城市 |
| `program_name` | string | 是 | 官网项目名称 |
| `program_type` | string | 是 | 当前固定为 `one_year_chinese_program` |
| `admission_cycle` | string | 是 | 招生季 |
| `instruction_language` | string | 是 | 授课语言 |
| `duration_text` | string | 是 | 学制说明，如 `1 year` |
| `tuition_amount` | number/null | 是 | 学费金额；官网未说明为 `null` |
| `tuition_currency` | string/null | 是 | 币种，如 `CNY` |
| `tuition_period` | string/null | 是 | `year`、`semester`、`program` 等 |
| `application_deadline` | date/null | 是 | 申请截止日期；未知为 `null` |
| `requirements` | ProgramRequirements | 是 | 项目申请要求 |
| `evidence` | array[EvidenceRef] | 是 | 官网证据列表 |
| `verification_status` | string | 是 | `verified`、`partial`、`conflicting`、`stale`、`unverified` |
| `review_flags` | array[string] | 是 | 字段缺失或待确认时的人工处理标记，如 `needs_manual_review:application_deadline` |
| `last_reviewed_at` | datetime/null | 是 | 最近人工复核时间 |

> 缺失信息处理原则：官网找不到完整信息时，字段使用 `null`，并在 `review_flags` 中标记 `needs_manual_review:<field>`；不得由模型猜测补齐。

---

## 6. ProgramRequirements

从官网 requirements 中整理出的、售前需要判断的字段。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `education_level_required` | string/null | 是 | 所需学历背景 |
| `chinese_level_required` | string/null | 是 | 中文要求 |
| `hsk_level_required` | integer/null | 是 | HSK 等级要求 |
| `hsk_score_required` | integer/null | 是 | HSK 分数要求 |
| `ielts_score_required` | number/null | 是 | IELTS 要求 |
| `toefl_score_required` | number/null | 是 | TOEFL 要求 |
| `other_requirements` | array[string] | 是 | 其他要求摘要 |

---

## 7. EvidenceRef

每条关键项目数据都应能追溯到官网来源。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `source_id` | string | 是 | 官方来源 ID |
| `source_url` | string | 是 | 官网 URL |
| `source_title` | string | 是 | 页面或文件标题 |
| `source_quote` | string | 是 | 原文短句证据 |
| `admission_cycle` | string | 是 | 招生季 |
| `accessed_at` | date | 是 | 访问日期 |

---

## 7.5 城市库证据预检

实现位置：`src/study_abroad/catalog_validation.py`。

预检规则：

- active 学校项目必须有 Evidence；
- Evidence 的 `source_id` 必须能在本地来源集合中找到；
- Evidence 的 `source_url` 必须与来源记录一致；
- `source_quote` 必须出现在对应来源正文中，比较时仅做空白与大小写归一化；
- 预检失败只报告问题，不自动修改数据。

南京 CityPack 已用 4 个真实官方页面完成一次预检，结果为 0 个证据问题。

### 来源快照

- 可版本化来源元数据：`data/city_packs/nanjing_sources.json`
- 原始 HTML 快照：`.local/sources/nanjing/`，不上传 GitHub
- 加载器：`src/study_abroad/source_snapshots.py`
- 快照路径必须位于项目根目录内，禁止目录穿越
- 预检可离线复现，不依赖临时联网页面

---

## 8. JSON 示例

```json
{
  "city_pack_id": "nanjing_pack_v1",
  "city": "Nanjing",
  "country": "China",
  "target_program_type": "one_year_chinese_program",
  "admission_cycle": "2027_fall",
  "version": "v1",
  "created_at": "2026-11-23T10:00:00Z",
  "updated_at": "2026-11-23T10:00:00Z",
  "universities": [
    {
      "university": "Nanjing University",
      "city": "Nanjing",
      "tier_hint": "reach",
      "official_programs": [
        {
          "program_id": "nju_2027_one_year_chinese",
          "university": "Nanjing University",
          "city": "Nanjing",
          "program_name": "One-Year Chinese Language Program",
          "program_type": "one_year_chinese_program",
          "admission_cycle": "2027_fall",
          "instruction_language": "Chinese",
          "duration_text": "1 year",
          "tuition_amount": 26000,
          "tuition_currency": "CNY",
          "tuition_period": "year",
          "application_deadline": "2027-06-30",
          "requirements": {
            "education_level_required": "high_school",
            "chinese_level_required": "beginner_or_above",
            "hsk_level_required": null,
            "hsk_score_required": null,
            "ielts_score_required": null,
            "toefl_score_required": null,
            "other_requirements": [
              "International students",
              "One-year language study plan"
            ]
          },
          "evidence": [
            {
              "source_id": "nju_2027_chinese_program",
              "source_url": "https://example.edu/nju-chinese-program",
              "source_title": "Nanjing University One-Year Chinese Program",
              "source_quote": "One-year Chinese language program for international students.",
              "admission_cycle": "2027_fall",
              "accessed_at": "2026-11-23"
            }
          ],
          "verification_status": "partial",
          "last_reviewed_at": "2026-11-23T10:00:00Z"
        }
      ]
    }
  ]
}
```

---

## 9. 该数据契约如何支持当前 MVP

### 9.1 支持学生输入 Schema

`ProgramEntry.requirements` 是反推 `StudentIntake` 字段的重要依据。

例如：

- 项目要求 HSK → 学生表单需要收集 HSK；
- 项目要求预算 → 学生表单需要收集预算；
- 项目要求学历背景 → 学生表单需要收集当前学历。

### 9.2 支持推荐表输出 Schema

`RecommendationReport` 中的 `TierItem` 可直接从 `ProgramEntry` 派生：

- 学校名
- 项目名
- 学费
- 截止时间
- 要求摘要
- 证据引用

### 9.3 支持 RAG

`ProgramEntry` 及其 evidence 可以继续分块进入 Chroma，供售前顾问检索官网依据。

---

## 10. 当前边界

### 当前适合做什么

- 南京一年制汉语项目资料包；
- 城市维度学校池管理；
- 售前推荐表生成；
- 官网证据保留与检索。

### 当前不适合做什么

- 全国学校池；
- 多项目类型混合推荐；
- 自动录取概率判断；
- 没有官网证据的项目推荐。

---

## 11. 一句话总结

> CityPack 是“城市级可复用资产”的结构化载体，ProgramEntry 是售前推荐表和 RAG 检索共同依赖的最小项目单元。
