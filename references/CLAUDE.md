[根目录](../../CLAUDE.md) > **references**

# references — 课程资源总目录

> **职责**：存储课程材料、索引、原始数据与蒸馏卡的根目录。
> **状态**：v1.0 已交付；v3.0 计划新增 herb_index.jsonl。

---

## 模块职责

为 Agent 提供课程资源：

1. **课程级元数据** — `course_digest.md` / `course_package.json`
2. **课程路径** — `lesson_index.json` / `study_paths.md`
3. **概念词典** — `concept_glossary.md`
4. **证据映射** — `evidence_map.json`（1232 条 lesson 来源）
5. **金句索引** — `quote_index.md`（stubbed，待补）
6. **导师剧本** — `mentor_playbook.md` / `mentor_sessions.md` / `learner_progress.json`（stubbed）
7. **OKF 阅读框架** — `okf/` 子目录
8. **蒸馏数据** — `text_distillation/evidence_cards.jsonl`（232MB LFS）
9. **原始数据** — `raw/20120413mssql.sqlite`（660MB，**不入 git**）

---

## 文件清单

| 文件/目录 | 类型 | 大小 | 说明 | git-lfs / gitignore |
|----------|------|-----:|------|:----:|
| `course_digest.md` | 文档 | 3KB | 课程摘要（数据来源、规模、蒸馏方法） | git |
| `course_package.json` | 元数据 | KB 级 | 课程包规范化对象（schema_version + lessons） | git |
| `concept_glossary.md` | 词典 | KB 级 | 8 个核心概念（中医基础理论/中药学/方剂学/诊断学/内科学/针灸学/伤寒/金匮） | git |
| `evidence_map.json` | 索引 | KB 级 | 1232 条 lesson 的来源路径（按类别） | git |
| `quote_index.md` | 索引 | 1KB | 金句索引（stubbed，待补） | git |
| `study_paths.md` | 文档 | 2KB | 4 条学习路径（入门/经典/临床/中药专攻） | git |
| `lesson_index.json` | 索引 | KB 级 | 1232 条 lesson 元数据 | git |
| `mentor_playbook.md` | 文档 | stub | 导师剧本（lineage-skill 生成） | git |
| `mentor_sessions.md` | 文档 | stub | 导师会话 | git |
| `learner_progress.json` | 数据 | stub | 学习进度 | git |
| `full_transcript.md` | 文档 | stub | 源文件索引 | git |
| `okf/` | 子模块 | — | 渐进式阅读框架 | git |
| `text_distillation/` | 子模块 | 232MB | 31.7 万张 evidence_cards.jsonl | **LFS** |
| `books_json/` | 子模块 | 207MB | **689 本古籍 JSON**（每本书一个文件，按 BM1/章节/条目结构化） | **LFS** |
| `raw/` | 子模块 | 660MB | 原始 SQLite（**不入 git**） | **gitignore** |

---

## 入口与启动

`references/` 是**数据目录**，无执行入口。Agent 通过根目录的 `SKILL.md`（Reference Priority 章节）按顺序读取：

1. `references/okf/index.md`
2. `references/course_digest.md`
3. `references/lesson_index.json`
4. `references/concept_glossary.md`
5. `references/evidence_map.json`
6. `references/quote_index.md`
7. `references/study_paths.md`
8. `references/text_distillation/evidence_cards.jsonl`（核心）
9. `references/raw/20120413mssql.sqlite`（可选，需本地）

---

## 对外接口

### Agent 检索协议

```python
# 关键词检索（默认入口）
python scripts/search_course_notes.py <关键词>

# 朝代排序方剂查询
python scripts/query_formula.py <关键词>

# 取回证据原文
python scripts/fetch_course_evidence.py --card-id <card_id>

# (v3.0) 按中药查方剂
python scripts/query_herb.py <中药名>
```

---

## 关键依赖与配置

### git-lfs 跟踪

`.gitattributes`：
```
references/text_distillation/evidence_cards.jsonl filter=lfs diff=lfs merge=lfs -text
```

### gitignore 排除

`.gitignore`：
```
references/raw/*.sqlite
references/raw/*.db
references/raw/*.sqlite3
```

### 来源元数据

`lineage_manifest.json` 标注各文件状态：

| 文件 | 状态 |
|------|------|
| course_package.json | copied |
| course_digest.md | copied |
| concept_glossary.md | copied |
| quote_index.md | copied |
| study_paths.md | copied |
| lesson_index.json | copied |
| evidence_map.json | copied |
| mentor_playbook.md | stubbed |
| mentor_sessions.md | stubbed |
| learner_progress.json | stubbed |
| okf/ | generated 4 concepts, 0 evidence chunks |
| scripts/search_course_notes.py | generated |
| scripts/fetch_course_evidence.py | copied |

---

## 数据模型

### 顶层字段（按 SKILL.md Reference Priority）

1. **OKF 渐进阅读** — `okf/index.md` + 子索引 + 概念文件 + `# Citations` 链接
2. **课程元数据** — `course_package.json` 数组（lessons[] + evidence_refs[]）
3. **证据卡** — `text_distillation/evidence_cards.jsonl`（每行一张 card）
4. **原始数据** — `raw/20120413mssql.sqlite`（4 张表）

---

## 测试与质量

### 数据完整性校验

```bash
# evidence_cards.jsonl 行数应为 317,580
python -c "import json; print(sum(1 for _ in open('references/text_distillation/evidence_cards.jsonl', encoding='utf-8')))"

# lesson_index.json total_lessons 应为 1,232
python -c "import json; d=json.load(open('references/lesson_index.json')); print(d['total_lessons'])"
```

### 部署验证清单

参见 [raw/CLAUDE.md §10 验证清单](./raw/CLAUDE.md)。

---

## 常见问题 (FAQ)

**Q: `evidence_cards.jsonl` 怎么这么大？**
A: 31.7 万张卡，平均 766 字节/张 ≈ 232MB。已用 git-lfs。

**Q: 我可以删除 `quote_index.md` 吗？**
A: 它是 stubbed 状态，lineage-skill 框架默认生成。删除会导致 lineage-skill 重生成时再补回来。

**Q: 为什么同时有 `evidence_map.json` 和 `text_distillation/evidence_cards.jsonl`？**
A: evidence_map.json 是 lesson 级（1232 条），evidence_cards.jsonl 是 card 级（31.7 万张）。前者是索引，后者是数据。

---

## 相关文件清单

- [`./okf/CLAUDE.md`](./okf/CLAUDE.md) — OKF 阅读框架
- [`./text_distillation/CLAUDE.md`](./text_distillation/CLAUDE.md) — 蒸馏数据
- [`./raw/CLAUDE.md`](./raw/CLAUDE.md) — 原始 SQLite
- [`../SKILL.md`](../SKILL.md) — Reference Priority 完整列表
- [`../lineage_manifest.json`](../lineage_manifest.json) — 元数据

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- 无数据改动

### v1.0
- lineage-skill 完整包交付（lineage_manifest.generated_at = 2026-07-01）