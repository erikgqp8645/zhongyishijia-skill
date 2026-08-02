# {formula_name}历代医家注解汇编

> **数据来源**：中医世家知识库（zysj.com.cn）2012-2014年离线数据
> **证据卡片数**：{card_count}条（主卡片）/ {total_matches}条（总提及）
> **时间跨度**：{time_span}
> **检索字段**：方剂名「{formula_name}」

---

## 一、出处溯源

### 1.1 经典原文

{classic_origins}

### 1.2 组成

{composition_table}

### 1.3 煎服法

{usage_table}

---

## 二~九、历代医家注解（按朝代展开）

{dynasty_sections}

---

## 十、病机归纳

### 10.1 核心病机

> **{core_pathogenesis}**

### 10.2 病因病机表

| 病因 | 病机 |
|:----:|:-----|
{pathogenesis_table}

### 10.3 证候要点表

| 症状 | 病机解释 |
|:-----|:--------|
{symptoms_table}

### 10.4 治法方解

{prescription_analysis}

---

## 十一、方剂演变

### 11.1 家族方剂演变树

```
{formula_family_tree}
```

### 11.2 相关方剂辨析

| 方剂名 | 与本方关系 | 区别要点 |
|:------:|:----------|:---------|
{related_formulas_table}

---

## 十二、临床应用

### 12.1 经典适应症

| 病证 | 表现 | 治法 |
|:----:|:-----|:-----|
{classic_indications_table}

### 12.2 现代对应

| 中医病证 | 现代疾病 | 证据来源 |
|:---------|:---------|:---------|
{modern_diseases_table}

### 12.3 现代应用

| 分类 | 记载 |
|:----:|:-----|
{modern_applications_table}

---

## 十三、历代剂量换算

### 13.1 原方剂量

{original_dosage_table}

### 13.2 现代参考剂量

{modern_dosage_table}

### 13.3 古今折算说明

> **注**：古今剂量差异较大（东汉1两≈3-15g，常用折算≈3g；1升≈200ml），以上按东汉1两≈3g折算。
> 临床应用应根据患者具体情况、病情轻重缓急以及地域差异调整。

---

## 附录A：证据索引

| 朝代 | 著作 | 作者 | card_id |
|:----:|:----:|:----:|:--------|
{evidence_index}

---

## 附录B：使用说明

> 本报告由 `formula_query.py` 自动检索 `evidence_cards.jsonl` 生成，结合 `templates/formula_report_template.md` 模板渲染。
>
> **数据基础**：
> - 中医世家网站（zysj.com.cn）2012-2014年离线数据
> - 31.7万张证据卡（中药+方剂+临床理论+综合数据）
> - 678本古籍+1800年跨朝代文献
>
> **使用提示**：
> - "主卡片"指 title 包含该方剂名的卡片，是直接相关论述
> - "次卡片"指 title 不含但正文中提及的卡片，已过滤不混入主章节
> - 临床应用部分为经典理论与现代研究的整理，**仅供参考，不替代专业医生诊疗**

---

*本文档由中医世家知识库（zysj.com.cn）evidence_cards.jsonl 自动检索生成*
*检索时间：{query_date}*
*主卡片数：{card_count}条 / 总匹配数：{total_matches}条*