---
name: formula-query
description: "Use when the user asks about a classical formula's composition, historical interpretations, or ancient text citations; triggers on phrases like 'XX汤治什么', 'XX方的组成', 'XX方历代注解', '查询XX方', '桂枝人参汤', '小柴胡汤'."
---

# formula-query

## 核心能力

给定方剂名，返回历代条文按朝代排序（东汉→现代）+ 作者归属 + 原文引用。

## 工具

```
python scripts/formula_query.py <方剂名>
python scripts/formula_query.py <方剂名> --max-cards 20
```

## 输入

- 方剂名（必填）：如 `桂枝人参汤`、`小柴胡汤`

## 输出格式

Markdown 表格：

| 朝代 | 著作 | 作者 | 原文论述摘要 | 卡片类型 |
|:----:|:----:|:----:|:-----------|:--------:|

## Fallback 规则

| 触发条件 | 修复动作 |
|---------|---------|
| `formula_query.py` 无结果 | 尝试 `scripts/text_search.py <方剂名>` 全文检索 |
| SQLite 文件找不到 | 明确告知用户"本地知识库未配置，请检查 --sqlite 参数" |

## 边界

- 只返回有历史文献依据的条文，不做方剂现代配伍解读
- 不要在无 source_map 命中时编造朝代/作者（返回"待考"时须标注）
- 区分原文引用（标注【原文】）与推断（标注【推断】）
