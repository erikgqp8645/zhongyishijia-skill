[根目录](../CLAUDE.md) > **docs**

# docs — 开发文档

> **职责**：存储 v3.0 及未来版本的设计计划、架构决策记录（ADR）、开发指南。
> **状态**：v3.0 计划文档已交付。

---

## 模块职责

存放**开发类文档**（区别于 references/ 下的课程资源）：

1. **版本计划** — `PLAN_v*.md`（重大变更的设计方案）
2. **架构决策记录（ADR）** — 未来新增（TODO）
3. **API 设计** — 未来新增（TODO）

---

## 文件清单

| 文件 | 大小 | 状态 | 说明 |
|------|-----:|:----:|------|
| `PLAN_v3_query_herb.md` | ~12 KB | 计划中 | v3.0 完整开发计划（5 个工作流 + 风险 + 时间预估） |

---

## 入口与启动

`docs/` 是**设计文档目录**，无执行入口。

---

## 对外接口

### 当前文档列表

#### PLAN_v3_query_herb.md（v3.0 计划）

**5 个工作流**：

1. **抽 scripts/_source_map.py 共用模块** — 扩展 SOURCE_MAP 至 80+ 条（+25 条）
2. **重构 query_formula.py** — 改 import `_source_map`
3. **新建 scripts/query_herb.py** — 按中药查本药 + 含此药方剂（纯 SQLite，80ms）
4. **建 references/text_distillation/herb_index.jsonl 反向索引** — `build_herb_index.py` + ~18,000 条索引
5. **重蒸馏 evidence_cards.jsonl** — 加 5 个结构化字段（card_kind / dynasty / book / author / prescribed_herbs）

**时间预估**：5-6 小时

**风险**：
- 重蒸馏失败 → 备份为 `evidence_cards.jsonl.bak`
- SOURCE_MAP key 冲突 → first match，新旧不重叠
- GBK 编码丢失 → `errors='replace'` 容错

详细计划见 [./PLAN_v3_query_herb.md](./PLAN_v3_query_herb.md)。

---

## 关键依赖与配置

无运行时依赖。文档本身是 Markdown。

---

## 数据模型

无。本目录是纯文档。

---

## 测试与质量

### v3.0 验证方案

```bash
# ── 工作流 1+2：向后兼容 ──
python scripts/query_formula.py 桂枝人参汤  # 期望：5+ 行朝代排序表格

# ── 工作流 3：核心功能 ──
python scripts/query_herb.py 细辛
#   第一段"细辛本药"≥3 行
#   第二段"含细辛的方剂"≥50 行
#   总输出 ≤200 行（vs search 5903）

# ── 朝代分布验证 ──
python scripts/query_herb.py 细辛 | grep -E '^\| (东汉|梁|魏|唐|宋|元|明|清|民国|现代)' | wc -l
# 期望：≥10 个不同时代的命中行

# ── 工作流 4：索引构建 ──
python scripts/build_herb_index.py
python -c "import json; print(len(open('references/text_distillation/herb_index.jsonl',encoding='utf-8').readlines()))"
# 期望：~18,000 条

# ── 工作流 5：结构化字段 ──
python -c "
import json
with open('references/text_distillation/evidence_cards.jsonl', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 100: break
        card = json.loads(line)
        assert all(k in card for k in ('card_kind','dynasty','book','author'))
print('✓ All 100 sampled cards have new fields')
"
```

---

## 常见问题 (FAQ)

**Q: 计划文档和 README 有什么区别？**
A: README 面向**最终用户**（人类 + Agent），介绍用法；plan 面向**开发者**，介绍设计与变更。

**Q: v3.0 计划什么时间开始？**
A: 当前未排期。用户提交 issue 后启动。

**Q: 计划文档会改吗？**
A: 是。每次迭代更新本文档顶部的"状态"字段，并 append 到变更记录。

---

## 相关文件清单

- [`./PLAN_v3_query_herb.md`](./PLAN_v3_query_herb.md) — v3.0 完整计划
- [`../README.md`](../README.md) — 用户级文档
- [`../SKILL.md`](../SKILL.md) — Agent 入口描述
- [`../scripts/CLAUDE.md`](../scripts/CLAUDE.md) — 脚本集（v3.0 主要变更对象）
- [`../references/text_distillation/CLAUDE.md`](../references/text_distillation/CLAUDE.md) — 蒸馏数据（v3.0 重蒸馏目标）

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- **不覆盖** [./PLAN_v3_query_herb.md](./PLAN_v3_query_herb.md)

### v3.0 (计划中)
- 5 个工作流待实施（见 PLAN_v3_query_herb.md）