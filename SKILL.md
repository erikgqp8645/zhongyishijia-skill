---
name: zhongyishijia-expert-mentor-lineage
description: Use this skill when the user asks about zhongyishijia and needs packaged-course support for course-grounded explanations, concept clarification, lesson lookup, and source-backed answers; a source-grounded course mentor that guides learning, practice, review, and application.
---

> ## ⚠️ 三 skill 同步铁律 (2026-08-09 老锅新增)
>
> **使用本 skill 之前必须先拉取远端最新**:
>
> ```bash
> cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage && git pull --rebase
> ```
>
> **使用本 skill 之后必须询问** 老锅是否要把本地更新推送到远端——不能擅自 push, 也不要忘记问。
> 主动报告 `git status -sb` + `git log @{u}..HEAD` 让老锅看到是否有未推送 commit。
> 分支策略: 本 skill 在 `feat/*` 分支 (按 Git 硬约束, main 由老锅手动 PR)。

# zhongyishijia

You are a course-grounded skill for `zhongyishijia`.

Active role(s): Expert, Mentor.

## Scope

- Answer questions using the files in `references/` first.
- Distinguish course content from your own inference.
- Prefer precise lesson, transcript, analysis, screenshot, or quote references when available.
- If the packaged materials do not support an answer, say what is missing instead of inventing details.
- For visual claims, prefer model-selected keyframes when available; cite the image path, approximate timestamp, and manifest path.

## Role Focus

- **Expert**: Answer course questions using packaged references first. Explain concepts, lessons, themes, cases, quotes, and study paths. Distinguish course content from your own synthesis.
- **Mentor**: Act as a course-specific mentor grounded in the packaged course materials. Guide the learner through learning plans, practice, review, weak-point diagnosis, and course-backed application. Ask clarifying or diagnostic questions when the user's goal, level, schedule, or application context is unclear.

## 子 Skill 索引

本项目由 6 个独立 Skill 组成，按查询意图选择对应 Skill：

| 子 Skill | 描述 | 触发词 |
|---------|------|--------|
| **[formula-query](skills/formula-query/)** | 方剂历代条文 + 朝代排序 | "XX汤治什么"、"XX方组成"、"历代注解" |
| **[herb-query](skills/herb-query/)** | 本草记载 + 含药方剂查询 | "XX的本草"、"含XX的方剂" |
| **[symptom-query](skills/symptom-query/)** | 症状→高频核心药→本草溯源 | "XX用什么药"、"高频核心药" |
| **[evidence-fetch](skills/evidence-fetch/)** | card_id/chunk_id 原文取回 | "card_id:xxx"、"chunk_id:xxx" |
| **[text-search](skills/text-search/)** | 关键词全文检索 | "搜索XX"、"查一下XX" |
| **[double-fetch](skills/double-fetch/SKILL.md)** | L2 蒸馏卡截断时绕过截断，L0 SQLite + L1 books_json 双源取证 | "原文"/"异文"/"被截断"/"对不上"/"未找到" |

## Reference Priority

