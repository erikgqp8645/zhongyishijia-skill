---
name: zhongyishijia-double-fetch
description: 当 zhongyishijia-skill 数据库截断或缺失时绕过蒸馏卡、用 SQLite 拿原文。
---

# zhongyishijia-double-fetch — 蒸馏卡截断时的双源取证流程

## 触发条件

只要在 zhongyishijia-expert-mentor-lineage skill 中命中以下任一情形，**立即**用本流程：

- `formula_query.py` summary 看起来可疑地短（280 字符临界值）
- `text_search.py` 0 命中，但用户问的明显是库里有的
- 用户贴出的文本与库内文本对不上（怀疑异文）
- books_json / SQLite / 蒸馏卡 三方对同一 chunk 给出不同内容

**核心规则**：蒸馏卡是 UI 层，**SQLite + books_json 才是 ground truth**。绝不只看蒸馏卡就宣告"查不到"。

---

## 三层数据架构

| 层 | 文件 | 角色 |
|----|------|------|
| **L0 原始库** | `references/raw/20120413mssql.sqlite`（660MB） | ground truth |
| **L1 同源备份** | `references/books_json/<book_id>_<书名>.json`（207MB） | 交叉验证 + 章节结构化 |
| **L2 蒸馏卡** | `references/text_distillation/evidence_cards.jsonl`（268MB） | UI 快速浏览，summary 280 字截断 |

CLAUDE.md 明确说 L2 summary 280 截断是设计行为，不是 bug——L2 定位是 UI 浏览，不是原文取证。

---

## 标准操作流程

### 1. 启动 L0 直查

```python
import sqlite3

SKILL = "/Users/applemima1111/.hermes/skills/zhongyishijia-expert-mentor-lineage"
DB = f"{SKILL}/references/raw/20120413mssql.sqlite"

conn = sqlite3.connect(DB)  # ⚠️ 不要 text_factory=gbk
cur = conn.cursor()
```

### 2. 用 chunk_id 反查 SQLite 原文

蒸馏卡的 `chunk_id` 形如 `zysjllsj:195478`，直接拿这个 ID 进 SQLite：

```python
chunk_id = "zysjllsj:195478"
table, row_id = chunk_id.split(":")
cur.execute(
    "SELECT ID, BiaoTi, NeiRong FROM zysjllsj WHERE ID = ?",
    (int(row_id),)
)
chunk_id, title, full_body = cur.fetchone()
print(f"完整原文长度: {len(full_body)}")  # 1535 字符（vs 蒸馏卡 summary 280）
```

### 3. 用 L1 books_json 交叉验证

L0 是扁平表，**整本古籍的章节上下文在 L1**：

```python
import json
with open(f"{SKILL}/references/books_json/1247_辅行诀脏腑用药法要.json") as f:
    book = json.load(f)

chapter_text = book["chapters"][2]["sections"][0]["entries"][0]["content"]
assert chapter_text == full_body, "L0 ↔ L1 不一致，需人工核查"
```

### 4. 输出时明确分层

```
【原文 L0 (zysjllsj:195478)】：<1535 字符完整>
【原文 L1 (books_json/1247)】：同上，互为验证
【蒸馏卡 L2 (card=xxx)】：<280 字截断版本>
   ⚠️ 蒸馏卡截到 XX 为止，之后全部丢失
```

---

## 实战案例：辅行诀·大补心汤第二方（2026-08-02 沉淀）

| 操作 | 结果 |
|------|------|
| L2 formula_query 大补心汤 | 3 张《千金》方命中，**没有辅行诀那张** |
| L2 card_id=5244b10dfb7695e7 | summary 截断到"小泻心汤第一方"为止 |
| L0 SELECT NeiRong FROM zysjllsj WHERE ID=195478 | **1535 字完整**——含辨心包络四方 + 大补心汤第二方 |
| L1 books_json/1247 chapter[2] | 同 1535 字，与 SQLite 完全一致 |
| 用户贴 [新校正]版 vs L0 全文 | 3 处关键异文 + 1 处新增二段主治 |

**关键教训**：
- 蒸馏卡 summary 截断 ≠ "这条只有这些"。要看全段必须 L0。
- 用户贴的"二段主治/新校正"在 L0/L1/L2 都没有 —— 整理本异文。
- 任何"原文核查"操作 **必须先 L0**。

异文校勘档案：`references/collations/fuxingjue_dabuxixin2_xinjiaozheng.json`

---

## 反例（曾犯过的错）

**❌ 错**：只信蒸馏卡，宣告"查不到"。

> 2026-08-01 老锅查"大补心包汤"，我只看蒸馏卡 summary 后说"0 命中，只展示到大补心汤（第二方）就被截断"。**实际上** SQLite zysjllsj 195478 里有完整辨心包络四方。

**✅ 对**：蒸馏卡截断 → 立即转 L0 → chunk_id 反查全段。

---

## Pitfalls

1. **不要看到 0 命中就宣告**——SQLite zysjllsj 可能独立存有。
2. **不要轻信 L2 summary 长度**——所有 summary 都是 280 截断。
3. **不要只查 L0 不查 L1**——L0 扁平，章节上下文在 L1。两个都查，互校验。
4. **不要修改 evidence_cards.jsonl**——CLAUDE.md 禁用，走 LFS。
5. **不要修改 SQLITE_PITFALLS.md**——用户自有 skill，curator 不直写。
6. **不要手动追加 L2 新卡**——异文归档走 `references/collations/`，不污染 LFS。

---

## 异文校勘档案目录

`references/collations/` 目录收容独立异文卡，**不污染 evidence_cards.jsonl**。每张异文卡格式：

```json
{
  "collation_id": "...",
  "anchor_chunk_l0": "zysjllsj:195478",
  "anchor_book_l1": "books_json/...",
  "anchor_card_l2": "card_id=...",
  "ground_truth": {"L0": ..., "L1": ..., "L1↔L0_consistency": ...},
  "variant_source": "...",
  "variant_diffs": [...],
  "evidence_status": "unverified",
  "review_items": [...]
}
```

---

## 相关文档

- `references/raw/SQLITE_PITFALLS.md` — 字段陷阱
- `references/install-path.md` — 安装 / LFS 状态
- `docs/PLAN_v3_query_herb.md` — v3.0 重蒸馏规划（含 summary 截断修复方向）

