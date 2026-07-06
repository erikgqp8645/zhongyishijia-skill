[根目录](../../../CLAUDE.md) > [references](../../CLAUDE.md) > **text_distillation**

# references/text_distillation — 蒸馏数据

> **职责**：把 660MB 原始 SQLite 蒸馏为 232MB evidence_cards.jsonl，供 Agent 高效检索。
> **状态**：v1.0 31.7 万张已交付（git-lfs）；v3.0 计划重蒸馏 + 新增 herb_index.jsonl。

---

## 模块职责

存储**蒸馏后的结构化证据数据**：

1. **核心证据库** — `evidence_cards.jsonl`（31.7 万张，git-lfs）
2. **(v3.0) 反向索引** — `herb_index.jsonl`（约 18,000 条，git-lfs）

蒸馏过程（build_evidence_cards.py 内含）：
- 从 `zysjyj`（中药字典）生成 herb cards
- 从 `zysjllsj`（临床理论）生成 clinical_theory cards
- 从 `zysjzhsj`（综合数据）生成 synthesis cards
- 摘要截断 280 字符 / 卡片平均 766 字节

---

## 文件清单

| 文件 | 大小 | 行数 | git-lfs | 说明 |
|------|-----:|-----:|:------:|------|
| `evidence_cards.jsonl` | 232 MB | 317,580 | ✅ | 31.7 万张 evidence cards |
| `herb_index.jsonl` (v3.0 计划) | ~5-10MB | ~18,000 | ✅ | 中药反向索引 |

---

## 入口与启动

### evidence_cards.jsonl 数据样例

```json
{"card_id": "bb4302e01c4c1b50", "card_type": "herb", "title": "麻黄汤", "summary": "处方:麻黄（去节）6g 桂枝4g 杏仁（去皮尖）9g 甘草（炙）3g；主治:外感风寒。恶寒发热，头痛身疼，无汗而喘，舌苔薄白，脉浮紧。；用法:上四味，以水九升，先煮麻黄减二升，去上沫，内诸药煮去二升半，去滓，温服八合，覆取微似汗，不须啜粥，余如桂枝法将息。；出处:《伤寒论》", "source_ref": "《伤寒论》", "chunk_id": "zysjyj:122", "tags": ["中药", "TypeID:39"], "alias": null, "pinyin": null}
```

### herb_index.jsonl 数据样例（v3.0 计划）

```json
{"herb": "细辛", "sqlite_id": 25999, "type": "material", "in_formula_ids": [5358, 1613, 1237, ...]}
{"herb": "麻黄", "sqlite_id": 25789, "type": "material", "in_formula_ids": [...]}
```

---

## 对外接口

### Agent / 脚本读取方式

```bash
# 关键词检索（流式，避免一次性读 232MB 到内存）
python scripts/search_course_notes.py 桂枝人参汤

# 按 card_id 取
python scripts/fetch_course_evidence.py --card-id bb4302e01c4c1b50

# 直接读取（Python）
python -c "
import json
with open('references/text_distillation/evidence_cards.jsonl', encoding='utf-8') as f:
    for line in f:
        card = json.loads(line)
        # process card
        break
"
```

---

## 关键依赖与配置

### git-lfs

`.gitattributes`：
```
references/text_distillation/evidence_cards.jsonl filter=lfs diff=lfs merge=lfs -text
```

### 体积约束

- 旧版本：~233MB / 317,580 行（v1.0）
- v3.0 重蒸馏后：体积增长（每张卡 + 4-5 个字段，估算 +20% = ~280MB）

### 备份

`docs/PLAN_v3_query_herb.md` 工作流 5 要求：
- 重蒸馏前必须备份原文件为 `evidence_cards.jsonl.bak`
- 脚本失败时保留原文件

---

## 数据模型

### evidence_cards.jsonl 每行字段（v1.0）