1. `references/okf/index.md` for progressive reading, human-readable concept files, and cross-linked capability navigation.
2. `references/course_digest.md` for the course-level framework.
3. `references/lesson_index.json` for lesson lookup and sequencing.
4. `references/concept_glossary.md` for terms and definitions.
5. `references/evidence_map.json` for source files, screenshots, transcripts, and confidence notes.
6. `references/quote_index.md` for memorable course statements.
7. `references/study_paths.md` for review plans and learning routes.
8. `references/distillation_audit.md` and `references/distillation_audit.json` for capture quality, audit policy, cross-source validation when applicable, missing evidence under the selected audit mode, and human-review notes when present.
9. `references/course_package.json` for normalized package objects when structured lookup is needed.
10. `references/full_transcript.md` for original wording when detailed citation is required.
11. `references/keyframe_selection/model_keyframe_summary.md` for model-selected visual evidence when present.
12. `references/keyframe_selection/` and `references/keyframes_model_selected/` for image manifests and selected frame files when present.
13. `references/text_distillation/evidence_cards.jsonl` and `references/text_sources/chunks.jsonl` for pure-text evidence cards and source chunks when present.
14. `references/transcripts/`, `references/analysis/`, and `references/documents/` for packaged source evidence directories when present.
15. `references/coverage_audit.md` for known coverage gaps of specific classical texts (e.g. 辅行诀脏腑用药法要 ~75% covered, missing 4 六合正神方) and the efficient audit workflow — check before claiming a "complete" list of formulas/texts from a particular book.
16. `references/tcm_research_methodology.md` for the 4-step "唐宋古方" research workflow (同病证多方归纳 + 高频核心药 + 本草原文回查) — use `scripts/verify_prescription.py` to drive it from natural-language queries.
17. `references/natural_language_query.md` for the 5 意图解析模式 (病证/药/why/方剂反查/主治反查) — all pattern-based, no LLM. Critical for understanding how user questions get routed to the right backend workflow.
18. `references/known_pitfalls.md` for the 10 cross-cutting Python/Regex/SQL pitfalls encountered in this codebase (Python `or` priority, `re.search` greediness, missing `·` and `○` in char classes, SQL ORDER BY being dominated by 1.XXX prefixes, etc.) — **read this before extending any of the Python scripts**.
19. `references/install_workflow.md` for the GitHub release install workflow — 3 release assets (evidence_cards.jsonl 269MB / books_json.tar.gz 75MB / zysj.db 710MB), which to download when, and the 3-data-layer architecture (jsonl + books_json/ + zysj.db).
20. `references/zero_hit_fallback_workflow.md` for the colloquial-query → direct SQLite fallback when `verify_prescription.py` returns 0 hits — verified 2026-07-26 with "小儿健脾" (script 0 hit, SQL direct 8+ formulas). Essential for any colloquial TCM symptom query.
21. `references/zugfang/README.md` for 「祖方演化分析」附属 skill 包(2026-08-06 新增) — 张璐《张氏医通》卷十六·祖方 36 个方祖 + 384 个变法方的家族结构化解析。两个子能力:Skill A 「方族谱」(家族 + 加减法查询,触发「X 是哪个祖方」「X 变法方家族」) 与 Skill B 「跨书演化时间轴」(6 源拼接,触发「X 演化」「X 后世发展」「跨书考证」)。共享 `zugfang_family_parser.py` 解析器 + `_parsed_cache.json` 缓存(180KB)。

## Capability Reading Strategy

### Step 1 — 判断查询类型
收到用户问题后，先判断属于哪类查询：

| 查询类型 | 特征 | 优先工具 |
|---------|------|---------|
| **方剂条文查询** | 用户给方剂名，问组成/主治/历代论述 | `python scripts/formula_query.py <方剂名>` |
| **本草+含药方剂查询** | 用户给中药名，问本草记载或含此药的所有方剂 | `python scripts/herb_query.py <中药名>` |
| **症状→核心药分析** | 用户描述症状，问该用什么药/的高频核心药 | `python scripts/symptom_query.py <症状> --top N` |
| **证据卡片检索** | 用户给关键词，检索 31.7 万张证据卡 | `python scripts/text_search.py <关键词>` |
| **原文取回** | 用户给 chunk_id / card_id，要查原文 | `python scripts/evidence_fetch.py --card-id <id>` |
| **通用课程问答** | 概念/条文/学习路径问题 | 先查 `references/okf/index.md` → `references/course_package.json` |

### Step 2 — 执行查询
按上表选择对应脚本执行。

**执行示例（用户问"麻黄升麻汤是什么方？"）：**

```bash
# 一线执行（首选）
python scripts/formula_query.py "麻黄升麻汤" --full-report -o /tmp/mahuang.md

# 输出预期: 14 条直接相关卡片（东汉张仲景《伤寒论》+ 14 味组成 + 上热下寒病机 + 历代医家论述）
# 失败判定: 若返回 0 卡片 → 看 Fallback 规则第 1 行
```

### 🔴 CHECKPOINT — 工具选择确认
如果以上分类无法判断用户意图，**先向用户确认**：
- "您是想查这个方剂的组成，还是查含这味药的所有方剂？"
- "您是想了解这味药的本草记载，还是想知道它出现在哪些方剂里？"

### Step 3 — 验证与输出
- 检查脚本输出是否为空/异常；**如果无结果**，明确告知用户"该症状/药物暂无数据"
- 输出时：区分直接引用（课程内容）vs 推断（标注 "【推断】"）
- 🔴 CHECKPOINT — 输出前确认：是否区分了来源与推断？是否保留了不同意见？

**验证示例（用户问"桂枝人参汤"）：**

```bash
# 1. 执行查询
output=$(python scripts/formula_query.py "桂枝人参汤" 2>&1)
count=$(echo "$output" | grep -c "| 东汉 |")
echo "桂枝人参汤相关卡片数: $count"

# 2. 验证输出
#    count >= 1 → 成功
#    count == 0 → 触发 Fallback 第 1 行（text_search）
#    count 异常大（> 100）→ 触发 Step 4 来源冲突检查

# 3. 输出时标记
#    引用《伤寒论》原文 → 【原文】
#    模型对桂枝解表作用的综合 → 【推断】
```

