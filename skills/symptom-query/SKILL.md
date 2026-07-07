---
name: symptom-query
description: "Use when the user describes a symptom or disease and asks what core herbs to use, or asks for high-frequency herb analysis for a condition; triggers on phrases like 'XX症状用什么药', 'XX的高频核心药', '皮肤瘙痒用什么药', '中风病人吃什么药', '风疹怎么治'."
---

# symptom-query

## 核心能力

基于"唐宋古方研读方法论"：
1. 找到所有含该症状的方剂
2. 统计所有药物出现频次
3. 筛选高频核心药，回归《神农本草经》《名医别录》溯源印证

## 工具

```
python scripts/symptom_query.py <症状关键词>
python scripts/symptom_query.py <症状关键词> --top 10
python scripts/symptom_query.py 皮肤瘙痒 --top 5
python scripts/symptom_query.py 中风 --top 5
```

## 输入

- 症状关键词（必填）：如 `皮肤瘙痒`、`中风`、`风疹`
- `--top N`：输出前 N 味高频药（默认 10）

## 输出格式

**第一段**：方剂总览表

| # | 方剂名 | 药味数 | 功能主治（节选） |

**第二段**：药物频次统计

| # | 药物 | 出现频次 | 占比 |
|:---:|:---|:---:|:---:|

**第三段**：高频药本草原始条文溯源

每味高频药附《神农本草经》《名医别录》原始条文引用。

## Fallback 规则

| 触发条件 | 修复动作 |
|---------|---------|
| `symptom_query.py` 无结果 | 告知"暂无该症状方剂数据，建议描述更具体症状或查阅辨证章节" |
| SQLite 找不到 | 明确告知用户"本地知识库未配置" |

## 边界

- 高频药结论须有本草原文支撑，不要仅凭现代中药学知识推断
- 区分原文（【原文】）与推断（【推断】）