| 字段 | 类型 | 含义 | 示例 |
|------|------|------|------|
| `card_id` | str | 16 位 hex | `bb4302e01c4c1b50` |
| `card_type` | str | 类型 | `herb` / `clinical_theory` / `synthesis` |
| `title` | str | 标题 | `麻黄汤` |
| `summary` | str | 摘要（≤280 字符） | `处方:...；主治:...` |
| `source_ref` | str | 来源引用（字符串） | `《伤寒论》` |
| `chunk_id` | str | 锚点 | `zysjyj:122` |
| `tags` | list[str] | 标签 | `["中药", "TypeID:39"]` |
| `alias` | str \| null | 别名 | `null` |
| `pinyin` | str \| null | 拼音 | `null` |

### v3.0 新增字段（计划）

| 字段 | 类型 | 含义 |
|------|------|------|
| `card_kind` | str | `herb_material` / `formula` / `clinical_theory` / `synthesis` |
| `dynasty` | str | 结构化朝代（来自 SOURCE_MAP） |
| `book` | str | 结构化著作 |
| `author` | str | 结构化作者 |
| `prescribed_herbs` | list[str] | 方剂含的药材（仅 formula） |

### 统计（v1.0）

| card_type | 来源表 | 行数 | 占比 |
|-----------|--------|-----:|-----:|
| `herb` | zysjyj | 70,350 | 22.1% |
| `clinical_theory` | zysjllsj | 166,421 | 52.4% |
| `synthesis` | zysjzhsj | 80,809 | 25.4% |
| **总计** | | **317,580** | **100%** |

---

## 测试与质量

### 数据完整性校验

```bash
# 行数校验
python -c "
import json
n = sum(1 for _ in open('references/text_distillation/evidence_cards.jsonl', encoding='utf-8'))
assert n == 317580, f'expected 317580, got {n}'
print(f'✓ {n} cards')
"

# card_type 分布校验
python -c "
import json
from collections import Counter
c = Counter()
with open('references/text_distillation/evidence_cards.jsonl', encoding='utf-8') as f:
    for line in f:
        c[json.loads(line).get('card_type')] += 1
assert c['herb'] == 70350, c
assert c['clinical_theory'] == 166421, c
assert c['synthesis'] == 80809, c
print('✓ 分布正确', dict(c))
"
```

### git-lfs 验证

```bash
git lfs ls-files | grep evidence_cards.jsonl
# 应输出: <hash> * references/text_distillation/evidence_cards.jsonl
```

---

## 常见问题 (FAQ)

**Q: 为什么不直接用 SQLite？**
A: SQLite 660MB 不入 git；evidence_cards.jsonl 232MB 用 git-lfs 可入库，且每张卡平均 766 字节，便于 Agent 流式检索。

**Q: 蒸馏丢失了哪些信息？**
A: 主要是 `zysjyj.FuFang`（含此药的所有方剂）字段被压进 summary；TYPEID=39 vs 40 区分被合并到 `card_type=herb`。v3.0 重蒸馏恢复。

**Q: 怎么重蒸馏？**
A: v3.0 计划：`python scripts/redistill_cards.py`（详见 [docs/PLAN_v3_query_herb.md §三.5](../../../docs/PLAN_v3_query_herb.md)）。

**Q: HTML 实体乱码（如 `&amp;#236;`）怎么办？**
A: 脚本输出端用 `html.unescape()`，v3.0 计划在 `clean_summary()` 中加入。

---

## 相关文件清单

- [`../raw/CLAUDE.md`](../raw/CLAUDE.md) — 原始数据字典（与 evidence_cards 是源 vs 派生的关系）
- [`../../text_sources/chunks.jsonl`](../../text_sources/chunks.jsonl) — 证据块（fetch_course_evidence.py 读取）
- [`../../../scripts/CLAUDE.md`](../../../scripts/CLAUDE.md) — 读取 evidence_cards 的 4 个脚本
- [`../../../docs/PLAN_v3_query_herb.md`](../../../docs/PLAN_v3_query_herb.md) — v3.0 重蒸馏计划

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- 无数据改动

### v3.0（计划中）
- 新增 `herb_index.jsonl`（反向索引，~18,000 条）
- 重蒸馏 evidence_cards.jsonl（新增 5 个结构化字段）

### v1.0 (2026-07-01)
- lineage-skill build_course_skill.py 首次蒸馏（317,580 张卡片）