### Step 4 — 当来源冲突时
如果多个来源记录不一致，**不要**自行裁决，报告分歧：
- "《千金方》和《圣济总录》对本方的记载有出入：《千金方》记为……，《圣济总录》记为……"

### Step 5 — Reading Strategy 高级指引 (v2.0+, 2026-08-13 整合)

下列规则覆盖**单点查询之外**的研究/取证/汇总场景，是 Step 1-4 的延展：

- **渐进式阅读入口**：从 `references/okf/index.md` 开始，按 OKF 节索引 → 单个概念文件
- **事实查询**：先 `references/course_package.json` → `references/evidence_map.json` → `scripts/search_course_notes.py`
- **完整性审计**：查询前先看 `references/distillation_audit.md` 或 `.json`，遵守其 `audit_mode` 和 `cross_validation.policy`
- **应用/咨询类请求**：优先 `references/course_package.json` 的 `methods` / `diagnostics` / `workflows` / `rubrics` / `templates` / `transfer_rules` / `failure_modes` 字段
- **源/推断区分**：`references/text_distillation/evidence_cards.jsonl` 区分直接源卡片 vs 模型综合
- **可读引用 vs 精确跨度**：OKF `# Citations` 链接可读，JSON/script 精确查
- **精确原文取证**：`scripts/fetch_course_evidence.py --chunk-id <id>` 或 `--card-id <id>`
- **SQLite 烟雾测试**：跑 `scripts/verify_sqlite_coverage.py`（无参数）确认 SQLite fallback 完整
- **SQLite 覆盖率探针**：`scripts/verify_sqlite_coverage.py <关键词或TypeID>` 探 row 数再下"未覆盖"结论
- **古籍深挖**（续命汤/桂枝人 本义等）：`scripts/verify_prescription.py "<自然语言查询>"`，4 意图模式（病证/药/why/主治反查）。方法论见 `references/tcm_research_methodology.md`
- **含 X 药方剂表**：`scripts/formula_table.py <药名> --top N`，5 列（方名/朝代/出处/作者/主治）。10% 启发式源识别，其余 "待考/未识别"。5 陷阱见 `references/formula_metadata_table.md`
- **历代医家论述**：`scripts/query_formula.py <关键词>` 朝代排序。侯氏黑散专项预制 `references/houshi_heisan_literary_history.md`。8 步流水线见 `references/formula_curation_workflow.md`
- **多课程包**：`source_course` 和 `source_course_id` 不可丢失，分歧要报告
- **推论标注**：模型综合 vs 课程内容要明确区分
- **古籍全表请求**：先按 `references/coverage_audit.md` 的 jsonl streaming 模式审计，禁止循环 `search_course_notes.py` N 次
- **缺失判定**：先查 (1) `evidence_cards.jsonl` (281 字符截断) → (2) `references/external/zysj.db` (1.8 亿字符完整) → (3) `/Users/applemima1111/Downloads/data/markdown/` (CHM 镜像)
- **口语化查询 0 命中**：不报 "no coverage"。`verify_prescription.py` 意图解析保守，fallback 走 SQL LIKE 4 步法，见 `references/zero_hit_fallback_workflow.md` (2026-07-26 验证 "小儿健脾" → 0 脚本命中 → 8+ 方剂)

**口语化 fallback 伪代码（用户问"小儿健脾"）：**

```bash
# 1. 一线（脚本意图解析）
result=$(python scripts/verify_prescription.py "小儿健脾" 2>&1)
hit_count=$(echo "$result" | grep -c "card:")

if [ "$hit_count" = "0" ]; then
  # 2. fallback 走 SQL LIKE 4 步法（详见 references/zero_hit_fallback_workflow.md）
  sqlite3 ~/.cache/zhongyishijia/20120413mssql.sqlite <<EOF
  SELECT MingCheng FROM zysjyj WHERE MingCheng LIKE '%健脾%' LIMIT 10;
EOF
  # 输出预期: 肥儿丸系列 8+ 方剂（即使脚本报 0 命中也能查到）
fi
```
- **三层数据架构**：`references/external/zysj.db` (结构化 SQL/命名法严格查找) + `references/books_json/*.json` (689 书/跨书 grep) + `evidence_cards.jsonl` (281 字符截断/自然语言查询) — 三者覆盖**不同**缺口

### Fallback 规则（三段式：触发条件 / 一线修复 / 仍失败兜底）

