[根目录](../../CLAUDE.md) > **scripts**

# scripts — Agent 工具集

> **职责**：Agent 在 reasoning / 取证时调用的 Python 工具。
> **状态**：v1.0 已交付 4 个脚本；v3.0 计划新增 3 个 + 重构 1 个（详见 [../docs/PLAN_v3_query_herb.md](../docs/PLAN_v3_query_herb.md)）。

---

## 模块职责

为 Agent 提供以下能力：

1. **关键词检索** — 在 31.7 万张 evidence cards + 所有 references 中找匹配
2. **朝代排序查询** — 按朝代从古至今展示某方剂的历代医家论述
3. **证据取回** — 按 card_id / chunk_id 取出原文与关联卡片
4. **Markdown 全文检索** — 在原始 markdown 数据中找上下文
5. **(v3.0) 中药查方剂** — 给定一味中药，反查所有方剂及成书年代
6. **(v3.0) 反向索引构建** — `build_herb_index.py` 构建 herb_index.jsonl
7. **(v3.0) 重蒸馏** — 给 evidence_cards.jsonl 加结构化字段

---

## 文件清单

| 文件 | 行数（约） | 用途 | 状态 |
|------|-----------:|------|:----:|
| `search_course_notes.py` | 72 | 关键词检索（Agent 主入口） | v1.0 |
| `query_formula.py` | 286 | 标准化方剂查询（按朝代排序） | v2.0 |
| `fetch_course_evidence.py` | 81 | 按 chunk_id/card_id 取证据 | v1.0 |
| `search_md.py` | 78 | 全 markdown 文件检索 | v1.0 |
| `_source_map.py` | — | 共用朝代/作者映射模块 | v3.0 计划 |
| `query_herb.py` | — | 按中药查本药 + 含此药方剂 | v3.0 计划 |
| `build_herb_index.py` | — | 构建反向索引 herb_index.jsonl | v3.0 计划 |
| `redistill_cards.py` | — | 重蒸馏 evidence_cards.jsonl | v3.0 计划 |

---

## 入口与启动

### search_course_notes.py（v1.0 主入口）

```bash
python scripts/search_course_notes.py <关键词>
python scripts/search_course_notes.py <关键词> --type herb
python scripts/search_course_notes.py <关键词> --references-dir ../references
```

**逻辑**：
1. 读 `references/text_distillation/evidence_cards.jsonl`，按 `card_type/title/summary/quote/source_ref/chunk_id` 字段做子串匹配
2. 遍历 `references/` 所有文件，按行做子串匹配
3. 输出最多 80 条匹配，超出提示 `"... N more matches"`

### query_formula.py（v2.0 朝代排序）

```bash
python scripts/query_formula.py <关键词>
python scripts/query_formula.py <关键词> --max-cards 20
```

**逻辑**：
1. 读 evidence_cards.jsonl，过滤包含关键词的卡
2. 对每张卡调用 `identify_source(card)`：
   - SOURCE_MAP 命中（key 在 source_ref / title / summary 中）
   - TYPEID_MAP 命中（从 `TypeID=N` 反查）
   - 否则返回 `("待考", source_ref, "")`
3. 按 `(DYNASTY_ORDER[dyn], dyn, book, author)` 排序
4. 输出 Markdown 表格，每朝代限 `--max-cards` 条

**内置映射**（v2.0）：
- SOURCE_MAP：53 条（东汉/金/日本江户/明/清/民国/现代）
- TYPEID_MAP：29 条
- DYNASTY_ORDER：11 个朝代

### fetch_course_evidence.py（v1.0 取证）

```bash
python scripts/fetch_course_evidence.py --card-id <card_id>
python scripts/fetch_course_evidence.py --chunk-id <chunk_id>
python scripts/fetch_course_evidence.py --card-id <id> --context-chars 8000
```

**逻辑**：
1. 读 evidence_cards.jsonl + text_sources/chunks.jsonl
2. 按 card_id 或 chunk_id 定位
3. 输出 JSON：`{chunk: {chunk_id, source_id, source_path, text...}, cards: [...]}`

### search_md.py（v1.0 markdown 全文）

```bash
python scripts/search_md.py <关键词>
python scripts/search_md.py <关键词> --limit 30
```

**注意**：硬编码 `PROJECT_ROOT = Path(r'C:\Users\hxst01\Documents\aicoding\zhongyishijia\data')`，**仅在原始 markdown 数据存在时有效**。本 skill 发布包不含 markdown 数据，需自行准备。

---

## 对外接口（脚本与 Agent 的契约）

每个脚本都遵循：

1. **命令行**：argparse + RawDescriptionHelpFormatter + epilog 示例
2. **输出**：
   - 检索类（search/query）→ stdout Markdown 表格
   - 取证类（fetch）→ stdout JSON
   - 状态/进度 → stderr
3. **错误处理**：找不到文件时打印明确路径提示并退出
4. **编码兼容**：Windows / Linux 均输出 UTF-8（query_formula.py 顶部 TextIOWrapper 修复）

---

## 关键依赖与配置

### Python 标准库
- `argparse` / `pathlib` / `json` / `re` / `sqlite3` / `io` / `sys`
- **无第三方依赖**（纯 stdlib）

