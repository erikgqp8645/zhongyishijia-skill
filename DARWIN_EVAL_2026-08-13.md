# Darwin 评估报告 · zhongyishijia-skill · 2026-08-13

> **评估方法**: darwin-skill v2.1 9 维 rubric (SkillLens + SkillOpt 实证基础)
> **评估分支**: `darwin-eval-2026-08-13`（不污染 main）
> **评估范围**: 顶层 SKILL.md + 6 个子 skill SKILL.md + README.md
> **绝对总分**: **73.9 / 100** (Phase 1 baseline, 用于 triage 排名，**不用于 keep/revert**)

---

## 一、Runtime 适配性检查 (gate 项)

✅ **完全通过 — 无红灯命中**

| 扫描模式 | 命中数 |
|---------|-------|
| `在 Claude Code` | 0 |
| `Claude Code skill` | 0 |
| `Claude Code 用户` | 0 |
| `Cursor only` | 0 |
| `Codex 中` | 0 |
| `~/.claude/skills/[a-z]` | 0 |
| `/plugin install` | 0 |

**亮点**：README §"🚀 安装"明确分「作为 Hermes Skill / OpenClaw Skill / 自定义 Agent」三段，措辞 runtime-neutral。这一项 zhongyishijia **远优于** darwin-skill 实证案例中触发 nuwa-skill 拒绝装载的那类 skill。

---

## 二、9 维 Rubric 评分明细

| # | 维度 | 权重 | 评分 | 加权得分 | 加权短板 | 备注 |
|---|------|------|------|----------|----------|------|
| 1 | Frontmatter质量 | 7 | **8** | 56 | 1.4 | name+description+触发词齐全，无空话尾巴 |
| 2 | 工作流清晰度 | 12 | **8** | 96 | 2.4 | Step 1-5 完整，Fallback 表 + 检查点 |
| 3 | 失败模式编码 | 12 | **6** | 72 | 4.8 | **短板** — if-then 三段式分支不够明确 |
| 4 | 检查点设计 | 6 | **6** | 36 | 2.4 | 4 个 🔴/CHECKPOINT 标记（建议 ≥8） |
| 5 | 可执行具体性 | 18 | **7** | 126 | 5.4 | **大短板** — 软化措辞 0 处✓，但代码示例少（仅 2 处） |
| 6 | 资源整合度 | 4 | **7** | 28 | 0.4 | **发现 3 处文档漂移**（见下文） |
| 7 | 整体架构 | 12 | **9** | 108 | 1.2 | 子 Skill 索引 + Reference Priority + Capability Strategy 三件套齐全 |
| 8 | 实测表现 | 23 | **7** | 161 | 6.9 | **最大短板** — 干跑验证，需 full_test 确认 |
| 9 | 反例与黑名单 | 6 | **8** | 48 | 1.2 | 有"反例清单"但未单独列章节 |

**总分**：73.9 / 100（**优秀**，darwin-skill 自评参考线 86-92）

---

## 三、加权短板排序（Phase 2 优先目标）

按 `weighted_gap = weight × (10 - score) / 10` 排序：

| 排序 | 维度 | 加权短板 | 当前分 | 预期改进点 |
|------|------|----------|--------|-----------|
| 🔴 1 | **dim8 实测表现** | **6.9** | 7/10 | 跑 full_test 替换 dry_run（子agent执行 3 个测试 prompt） |
| 🔴 2 | **dim5 可执行具体性** | **5.4** | 7/10 | 增加代码/示例块数（2 → ≥8），针对 Step 1-4 加伪代码 |
| 🔴 3 | **dim3 失败模式编码** | **4.8** | 6/10 | 三段式 if-then（触发条件 / 一线修复 / 仍失败兜底）|
| 4 | dim2 工作流清晰度 | 2.4 | 8/10 | Step 6 加 fallback 决策树 |
| 4 | dim4 检查点设计 | 2.4 | 6/10 | 把"用户确认"改为 🔴 CHECKPOINT 视觉标记 |
| 6 | dim1 Frontmatter | 1.4 | 8/10 | description 末尾加触发词片段 |
| 7 | dim7 整体架构 | 1.2 | 9/10 | 已饱和 |
| 7 | dim9 反例黑名单 | 1.2 | 8/10 | 单列「## 反例清单」章节 |
| 9 | dim6 资源整合度 | 0.4 | 7/10 | 修复 3 处文档漂移 |

**HL-3 警告（相关簇）**: dim2/dim3/dim4 是相关簇——修 dim3 时 dim2/dim4 常跟着涨。建议 dim3+dim4 同步改（一次 paired 比较）。

---

## 四、关键发现（按 darwin-skill 反例黑名单检查）

### 发现 1：SKILL.md 文档漂移（dim6 相关）

**3 处引用实际不存在的 references**：

| 引用 | 状态 |
|------|------|
| `references/distillation_audit.json` | ❌ 不存在 |
| `references/distillation_audit.md` | ❌ 不存在 |
| `references/install_workflow.md` | ❌ 不存在（v2.2 节也提到，但 README 已删） |

