# 售前工作流契约：学生输入与推荐表输出

## 1. 设计原则

本 MVP 的输入与输出不是围绕“自由问答”设计，而是围绕**售前推荐表工作流**设计。

核心原则有三条：

1. **从官网项目 requirements 反推输入字段**  
   学生表单字段优先来自目标项目真正需要判断的条件，而不是拍脑袋设计。

2. **先服务售前沟通，不直接做录取判断**  
   当前系统输出的是“顾问可读、可解释的推荐表”，不是“自动录取结论”。

3. **保留证据与缺失信息**  
   每个推荐项都应能追溯到官网证据，并明确哪些信息仍缺失或需人工确认。

---

## 2. 学生输入 Schema（StudentIntake）

> 用途：在售前阶段收集学生背景，供顾问或系统生成第一轮学校推荐表。

### 2.1 顶层结构

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `intake_id` | string | 是 | 本次填写记录的唯一标识 |
| `student_ref` | string/null | 是 | 学生编号或匿名引用；没有则为 `null` |
| `preferred_city` | string | 是 | 首选城市，例如 `Nanjing` |
| `backup_cities` | array[string] | 是 | 备选城市列表；无则为空数组 |
| `target_program_type` | string | 是 | 当前固定为 `one_year_chinese_program` |
| `target_intake_cycle` | string | 是 | 目标入学季，例如 `2027_spring`、`2027_fall` |
| `created_at` | datetime | 是 | 填写时间 |

---

### 2.2 教育背景（education）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `current_education_level` | string | 是 | 当前最高学历，如 `high_school`、`bachelor` |
| `graduation_status` | string | 是 | `graduated`、`expected_graduation`、`in_progress` |
| `school_name` | string/null | 是 | 当前或毕业学校；未知为 `null` |
| `gpa_or_ranking` | string/null | 是 | GPA、排名或成绩描述；未知为 `null` |

---

### 2.3 语言背景（language）

> 说明：字段值允许为 `null`，表示尚未提供，而不是“没有”。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `native_language` | string | 是 | 母语，如 `Vietnamese` |
| `chinese_level` | string/null | 是 | 如 `none`、`beginner`、`intermediate`、`advanced` |
| `hsk_level` | integer/null | 是 | HSK 等级；未知为 `null` |
| `hsk_score` | integer/null | 是 | HSK 分数；未知为 `null` |
| `ielts_score` | number/null | 是 | IELTS 总分；未知为 `null` |
| `toefl_score` | integer/null | 是 | TOEFL 总分；未知为 `null` |
| `other_language_cert` | string/null | 是 | 其他语言证明说明；未知为 `null` |

---

### 2.4 预算与偏好（constraints）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `annual_budget_cny` | number/null | 是 | 每学年预算上限；未知为 `null` |
| `preferred_school_tiers` | array[string] | 是 | 可接受学校档次，如 `reach`、`match`、`safety` |
| `preferred_campus_type` | string/null | 是 | 如 `urban`、`suburban`、`no_preference` |
| `needs_dormitory` | boolean/null | 是 | 是否需要宿舍；未知为 `null` |

---

### 2.5 个性化问题（preferences）

> 说明：这些字段不直接决定是否“录取”，但会影响推荐表解释和梯度排序。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `preferred_universities` | array[string] | 是 | 学生特别想去的学校 |
| `excluded_universities` | array[string] | 是 | 明确不想考虑的学校 |
| `priority_ranking` | array[string] | 是 | 排序优先级，如 `city`、`school_tier`、`cost`、`language` |
| `special_notes` | string/null | 是 | 顾问或学生补充说明 |

---

### 2.6 推荐 JSON 示例

```json
{
  "intake_id": "intake_2026_0001",
  "student_ref": null,
  "preferred_city": "Nanjing",
  "backup_cities": ["Suzhou", "Hangzhou"],
  "target_program_type": "one_year_chinese_program",
  "target_intake_cycle": "2027_fall",
  "created_at": "2026-11-23T10:00:00Z",
  "education": {
    "current_education_level": "high_school",
    "graduation_status": "expected_graduation",
    "school_name": "Hanoi High School",
    "gpa_or_ranking": "top 20%"
  },
  "language": {
    "native_language": "Vietnamese",
    "chinese_level": "beginner",
    "hsk_level": null,
    "hsk_score": null,
    "ielts_score": 6.0,
    "toefl_score": null,
    "other_language_cert": null
  },
  "constraints": {
    "annual_budget_cny": 30000,
    "preferred_school_tiers": ["reach", "match", "safety"],
    "preferred_campus_type": "no_preference",
    "needs_dormitory": true
  },
  "preferences": {
    "preferred_universities": [],
    "excluded_universities": [],
    "priority_ranking": ["city", "school_tier", "cost"],
    "special_notes": "Student prefers schools with stronger international student support."
  }
}
```