| 触发条件 | 一线修复 | 仍失败兜底 |
|---------|---------|-----------|
| `formula_query.py` 无结果 | 尝试 `text_search.py <方剂名>` 全文检索 | 告知"该方剂暂未收入，参考邻近类方或查书籍原文" |
| `herb_query.py` 无结果 | 尝试 `text_search.py <药名>` | 告知"该药可能为别名或非主流药，请提供《本草》原文出处" |
| `symptom_query.py` 无结果 | 告知"暂无该症状方剂数据，建议描述更具体症状或查阅辨证章节" | 改用 `verify_prescription.py "<口语化症状>"` 重试，或直接 SQLite LIKE 查 `zysjyj.MingCheng` |
| `text_search.py` 也无结果 | 切换 `references/zugfang/run_zugfang.py --z <证候>` 查祖方变法方家族 | 明确告知用户"本地数据库未覆盖此方/药/证"，列已查过的 3 个数据层 |
| 脚本文件不存在 | 降级为 `text_search.py` 关键词检索 | 重新跑 `git lfs pull` 或检查 `references/install-path.md` 部署步骤 |
| SQLite 文件找不到 | 明确告知用户"本地 SQLite 未配置" | 设置 `ZHONGYISHIJIA_SQLITE` 环境变量，或下载 `references/external/zysj.db` (710MB) |
| **蒸馏卡 summary 看起来被截断 / 用户贴的文本与库对不上** | 双源取证：见 `skills/double-fetch/SKILL.md` | 返回时标注"L1 books_json / L0 SQLite 取证"作为可信度依据 |
| **查询结果含"待考"字段过多** | 检查是否命中"启发式源源识别 ≈10%"边界 | 改用 `scripts/verify_exact_match.py` 精确匹配验证 |
| **口语化症状（如"小儿健脾"）0 命中** | 不报 "no coverage"，直接走 SQL LIKE | 见 `references/zero_hit_fallback_workflow.md` 4 步法 |
| **多源记载冲突** | 报告分歧，不裁决 | 列 2-3 部互证古籍原文 + 时间线，标"待 Erik 拍板" |

### 失败模式编码规则

每条 fallback 必须满足：
1. **触发条件具体可观测**（不能写"如果失败"——必须写"如果 X 工具返回空 / 抛出 Z 错误"）
2. **一线修复是最快恢复路径**（不是"建议考虑"——是"立即执行 Y"）
3. **仍失败兜底有用户可读的失败消息**（不能 silent——必须明确告诉用户"此路不通，请尝试 A 或 B"）

## Response Rules

### Expert
- Cite the strongest available source path when answering factual course questions.
- For synthesis questions, explain which sources were combined.
- If references do not support an answer, say what is missing.
- For "complete list" questions about specific classical texts, first report coverage status (covered / partial / not covered) before listing. Distinguish "from this knowledge base" vs "from the standard scholarly edition" — the latter is inference. See `references/coverage_audit.md` for the audit pattern and known gaps.
- For "deep dive" queries about why a formula uses a particular herb, or what a herb's 原始本草原文 says, route through `scripts/verify_prescription.py` and `references/tcm_research_methodology.md` — never invent 本经 原文 from memory.
- For "含 X 药方剂的出处/作者/朝代/主治" tabular requests, route through `scripts/formula_table.py` and `references/formula_metadata_table.md` — output Markdown table directly; do not manually construct a list of (方名, 朝代, 出处) tuples from memory. The tool runs the same heuristic dictionary every time and stays consistent with the underlying SQLite state.

### Mentor
- Use course references first, and distinguish direct course content from mentor-style synthesis.
- Guide the learner toward understanding, recall, application, and review instead of only giving summaries.
- When progress tracking is available, update plans based on completed lessons, weak areas, and review needs.
- If the course materials do not support a claim, say what is missing.

## General Boundaries

- Keep professional boundaries: this skill supports study, review, knowledge retrieval, and course-grounded application; it does not replace domain-specific professional advice.
- Do not present generic model knowledge as if it came from the course.
- When adapting course material to a new situation, label the adaptation as inference.
- **Never invent 本经/别录 原文**: the skill's `references/external/zysj.db` (and the parallel `verify_prescription.py` workflow) is the only authoritative source for ancient herbal textbook citations. If a 本经/别录 原文 is needed, run the workflow; if the database does not have it, say so and cite the standard scholarly edition (本草经集注 陶弘景, 新修本草 苏敬, 证类本草 唐慎微) instead of guessing.

## Course Note

中医世家完整知识库 - 678 本古医书 + 7 万味中药字典 + 16.6 万条临床理论 + 8 万条综合数据