### 输入文件路径（默认）

| 脚本 | 输入路径 | 是否必需 |
|------|---------|:----:|
| search_course_notes.py | `references/text_distillation/evidence_cards.jsonl` + `references/**/*.md` | 是 |
| query_formula.py | `references/text_distillation/evidence_cards.jsonl` | 是 |
| fetch_course_evidence.py | `references/text_distillation/evidence_cards.jsonl` + `references/text_sources/chunks.jsonl` | 是 |
| search_md.py | `C:\Users\hxst01\Documents\aicoding\zhongyishijia\data\markdown\` | 否（硬编码路径） |
| query_herb.py (v3.0) | `references/raw/20120413mssql.sqlite`（用 `find_sqlite_path()`） | 是 |

### 输出路径

- 默认全部输出到 stdout
- `*.tsv` 等临时文件已在 `.gitignore` 排除

---

## 数据模型

### evidence_cards.jsonl 每行结构

```json
{
  "card_id": "bb4302e01c4c1b50",
  "card_type": "herb",
  "title": "麻黄汤",
  "summary": "处方:麻黄（去节）6g 桂枝4g...;主治:外感风寒...",
  "source_ref": "《伤寒论》",
  "chunk_id": "zysjyj:122",
  "tags": ["中药", "TypeID:39"],
  "alias": null,
  "pinyin": null
}
```

**已知问题**：
- HTML 实体未转义（`&amp;#236;` 等），需在输出端 `html.unescape()`
- `source_ref` 是字符串非结构化，靠 SOURCE_MAP 模糊匹配（v2.0 命中率 17.2%）
- `card_type` 粒度太粗（herb / clinical_theory / synthesis），无法区分"单味药"与"方剂"

### v3.0 重蒸馏后字段（计划）

```json
{
  "card_id": "f7ff2891e750cff8",
  "card_type": "herb",
  "card_kind": "herb_material | formula | clinical_theory | synthesis",
  "title": "细辛",
  "dynasty": "现代",
  "book": "《中国药典》",
  "author": "",
  "prescribed_herbs": [],
  "summary": "...",
  "source_ref": "《中国药典》",
  "chunk_id": "zysjyj:444",
  "tags": ["中药", "TypeID:40"],
  "alias": null,
  "pinyin": "Xi Xin"
}
```

---

## 测试与质量

### 端到端测试（README 4/4 通过）

| Q# | 问题 | 测试命令 | 期望结果 |
|---:|------|---------|---------|
| Q1 | 桂枝人参汤治什么证？ | `python query_formula.py 桂枝人参汤` | 5+ 行朝代排序表格，含《伤寒论》《景岳全书》《四圣心源》《药征》《伤寒金匮发微》 |
| Q2 | 人参与党参区别？ | `python search_course_notes.py 党参` | 找到峻补/平补对照 |
| Q3 | 麻黄升麻汤是什么方？ | `python query_formula.py 麻黄升麻汤` | 含东汉《伤寒论·辨厥阴病脉证并治》 |
| Q4 | 理中丸和桂枝人参汤的异同？ | `python query_formula.py 桂枝人参汤` | 出现"桂枝人参汤 = 理中汤 + 解表" |

### v3.0 验证（计划）

```bash
python scripts/query_herb.py 细辛 | wc -l   # 期望 ≤200（vs search 5903）
python scripts/query_herb.py 细辛 | grep -E '^\| (东汉|梁|魏|唐|宋|元|明|清|民国|现代)' | wc -l  # ≥10 命中
python scripts/build_herb_index.py
python -c "import json; print(len(open('references/text_distillation/herb_index.jsonl',encoding='utf-8').readlines()))"  # ~18,000
```

---

## 常见问题 (FAQ)

**Q: `query_formula.py` 输出的朝代经常是"待考"？**
A: SOURCE_MAP 当前只有 53 条，命中率 17.2%。v3.0 计划扩展到 80+ 条。

**Q: Windows 终端中文乱码？**
A: query_formula.py 顶部已修：`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`。

**Q: `search_course_notes.py` 5903 条匹配噪音大？**
A: 因为单味药 + 含此药的方剂混排。v3.0 用 SQLite 反向索引 + `query_herb.py` 解决。

**Q: `search_md.py` 在本仓库报"No such file"？**
A: 它的 PROJECT_ROOT 硬编码为开发机路径。发布版不含 markdown 原始数据。

---

## 相关文件清单

- [`../README.md`](../README.md) §"标准化方剂查询（v2.0 新增）" — query_formula.py 用户文档
- [`../docs/PLAN_v3_query_herb.md`](../docs/PLAN_v3_query_herb.md) — v3.0 完整开发计划
- [`../references/text_distillation/CLAUDE.md`](../references/text_distillation/CLAUDE.md) — evidence_cards.jsonl 数据格式
- [`../references/raw/CLAUDE.md`](../references/raw/CLAUDE.md) — SQLite 数据字典（含 find_sqlite_path 模板）

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- 无代码改动

### v2.0 (2026-07-01)
- 新增 `query_formula.py`

### v1.0
- 新增 `search_course_notes.py` + `fetch_course_evidence.py` + `search_md.py`