---

## 3. 推荐表输出 Schema（RecommendationReport）

> 用途：把学生输入转成顾问可读的售前推荐结果。  
> 重点不是“最终录取结论”，而是“第一轮推荐表”。

### 3.1 顶层结构

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `report_id` | string | 是 | 推荐表唯一标识 |
| `intake_id` | string | 是 | 对应的学生输入 ID |
| `city` | string | 是 | 本次推荐对应城市 |
| `target_program_type` | string | 是 | 当前固定为 `one_year_chinese_program` |
| `generated_at` | datetime | 是 | 推荐表生成时间 |
| `summary` | string | 是 | 面向顾问的简短总结 |
| `tiers` | array[Tier] | 是 | 学校梯度推荐结果 |
| `missing_fields` | array[string] | 是 | 当前仍缺失、建议补充的信息 |
| `disclaimer` | string | 是 | 售前参考声明 |

---

### 3.2 学校梯度 Tier

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `tier_name` | string | 是 | `reach`、`match`、`safety` |
| `tier_label` | string | 是 | 展示名，如“冲刺档”“匹配档”“保底档” |
| `items` | array[TierItem] | 是 | 该梯度下的学校推荐项 |

---

### 3.3 推荐项 TierItem

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `university` | string | 是 | 学校名称 |
| `city` | string | 是 | 学校所在城市 |
| `program_name` | string | 是 | 项目名称 |
| `program_type` | string | 是 | 项目类型 |
| `instruction_language` | string | 是 | 授课语言 |
| `duration_text` | string | 是 | 学制说明 |
| `tuition_amount` | number/null | 是 | 学费金额；官网未说明为 `null` |
| `tuition_currency` | string/null | 是 | 币种，如 `CNY` |
| `tuition_period` | string/null | 是 | `year`、`semester`、`program` 等 |
| `application_deadline` | date/null | 是 | 截止日期；未知为 `null` |
| `requirement_summary` | array[string] | 是 | 官网 requirements 摘要 |
| `fit_summary` | string | 是 | 为什么放入该梯度，或为什么暂不推荐 |
| `flags` | array[string] | 是 | 如 `missing_budget`、`needs_manual_review`、`language_requirement_unclear` |
| `evidence` | array[EvidenceRef] | 是 | 官网证据引用 |

---

### 3.4 证据引用 EvidenceRef

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `source_id` | string | 是 | 官方来源 ID |
| `source_url` | string | 是 | 官网 URL |
| `source_title` | string | 是 | 页面或文件标题 |
| `source_quote` | string | 是 | 支持该推荐项的原文短句 |
| `admission_cycle` | string | 是 | 招生季 |
| `accessed_at` | date | 是 | 访问日期 |

---

## 4. 输出 JSON 示例

```json
{
  "report_id": "report_2026_0001",
  "intake_id": "intake_2026_0001",
  "city": "Nanjing",
  "target_program_type": "one_year_chinese_program",
  "generated_at": "2026-11-23T10:05:00Z",
  "summary": "Based on the current intake information, Nanjing options can be organized into reach, match, and safety tiers for initial consultation.",
  "tiers": [
    {
      "tier_name": "reach",
      "tier_label": "冲刺档",
      "items": [
        {
          "university": "Nanjing University",
          "city": "Nanjing",
          "program_name": "One-Year Chinese Language Program",
          "program_type": "one_year_chinese_program",
          "instruction_language": "Chinese",
          "duration_text": "1 year",
          "tuition_amount": 26000,
          "tuition_currency": "CNY",
          "tuition_period": "year",
          "application_deadline": "2027-06-30",
          "requirement_summary": [
            "High school diploma or equivalent",
            "HSK 4 preferred"
          ],
          "fit_summary": "Placed in reach tier because of school tier and current language profile.",
          "flags": ["needs_manual_review"],
          "evidence": [
            {
              "source_id": "nju_2027_chinese_program",
              "source_url": "https://example.edu/nju-chinese-program",
              "source_title": "Nanjing University 2027 Chinese Program",
              "source_quote": "One-year Chinese language program for international students.",
              "admission_cycle": "2027_fall",
              "accessed_at": "2026-11-23"
            }
          ]
        }
      ]
    }
  ],
  "missing_fields": ["hsk_level", "hsk_score"],
  "disclaimer": "This report is for pre-sales consultation only and is not an admission decision."
}
```

