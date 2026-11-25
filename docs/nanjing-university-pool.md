# 南京候选学校池工作稿

## 1. 目的

本文档用于整理南京高校一年制汉语学习项目 Demo 的候选学校池。  
当前目标不是一次性确定全部正式推荐学校，而是先建立一套**候选池 → 数据核验 → active/pending 状态**的工作方法。

---

## 2. 学校池分层原则

南京学校池按两个维度维护：

### 2.1 学校梯度
用于售前推荐分层：

- `tier_985`
- `tier_211`
- `tier_regular_key`
- `tier_safety_accessible`

### 2.2 数据状态
用于决定是否进入当前正式推荐池：

- `active`：官网资料可得，已进入当前 CityPack
- `pending`：官网资料存在线索，但还没完成结构化核验
- `excluded_no_official_data`：官网资料不足，暂不纳入
- `excluded_out_of_scope`：不符合当前 MVP 范围

---

## 3. 当前候选学校池（工作稿）

> 说明：以下是候选池，不等于全部已进入 `data/city_packs/nanjing_pack_v1.json`。

| 学校 | 候选梯度 | 当前状态 | 备注 |
|---|---|---|---|
| 南京大学 | tier_985 | active | 已录入一条长期汉语进修项目记录，状态 `partial` |
| 东南大学 | tier_985 | active | 已补秋季申请截止日 2027-07-30；学制和学历要求仍待人工确认 |
| 南京理工大学 | tier_211 | pending | 已检索到“汉语进修项目”官网线索，待结构化 |
| 南京航空航天大学 | tier_211 | pending | 候选保留，待补官网项目页 |
| 河海大学 | tier_211 | active | 已录入 2022 汉语进修页（13,200 元/年、一学期及以上）；标记 `stale`，需确认 2027 页面 |
| 南京师范大学 | tier_211 | active | 已按 2027 指南“一年汉语后进入专业”录入 `partial`，独立项目属性、截止日期、学费表原文待人工确认 |
| 南京农业大学 | tier_211 | pending | 候选保留，待补官网项目页 |
| 中国药科大学 | tier_211 | pending | 候选保留，待补官网项目页 |
| 南京邮电大学 | tier_regular_key | pending | 候选保留，待补官网项目页 |
| 南京信息工程大学 | tier_regular_key | pending | 候选保留，待补官网项目页 |
| 南京工业大学 | tier_regular_key | active（safety） | 已录入语言预科项目（1 年、15,000 元/年）；招生季和截止日期未标注，`partial` |
| 南京林业大学 | tier_regular_key | pending | 候选保留，待补官网项目页 |
| 南京财经大学 | tier_regular_key | pending | 候选保留，待补官网项目页 |
| 南京审计大学 | tier_safety_accessible | pending | 候选保留，待补官网项目页 |
| 江苏第二师范学院 | tier_safety_accessible | pending | 候选保留，待补官网项目页 |
| 金陵科技学院 | tier_safety_accessible | pending | 候选保留，待补官网项目页 |

---

## 4. 当前已进入 CityPack 的学校

当前 `data/city_packs/nanjing_pack_v1.json` 中已有 5 所学校：

- 南京大学：`active`，已录入一条“长期汉语进修”项目骨架数据
- 东南大学：`active`，已录入“Chinese Language and Culture Program”部分记录；秋季截止日已由英文官网确认，但该页未明确写 2027 专属，招生季、学制和学历要求仍标记人工处理
- 河海大学：`active`，依据 2022 官网项目页录入 13,200 元/年、一学期及以上；数据标记 `stale`，2027 信息仍需确认
- 南京师范大学：`active`，依据 2027 申请指南中“一年汉语后进入专业”的表述录入 `partial` 记录，仍待确认独立项目属性、截止日期和学费表原文
- 南京工业大学：`active`，safety 档；依据官网语言预科页和收费页录入 1 年、15,000 元/年，招生季和截止日期未标注，标记 `partial`

缺失信息统一写入 `review_flags`，示例：

- `needs_manual_review:application_deadline`
- `needs_manual_review:education_requirement`
- `needs_manual_review:current_cycle_program_page`
- `needs_manual_review:standalone_program_scope`

> 注意：当前南京大学条目已进入 CityPack，但仍属于最小可运行数据，不等于南京真实项目库已经完成整理。

---

## 5. 目前从联网检索中已确认到的线索

以下只是“存在官网线索”，不是最终已结构化数据：

- 南京大学：已确认存在“长期汉语进修”页面，并已先录入 CityPack 骨架
- 东南大学：检索到海外教育学院、汉语课程和收费页面线索
- 河海大学：已录入 2022 汉语进修页（13,200 元/年），标记 `stale`
- 南京师范大学：检索到 2027 国际学生申请指南页面
- 南京工业大学：已录入语言预科项目页与收费页，1 年、15,000 元/年
- 南京理工大学：检索到“汉语进修项目”相关页面线索，尚未纳入当前 CityPack

其余候选仍先标为 `pending`，后续再决定是否转为 `active`。

---

## 6. 当前工作原则

1. 不硬编官网没有的信息；
2. 查不到足够资料的学校，先标 `pending` 或 `excluded_no_official_data`；
3. `active` 只用于已经进入当前 CityPack 的学校；
4. 候选池文档先于正式数据入库；
5. 后续要把候选池逐步转化为真实 `CityPack` 数据。

---

## 7. 下一步建议

1. 从 `pending` 学校中优先挑 3–5 所官网信息较完整的学校；
2. 逐所收集官网项目页或 PDF；
3. 把一年制汉语项目结构化进 `CityPack`；
4. 把无法核验的学校继续保留为 `pending`。

---

## 8. 一句话总结

> 当前南京学校池采用“候选池先行、官网核验后再进入 active”的工作方式，避免把资料不足的学校硬塞进推荐结果。
