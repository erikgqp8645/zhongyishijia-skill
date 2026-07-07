---
name: evidence-fetch
description: "Use when the user provides a card_id or chunk_id and wants the original source text; triggers on phrases like 'card_id:bb4302e01c4c1b50', 'chunk_id:zysjyj:122', '查这个原文', '取出证据原文'."
---

# evidence-fetch

## 核心能力

给定 `card_id` 或 `chunk_id`，取出原始出处原文 + 关联证据卡片。

## 工具

```
python scripts/evidence_fetch.py --card-id <card_id>
python scripts/evidence_fetch.py --chunk-id <chunk_id>
python scripts/evidence_fetch.py --card-id <id> --context-chars 8000
```

## 输入

- `--card-id <id>`：证据卡片 ID（如 `bb4302e01c4c1b50`）
- `--chunk-id <id>`：原始文本块 ID（如 `zysjyj:122`）
- `--context-chars N`：周围上下文字符数（默认 2000）

## 输出格式

JSON：

```json
{
  "chunk": {
    "chunk_id": "zysjyj:122",
    "source_path": "...",
    "text": "..."
  },
  "cards": [
    {"card_id": "...", "title": "...", "summary": "..."}
  ]
}
```

## Fallback 规则

| 触发条件 | 修复动作 |
|---------|---------|
| card_id/chunk_id 不存在 | 告知用户"未找到对应证据，请核实 ID" |
| evidence_cards.jsonl 不存在 | 告知用户"证据库文件不存在" |

## 边界

- 只取出原始文本，不做解读或推断
- 严格保留原文文字，不修改