---

## 5. 当前 Schema 的使用边界

### 5.1 这套 Schema 现在能支持什么

- 顾问标准化收集学生信息；
- 城市级项目库输出；
- 按学校梯度组织推荐结果；
- 为每个推荐项挂官网证据；
- 明确缺失字段和人工复核点。

### 5.2 这套 Schema 暂时不支持什么

- 自动判断“一定能录取”；
- 自动给出全国学校最优排序；
- 申请流程状态跟踪；
- 复杂多轮对话式自由问答。

---

## 6. 与 AI 技术栈的关系

这套 Schema 是后续 LangChain / RAG / LangGraph 工作流的输入输出契约。

### LangChain
- 从官网资料抽取 `TierItem` 中需要的结构化字段；
- 将缺失字段整理为 `missing_fields`。

### RAG
- 根据城市和项目类型检索相关官网依据；
- 支持推荐表中的 `evidence` 回填。

### LangGraph
- 根据 `missing_fields` 决定是否需要追问；
- 在推荐表生成前执行必要检查；
- 必要时进入人工确认节点。

---

## 7. 一句话总结

> `StudentIntake` 负责把学生售前信息结构化，`RecommendationReport` 负责把官网项目库转成顾问可读、按学校梯度组织的推荐结果。

---

## 8. 复习用：核心模型关系图

### 8.1 先记一句话

> **Program / Evidence 是“官网项目库”的模型；StudentIntake / RecommendationReport 是“售前工作流”的模型。**

---

### 8.2 它们分别解决什么问题

| 模型 | 所属层级 | 解决的问题 |
|---|---|---|
| `Program` | 官网项目库层 | 一个项目本身有哪些字段，比如学校、项目名、学费、要求、截止日期 |
| `Evidence` | 官网项目库层 | 每个关键字段的官网证据是什么，来自哪个 URL、哪句原文 |
| `StudentIntake` | 售前工作流层 | 学生填写了哪些背景信息，比如城市、预算、语言成绩 |
| `RecommendationReport` | 售前工作流层 | 系统最终输出什么推荐表，给顾问或学生看 |

---

### 8.3 一条主线理解

```text
StudentIntake（学生输入）
        ↓
CityPack / ProgramCatalog（城市项目库）
        ↓
RecommendationReport（推荐表输出）
```

其中：

- `Program / Evidence` 属于项目库层；
- `StudentIntake / RecommendationReport` 属于工作流层；
- `CityPack / UniversityEntry / ProgramEntry` 则把项目库组织成“城市资产包”。

---

### 8.4 举个例子

学生填写：

```text
想去南京
读一年制汉语项目
预算 3 万以内
HSK 暂无
```

系统里已有官网项目库：

```text
南京大学一年制汉语项目
东南大学一年制汉语项目
南京师范大学一年制汉语项目
...
```

最后输出：

```text
冲刺档：南京大学
匹配档：东南大学
保底档：南京师范大学
```

在这条链路里：

- `StudentIntake` 保存学生输入；
- `Program` 保存每个学校项目的官网结构化信息；
- `Evidence` 保存这些项目字段对应的官网证据；
- `RecommendationReport` 保存最终给顾问看的推荐结果。

---

### 8.5 面试时怎么解释

你可以直接这样说：

> Program 和 Evidence 是项目库层模型，用来表示官网项目事实及其证据；StudentIntake 和 RecommendationReport 是售前工作流模型，用来表示学生输入和推荐表输出。前者解决“官网知识怎么沉淀”，后者解决“顾问怎么使用这些知识”。

---

### 8.6 和城市包的关系

```text
CityPack
  └─ UniversityEntry
       └─ ProgramEntry
            ├─ requirements
            └─ evidence
```

可以把它们理解成：

- `Program / Evidence`：更偏底层事实建模；
- `ProgramEntry / CityPack`：更偏城市资产组织；
- `StudentIntake / RecommendationReport`：更偏业务流程输入输出。
