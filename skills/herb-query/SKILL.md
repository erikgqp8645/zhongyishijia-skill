---
name: herb-query
description: "Use when the user asks about a single herb's bencao records, or wants to find all formulas containing a specific herb; triggers on phrases like '含有XX的方剂', 'XX的本草记载', '鸡血藤', '苍术', '查细辛', '这味药出现在哪些方剂里'."
---

# herb-query

## 核心能力

给定一味中药，返回：
1. 本药历代本草论述（《神农本草经》《名医别录》等，按朝代排序）
2. 含此药的所有方剂列表（按朝代排序）

## 工具

```
python scripts/herb_query.py <中药名>
python scripts/herb_query.py <中药名> --max-formulas 30
python scripts/herb_query.py <中药名> --excel output.xlsx
```

## 输入

- 中药名（必填）：如 `鸡血藤`、`苍术`、`细辛`

## 输出格式

**第一段**：本草论述 Markdown 表格

| 朝代 | 著作 | 作者 | 性味 | 归经 | 功能主治 |
|:----:|:----:|:----:|:----:|:----:|:--------|

**第二段**：含药方剂 Markdown 表格

| 朝代 | 著作 | 作者 | 方剂名 | 处方组成（节选） | 主治（节选） |
|:----:|:----:|:----:|:----:|:--------|:--------|

## Fallback 规则

| 触发条件 | 修复动作 |
|---------|---------|
| `herb_query.py` 无本草记录 | 告知用户"该药暂无本草数据" |
| `herb_query.py` 无方剂结果 | 尝试 `scripts/text_search.py <药名>` |
| 用户要求 Excel 输出 | 添加 `--excel <路径>` 参数 |

## 边界

- 不要在无 source_map 命中时编造朝代/作者
- 区分原文引用（【原文】）与推断（【推断】）
