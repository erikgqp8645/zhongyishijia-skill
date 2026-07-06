[根目录](../../../CLAUDE.md) > [references](../../CLAUDE.md) > **okf**

# references/okf — OKF 渐进式阅读框架

> **职责**：以 Markdown 形式提供人类可读的概念图谱与学习路径。
> **状态**：已生成（lineage-skill v0.1 输出 4 个概念，0 证据块）。

---

## 模块职责

OKF（Open Knowledge Framework）是一个**渐进式阅读**的 Markdown 知识包，目的是：

1. **人类可读** — 不是 JSON / SQLite，而是带超链接的 Markdown
2. **跨 Agent 交换** — 任何 LLM 都能直接消费
3. **渐进式阅读** — 从 `index.md` 入口，按 capability section → 概念文件 → 引用证据

---

## 文件清单

| 文件 | 大小（约） | 含义 |
|------|-----------:|------|
| `index.md` | 0.6 KB | OKF Bundle 入口，列出 Boundaries / Study Paths |
| `boundaries/index.md` | stub | 边界索引 |
| `boundaries/001-boundary-1.md` | stub | 边界 1（占位） |
| `study-paths/index.md` | stub | 学习路径索引 |
| `study-paths/001-入门路径.md` | stub | 中医入门：基础理论→诊断→中药→方剂 |
| `study-paths/002-临床路径.md` | stub | 中医内科→伤寒→金匮→温病 |
| `study-paths/003-中药路径.md` | stub | 中药字典→本草纲目→本草备要 |
| `log.md` | stub | OKF 生成日志 |

---

## 入口与启动

### 阅读顺序（来自 okf/index.md）

```
1. Start here (index.md)
2. Open the relevant capability section index
3. Read individual concept files
4. Follow `# Citations` links to evidence chunks when exact source wording matters
```

### Agent 调用入口

```
references/okf/index.md  ← SKILL.md Reference Priority 第 1 条
```

---

## 对外接口

### Markdown 概念文件结构（标准）

```markdown
# 概念名

[概念正文...]

# Citations

- [相关 lesson 1](../course_package.json#lesson-xxx)
- [相关 card](../text_distillation/evidence_cards.jsonl#card-xxx)
```

### 概念索引（来自 okf/index.md）

- **Boundaries**（1 个）：1 个概念文件
- **Study Paths**（3 个）：3 个概念文件（入门/临床/中药路径）

---

## 关键依赖与配置

- **依赖**：lineage-skill 框架（用于重新生成 OKF）
- **可选依赖**：`LINEAGE_TEXT_API_KEY`（用于 LLM 抽取名句与概念）

---

## 数据模型

OKF 是纯 Markdown，不依赖数据库或 JSON。每篇概念文件是 1 个 Markdown 文件，链接用相对路径。

---

## 测试与质量

### 生成质量检查

- 概念数：4 个（1 boundary + 3 study-paths）
- 证据块：0（lineage-skill manifest 中标注 `okf/: generated 4 concepts, 0 evidence chunks`）
- 引用完整性：每个概念文件应有 `# Citations` 段

### 已知 stub 状态

`okf/log.md` / 各概念文件多为 stub 状态（lineage-skill 框架默认占位），需后续用 LLM 重蒸馏补全。

---

## 常见问题 (FAQ)

**Q: OKF 和 references/ 下其他索引有什么区别？**
A: OKF 是**人类可读 + Agent 可读**的双消费方知识图谱；lesson_index.json / evidence_map.json 是机器索引。

**Q: 怎么重新生成 OKF？**
A: 跑 `lineage-skill` 的 `build_course_skill.py` 并设置 `LINEAGE_TEXT_API_KEY` 让 LLM 抽取概念与引用。

---

## 相关文件清单

- [`../../SKILL.md`](../../SKILL.md) §"Reference Priority" — OKF index.md 是第 1 优先
- [`../../../lineage_manifest.json`](../../../lineage_manifest.json) — `okf/: generated 4 concepts, 0 evidence chunks`

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- 无 OKF 文件改动

### v1.0 (2026-07-01)
- lineage-skill 生成 OKF Bundle（4 个概念，0 证据块）