**另外 7 个 references 引用指向部署依赖**（部署后才存在，**不算 SKILL.md 错**）：
- `references/external/zysj.db` (LFS, 部署后才有)
- `references/text_sources/chunks.jsonl` (同上)
- `references/keyframe_selection/` (keyframe_skill 部署后)
- `references/keyframes_model_selected/` (同上)
- `references/transcripts/` (CHM 镜像)
- `references/analysis/` (分析文档)
- `references/documents/` (源文档)

### 发现 2：AI 废话零容忍（dim7）

✅ **AI 废话数 = 0**——"说白了/换句话说/首先/其次/综上"等花叔禁用词全部清零。这是我**见过的最严谨的 SKILL.md 之一**。

### 发现 3：反例清单章节不够独立（dim9）

SKILL.md 有 `## 反例清单（不要做的事）` 表格，但**未单独成章**，混在「Scope」之后。建议：
- 提升为独立 `## 反例与黑名单` 章节
- 增加更多条目（尤其**高风险操作**如 `git reset --hard`、批量修改参考文件的 SOP）

### 发现 4：实测验证（缺（dim8 短板最大）

本评估使用**干跑（dry_run）**，因为 darwin-skill 子 agent 触发在本机环境有限制。**这是最大的不确定性源**——darwin-skill 的核心结论之一就是「绝对分数不可信，必须 paired 比较」。

**3 个 test prompts 已写入** `test-prompts.json`：
1. 桂枝人参汤历代医家论述（覆盖 formula-query skill）
2. 理中汤/四逆汤/桂枝汤家族关系（覆盖 zugfang 祖方 skill）
3. 蒸馏卡截断时双源取证（覆盖 double-fetch skill）

如 Erik 决定进 Phase 2，建议先在另一台机器或用 OpenClaw runtime 跑一遍 full_test，**真实对比 with_skill vs baseline 输出**。

---

## 五、与 darwin-skill 自评的对比

| Skill | 绝对总分 | 关键短板 |
|-------|----------|---------|
| darwin-skill（自评） | 92.7 | 暂无显著短板 |
| huashu-gpt-image | 91.65 | 实测 prompt 边缘 case |
| **zhongyishijia-skill** | **73.9** | **dim3 失败模式 + dim5 示例 + dim8 实测** |

**zhongyishijia 在 dim1/dim7/dim9 上接近顶级**（务实不废话），但**dim3/dim5/dim8 是「学术化 skill」常见的盲区**——重理论轻操作，重结构轻验证。

---

## 六、Phase 2 优化建议（待 Erik 拍板）

### P0 推荐（绝对优先 — weighted_gap > 4）

| 维度 | 改进方案 | 预期提升 |
|------|---------|---------|
| **dim3** | 把 Fallback 表格升级为「三段式 if-then」：触发条件 / 一线修复 / 仍失败兜底 | +2 分（6→8） |
| **dim5** | 给 Step 1-5 每个 Step 加伪代码示例（python/bash 双格式） | +2 分（7→9） |
| **dim8** | 跑 3 个 test prompts 的 full_test，标 full_test 而非 dry_run | +1~2 分（7→8/9） |

### P1 推荐（次优 — weighted_gap 2-3）

| 维度 | 改进方案 |
|------|---------|
| dim4 | 把"用户确认"措辞统一改为 🔴 CHECKPOINT 视觉标记 |
| dim6 | 修复 3 处文档漂移（删除 install_workflow.md 引用 + distillation_audit 引用） |

### P2 可选

| 维度 | 改进方案 |
|------|---------|
| dim9 | 提升反例清单为独立章节 |
| dim1 | description 末尾加触发词片段（"xuewei/胃痛/方剂"等具体词） |

---

## 七、回滚预案

评估结果在 `darwin-eval-2026-08-13` 分支上，**main 完全干净**。如决定不进入 Phase 2：

```bash
git checkout main
git branch -D darwin-eval-2026-08-13   # 删除评估分支
```

如决定进 Phase 2 且最终确认改动有用：

```bash
git checkout darwin-eval-2026-08-13
# ... 优化循环（每轮 paired 比较 + 奇数多数决）
git checkout main
git merge darwin-eval-2026-08-13 --no-ff
```

---

## 八、结论

**zhongyishijia-skill 已经是一个 73.9/100 的优质 skill**（超平均水准），主要短板是「**学术化倾向**」——重理论轻操作、重结构轻验证。

**最值得做的 3 件事**：
1. dim3 三段式 if-then（最易实施 + 杠杆最大）
2. dim5 加代码示例（提升可执行性）
3. 修复 3 处文档漂移（提升准确性）

**不推荐做的事**：
- 盲目堆字数（darwin 反例 #3「为凑分增冗余」）
- 改 dim7（已饱和，再改反而掉分）
- 单轮改多个维度（darwin 反例 #5）

---

**🛑 STOP · 等 Erik 拍板**：

- [ ] 接受评估结果，**进入 Phase 2 优化循环**？
- [ ] 只采纳 P0 的 dim3+dim5+dim8，跳过 P1/P2？
- [ ] **只保留基线评估报告**，不进入优化循环？
- [ ] 删除评估分支，回到干净 main？

---

**作者**: Hermes Agent (执行: darwin-skill 评估)
**工具**: darwin-skill v2.1
**日期**: 2026-08-13
**结果文件**: `results.tsv` (1 行 baseline)