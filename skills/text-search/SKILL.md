---
name: text-search
description: "Use when the user wants a keyword search across all evidence cards and reference files; triggers on phrases like '搜索XX', '查一下XX', '全文检索XX', '关键词XX' (when no specific formula or herb name is given)."
---

# text-search

## 核心能力

对 31.7 万张证据卡 + 所有 reference 文件做关键词全文检索。

## 工具

```
python scripts/text_search.py <关键词>
python scripts/text_search.py <关键词> --limit 80
```

## 输入

- 关键词（必填）

## 输出格式

Markdown 列表，最多 80 条匹配，超出提示 `"... N more matches"`。

每条输出：`card_id`、`title`、`summary`、匹配片段。

## Fallback 规则

| 触发条件 | 修复动作 |
|---------|---------|
| 匹配结果为 0 | 告知用户"未找到匹配结果" |
| evidence_cards.jsonl 不存在 | 告知用户"证据库文件不存在" |

## 边界

- 全文检索结果噪音较大，结果需标注来源
- 不要把检索结果直接当作最终答案，应引导到具体查询工具
