# 中医世家知识库 Skill (zhongyishijia-skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Skill size](https://img.shields.io/badge/size-268MB-blue)](references/text_distillation/evidence_cards.jsonl)
[![Evidence cards](https://img.shields.io/badge/evidence_cards-317K-brightgreen)](references/text_distillation/evidence_cards.jsonl)
[![Skills](https://img.shields.io/badge/sub_skills-6-blueviolet)](#-子能力清单)
[![Source](https://img.shields.io/badge/source-zysj.com.cn-orange)](https://www.zysj.com.cn)

> **课程驱动的中医世家网站离线知识库**，已转化为 lineage-skill 格式，可直接安装到 Hermes / OpenClaw / Codex / Claude 等任何支持 lineage-skill 的 Agent runtime。
>
> **v3.0+ (2026-08-13 大整合)**：从单一查询工具进化为 **6 个子 skill** + 12 个新专题的完整课程生态。详见 [`CHANGELOG_2026-08-13.md`](CHANGELOG_2026-08-13.md)。

---

## ⚡ 子能力清单

本 skill 由 **6 个独立子 skill + 1 个祖方演化附属包**组成，按查询意图选择对应工具：

| 子 Skill | 触发词 | 入口 | 用途 |
|---------|--------|------|------|
| **[formula-query](skills/formula-query/)** | "XX汤治什么" / "XX方组成" / "历代注解" | `scripts/formula_query.py` | 方剂历代条文 + 朝代排序（851 行终极版，13 章节） |
| **[herb-query](skills/herb-query/)** | "XX的本草" / "含XX的方剂" | `scripts/herb_query.py` | 本草记载 + 含药方剂查询 |
| **[symptom-query](skills/symptom-query/)** | "XX用什么药" / "高频核心药" | `scripts/symptom_query.py` | 症状→高频核心药→本草溯源 |
| **[evidence-fetch](skills/evidence-fetch/)** | "card_id:xxx" / "chunk_id:xxx" | `scripts/evidence_fetch.py` | card_id/chunk_id 原文取回 |
| **[text-search](skills/text-search/)** | "搜索XX" / "查一下XX" | `scripts/text_search.py` | 关键词全文检索 |
| **[double-fetch](skills/double-fetch/)** | "原文" / "异文" / "被截断" / "对不上" | `skills/double-fetch/scripts/verify_double_fetch.py` | L2 蒸馏卡截断时双源取证（L0 SQLite + L1 books_json） |
| **祖方演化分析 (zugfang)** | "X 是哪个祖方" / "X 变法方" / "X 演化" | `references/zugfang/run_zugfang.py` | 张璐《张氏医通》36 方祖 + 384 变法方家族 |

每个子 skill 的详细使用方式见 `skills/<name>/SKILL.md`。

---

## 📖 这是什么？

将中医世家网站（zysj.com.cn）2012-2014 年的完整离线数据（678 本古医书 CHM + 两个 SQL 数据库，共 5.7GB 原始数据）**蒸馏**为：

- **31.7 万张结构化 evidence cards**（平均 766 字节/张）
- 每张卡包含方剂名 / 病证名 / 中药名 / 主治 / 处方 / 各家论述 / 出处
- 引用关系可追溯到《伤寒论》《金匮要略》《本草纲目》等具体古籍

LLM 通过 `scripts/text_search.py` 在 cards 里检索关键词 + 来源，**不会编造**，回答可验证。

---

## 📊 数据规模

| 类别 | 来源表 | 卡片数 | 代表内容 |
|---|---|---|---|
| herb（中药/方剂） | `zysjyj` | **70,350** | 麻黄汤、桂枝人参汤、人参… |
| clinical_theory（临床理论） | `zysjllsj` | **166,421** | 协热下痢、痞证表里、伤寒六经… |
| synthesis（综合医话/方论） | `zysjzhsj` | **80,809** | 历代各家注解、现代临床应用 |

**总计 317,580 张** · **268 MB** · **横跨东汉-现代 1800 多年**

---

## 🚀 安装

### 方式一：作为 Hermes Skill（推荐）

```powershell
# 1. 克隆仓库
git clone https://github.com/erikgqp8645/zhongyishijia-skill.git
cd zhongyishijia-skill

# 2. 安装 git-lfs（首次需要）
git lfs install

# 3. 拉取大文件 (268MB LFS)
git lfs pull

# 4. 复制到 hermes skill 目录
Copy-Item -Recurse . "$env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage"

# 5. 验证
python "$env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage\scripts\text_search.py" '桂枝人参汤'

# 6. 试用标准化方剂查询（13 章节完整报告）
python "$env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage\scripts\formula_query.py" '桂枝人参汤' --full-report

# 7. 试用祖方演化分析（Skill A 方族谱）
python "$env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage\references\zugfang\run_zugfang.py" '理中汤' --a
```

### 方式二：作为 OpenClaw Skill

```bash
# SKILL.md 兼容 OpenClaw 规范
cp -r . ~/.openclaw/skills/zhongyishijia-expert-mentor-lineage
```

### 方式三：自定义 Agent（任何支持 lineage-skill 的 runtime）

把 `SKILL.md` + `references/` + `scripts/` 路径告诉你的 Agent 即可：

- 把 `references/` 当作 Agent 的 lookup path
- 任何时候需要查证方剂/病证/中药时，运行 `scripts/text_search.py <关键词>`
- 需要历代医家论述汇总表时，运行 `scripts/formula_query.py <方剂名>`
- 需要查祖方/变法方家族时，运行 `references/zugfang/run_zugfang.py <方剂名>`

### 完整 SQLite 部署（可选，启用所有脚本）

```bash
# 下载 zysj.db (710MB) 以启用 symptom_query / herb_query / verify_prescription 等脚本
# 详见 references/install-path.md

# 也可在 ~/.cache/zhongyishijia/20120413mssql.sqlite 放置 660MB SQLite
# 或使用 --sqlite 参数指定路径
```

**SQLite 部署位置（3 级查找顺序，由脚本自动探测）**：

1. 环境变量 `ZHONGYISHIJIA_SQLITE`
2. `~/.cache/zhongyishijia/20120413mssql.sqlite`
3. `<project>/references/raw/20120413mssql.sqlite`

**SQLite 部署常见陷阱**：详见 `references/raw/SQLITE_PITFALLS.md`（必读）。

---

## ⚠️ JSONL-only 部署 vs 完整部署

**JSONL-only 部署**（仅 268MB LFS，无 SQLite）：
- ✅ 可用：`formula_query.py` / `text_search.py` / `zugfang/run_zugfang.py` / `skills/double-fetch/`
- ❌ 不可用（graceful degradation）：`herb_query.py` / `symptom_query.py` / `formula_table.py` / `verify_prescription.py` / `evidence_fetch.py`
- 错误信息统一提示「本地 SQLite 未配置，请检查 --sqlite 参数」

**完整 SQLite 部署**（+ 710MB zysj.db 或 660MB 原始 SQLite）：
- ✅ 全部 6 个子 skill + 12 个 scripts 都可用
- 详见 `references/install-path.md`

---

## 🧪 验证测试

4/4 测试全部通过 — hermes 用 MiniMax-M3 + zhongyishijia skill 跑的实际回答：

<details>
<summary><b>Q1: 桂枝人参汤治什么证？</b>（点击展开）</summary>

成功检索到 5 个具体 card_id（`a4a41cd8...`, `e90f3c8a...`, `f38ccd28...`等），引用 4 部互证古籍：
- 《伤寒论》原文（163 条）
- 《景岳全书·协热下痢》专论
- 《四圣心源·痞证表里》方解
- 《药征》（东洞吉益）反推印证
- 曹颖甫《伤寒金匮发微·附列门人治验》

回答涵盖：原文证候拆解 / 组成煎服法 / 方义（桂枝解表 + 理中温里）/ 与葛根芩连汤鉴别 / 临床要点 / 容易混淆方剂。
</details>

<details>
<summary><b>Q2: 人参与党参区别？</b></summary>

药力（峻/缓）、归经、价格、适用场景、反藜芦禁忌——"人参峻补、党参平补；急救用人参，慢补用党参"。
</details>

<details>
<summary><b>Q3: 麻黄升麻汤是什么方？</b></summary>

东汉《伤寒论·辨厥阴病脉证并治》/14味组成/上热下寒病机/发越郁阳清上温下方义。
</details>

<details>
<summary><b>Q4: 理中丸和桂枝人参汤的异同？</b></summary>

> "桂枝人参汤 = 理中汤 + 解表，是理中丸的扩展应用，处理表里同病的情况。"
</details>

<details>
<summary><b>Q5 (新增): 祖方理中汤的家族演化？</b></summary>

通过 `references/zugfang/run_zugfang.py 理中汤 --a` 跑出**方族谱**：四逆汤（玉函）家族 13 个变法方——四逆加人参汤 / 茯苓四逆汤 / 通脉四逆汤 / 通脉四逆加猪胆汁汤 / 白通汤 / 白通加猪胆汁汤 / 干姜附子汤 / 甘草干姜汤 / 芍药甘草汤 / 茯苓甘草汤 / 调胃承气汤 / 四逆散 / 当归四逆汤，每个附「变法」说明和原文摘要。
</details>

---

## 📋 标准化方剂查询（v3.0 / formula_query.py 851 行终极版）

`scripts/formula_query.py` 是核心的标准化查询工具，**13 章节完全数据驱动**。当你需要查看某个方剂或条文的 **历代医家论述汇总** 时使用。

### 用法

```bash
python scripts/formula_query.py <关键词> [选项]
```

### 示例

```bash
# 查询桂枝人参汤（默认表格模式：朝代排序 + 原文摘要）
python scripts/formula_query.py 桂枝人参汤

# 查询小柴胡汤
python scripts/formula_query.py 小柴胡汤

# 查询某个证候/条文
python scripts/formula_query.py "协热利"
python scripts/formula_query.py "心下痞硬"

# 生成完整结构化报告（13 章节）
python scripts/formula_query.py 甘草泻心汤 --full-report

# 指定输出路径 + 限制卡片数
python scripts/formula_query.py 麻黄升麻汤 --full-report -o 我的报告.md --max-cards 15
```

### 输出格式

#### 表格模式（默认）

自动输出按 **朝代从古至今排序** 的 Markdown 表格：

| 朝代 | 著作 | 作者 | 原文论述摘要 | 卡片类型 |
|:----:|:----:|:----:|:-----------|:--------:|
| 东汉 | 《伤寒论》 | 张仲景 | 太阳病，外证未除，而数下之，遂协热而利… | herb |
| 金 | 《明理论》 | 成无己 | 此一热字，乃言表热也，非言内热也… | clinical_theory |
| 明 | 《景岳全书》 | 张介宾 | 独不观仲景桂枝人参汤，岂治内热之剂乎？… | clinical_theory |
| 清 | 《四圣心源》 | 黄元御 | 宜桂枝人参汤，桂枝解其表，姜甘参术解其里… | clinical_theory |
| 民国 | 《伤寒金匮发微》 | 曹颖甫 | 宜于理中汤或桂枝人参汤者十不过二三 | clinical_theory |
| 现代 | 《方剂学》 | 教材 | 【功效】温阳健脾，解表散寒 | synthesis |
| … | … | … | … | … |

#### 完整报告模式（`--full-report`）

13 章节完全数据驱动的结构化 Markdown 文档：

| 章节 | 内容 |
|:-----|:-----|
| 一、出处溯源 | 经典原文、组成、煎服法 |
| 二~十一、朝代论述 | 按朝代展开的历代医家论述（东汉→现代） |
| 十二、病机归纳 | 核心病机、证候要点、治法方解 |
| 十三、方剂演变 | 泻心汤类方演变关系图 |
| 十四、临床应用 | 经典适应症、现代对应疾病 |
| 十五、剂量换算 | 历代剂量参考 |
| 附录 | 证据索引表 |

报告自动保存为 `{方剂名}_历代注解.md`。

### 可选项

```bash
--max-cards N     # 每个朝代最多输出多少条（默认 10）
--full-report     # 生成完整结构化 Markdown 报告
-o <文件>         # 指定完整报告输出路径
--references-dir  # 指定 evidence_cards.jsonl 目录（默认 references/text_distillation/）
```

### 与 text_search.py 的区别

| 工具 | 用途 |
|:----|:----|
| `text_search.py` | 原始关键词检索，返回卡片原始内容 |
| `formula_query.py` | **标准化输出**，自动识别朝代/作者并按年代排序为表格 |
| `formula_query.py --full-report` | **完整结构化报告**，13 章节 Markdown 文档 |

---

## 🌳 祖方演化分析（references/zugfang/）

张璐《张氏医通》卷十六·祖方 36 个方祖 + 384 个变法方的家族结构化解析。源自张璐自拟方 235 + 引用方 149。

### 4 个子能力

```bash
# Skill A — 方族谱（家族 + 加减法查询）
python references/zugfang/run_zugfang.py 理中汤 --a

# Skill B — 跨书演化时间轴（6 源拼接）
python references/zugfang/run_zugfang.py 四逆汤 --b

# Skill C — 跨祖方家族对比
python references/zugfang/run_zugfang.py 理中汤 四逆汤 桂枝汤 --c

# Skill C.2 — 病证反查
python references/zugfang/run_zugfang.py --z "上热下寒"
```

### 共享模块

- `zugfang_family_parser.py` (426 行) — 解析张璐祖方章节
- `_parsed_cache.json` (180KB) — 解析缓存
- `baizhu_fuzi_tang_literary_history.md` — 白术附子汤历代注解（11 医家）

---

## 🔍 L2 蒸馏卡截断 → 双源取证（skills/double-fetch/）

当用户说"原文被截断了""被截掉""对不上""异文""未找到"时，自动启用：

```bash
python skills/double-fetch/scripts/verify_double_fetch.py "<被截断的文本>"
```

**双源取证策略**：L2 蒸馏卡（jsonl，281 字符截断）查不到 → L1 books_json/（689 本古医书完整 JSON）查 → L0 SQLite（zysj.db，1.8 亿字符）查。三层 fallback 保证找到原文。

入口：`skills/double-fetch/SKILL.md` + `skills/double-fetch/scripts/verify_double_fetch.py`

---

## 🏗️ 仓库结构

```
zhongyishijia-skill/
├── SKILL.md                     # Agent 入口描述 (v2.0, Step 1-5 + 6 子 Skill)
├── CHANGELOG_2026-08-13.md      # 📜 2026-08-13 大整合工程记录 (284 行)
├── SIMPLE_SYNC.md               # 🔄 3-machine 同步 SOP (含大整合分支合并 SOP)
├── RESULT_CARD.md / .html       # 成果卡片
├── lineage_manifest.json        # 元数据
├── agents/
│   ├── openai.yaml              # OpenAI/Codex 接口配置
│   └── openclaw.yaml            # OpenClaw 接口配置
├── skills/                       # ⭐ 6 个独立子 Skill
│   ├── formula-query/            # 方剂查询子 skill
│   ├── herb-query/               # 本草查询子 skill
│   ├── symptom-query/            # 症状→核心药子 skill
│   ├── evidence-fetch/           # card_id 取回子 skill
│   ├── text-search/              # 关键词检索子 skill
│   └── double-fetch/             # ⭐ L2 蒸馏卡截断时双源取证 (362 行 verify 脚本)
├── references/
│   ├── okf/                      # OKF 渐进式阅读框架
│   ├── books_json/               # 📚 689 本古医书完整 JSON (LFS, 75MB)
│   ├── external/                 # 💾 zysj.db SQLite (1.8 亿字符, git-lfs)
│   │   └── zysj_index.py         # external SQLite 索引
│   ├── raw/                      # 原始 SQLite (660MB, 不入 git)
│   ├── collations/               # 异文校勘档案 (fuxingjue_dabuxixin2_xinjiaozheng.json)
│   ├── text_distillation/
│   │   └── evidence_cards.jsonl  # 🎯 核心: 317K 张卡片 (LFS, 268MB)
│   ├── course_digest.md          # 课程摘要
│   ├── course_package.json       # 课程包元数据
│   ├── concept_glossary.md       # 概念词典
│   ├── evidence_map.json         # 证据映射
│   ├── full_transcript.md        # 源文件索引
│   ├── lesson_index.json         # 课程路径索引
│   ├── quote_index.md            # 金句索引
│   ├── study_paths.md            # 学习路径
│   ├── mentor_playbook.md        # 导师剧本
│   ├── learner_progress.json     # 学习进度
│   ├── install-path.md           # 安装路径说明
│   ├── SQLITE_PITFALLS.md        # SQLite 字段位置 / 编码 / 反例模式（必读）
│   ├── zhangxichun_yangxu_formula.md    # 张锡纯治肾阳虚专题
│   ├── jianzhong_family_lineage.md       # 建中类方家族演化谱系专题
│   ├── houshi_heisan_literary_history.md # 侯氏黑散历代注解 (11 医家)
│   ├── xiongbi_jiu_literary_history.md   # 胸痹第九历代注解 (17 医家)
│   ├── xiaoluo_dan_literary_history.md   # 消瘰丸/消瘰丹/消疠丸 4 医家化裁 (15KB)
│   ├── yantong_literary_history.md       # 咽痛历代医家论述 (24 条/战国-民国, 32KB)
│   ├── tanpi_zhibian_yanshuo.md          # 痰癖治法演变全库溯源 (28 朝代/138 TypeID/379 原文/924 行/80KB, 10 节展开)
│   ├── distillation_workflow.md         # 深度蒸馏工作流 (3 阶段 9 步 + 5 段模板 + 双编码修复 SOP, 17KB)
│   ├── wenyao_bixi_daquan.md          # 闻药·鼻吸·鼻烟方剂大全 (115 张/10 大类/3 张鼻烟壶配方, 29KB)
│   ├── wenyao_query_workflow.md       # 方剂专题查询工作流 (3 阶段 4 步, 适用任何 X 主题方剂查询, 17KB)
│   ├── zhongyi_source_citation_principle.md # 中医方剂引用原文 5 大铁律 (不带省略号/双编码/不删减/可溯源/朝代, 10KB)
│   ├── fuling_xingren_ju_zhi_comparison.md # 茯苓杏仁甘草汤 vs 橘枳姜汤对偶
│   ├── coverage_audit.md         # 经典覆盖率审计
│   ├── tcm_research_methodology.md # 4 步唐宋古方研究方法论
│   ├── natural_language_query.md # 5 意图解析模式
│   ├── known_pitfalls.md         # 10 大 Python/Regex/SQL 陷阱
│   ├── zero_hit_fallback_workflow.md # 0 命中时的 SQLite fallback 4 步法
│   ├── formula_metadata_table.md # 方剂元数据 5 大陷阱
│   ├── formula_curation_workflow.md # 8 步方剂考据流水线
│   └── zugfang/                  # ⭐ 祖方演化分析附属包
│       ├── README.md
│       ├── run_zugfang.py        # 统一入口 (--a/--b/--c/--z)
│       ├── family_tree.py        # Skill A: 方族谱
│       ├── evolution_timeline.py # Skill B: 跨书演化时间轴
│       ├── cross_family_compare.py # Skill C: 跨祖方对比
│       ├── zheng_lookup.py       # Skill C.2: 病证反查
│       ├── zugfang_family_parser.py # 共享解析器 + 缓存
│       ├── _parsed_cache.json    # 解析缓存 (180KB)
│       └── baizhu_fuzi_tang_literary_history.md # 白术附子汤历代注解
├── scripts/
│   ├── text_search.py            # 关键词检索（Agent 主入口）
│   ├── evidence_fetch.py         # 按 card_id/chunk_id 取证据
│   ├── formula_query.py          # ⭐ 851 行方剂终极版（13 章节完全数据驱动）
│   ├── herb_query.py             # 本草 + 含药方剂
│   ├── symptom_query.py          # 症状→高频核心药
│   ├── formula_table.py          # ⭐ 含 X 药方剂 5 列表 (392 行)
│   ├── verify_prescription.py    # ⭐ 自然语言查询验证 (688 行)
│   ├── verify_exact_match.py     # 精确匹配验证 (171 行)
│   ├── verify_sqlite_coverage.py # ⭐ SQLite 烟雾测试 + 覆盖率探针 (206 行)
│   └── before_leaving.sh         # 出门前安全检查
├── templates/
│   └── formula_report_template.md # 方剂报告模板
├── docs/                          # 📖 进阶文档
│   ├── PLAN_v3_query_herb.md     # v3.0 query_herb 计划
│   ├── houshi_heisan_*.md        # 侯氏黑散历代注解
│   └── ...
└── RESULT_CARD.md / .html / .png  # 项目成果展示
```

---

## 🔧 自己重建（可选）

如果你有自己的 zysjmssqlbak.sqlite 数据，可以重新生成 `evidence_cards.jsonl`：

```bash
# 重新蒸馏 SQLite → evidence_cards.jsonl
python scripts/redistill_cards.py
# 或（v3.0 重蒸馏）
python scripts/extract_books_to_json.py    # 从原始 SQLite 提取书籍 JSON
python scripts/build_herb_index.py         # 构建本草反向索引
```

蒸馏参数（参考 `scripts/redistill_cards.py` 内含）：
- 从 `zysjyj` (中药字典) 生成 herb cards
- 从 `zysjllsj` (临床理论) 生成 clinical_theory cards
- 从 `zysjzhsj` (综合数据) 生成 synthesis cards
- 摘要截断 280 字符 / 卡片平均 766 字节

---

## 📜 数据来源

- **中医世家**（zysj.com.cn）2012-2014 年的完整离线数据
- 678 本古医书 CHM（伤寒论 / 本草纲目 / 黄帝内经 / 针灸大成 / 景岳全书 / 脉经 / 难经 / 温病条辨…）
- MySQL `zysjmssqlbak` 数据库（4 表，318K 行）
- MSSQL `20120413mssql` 数据库（备份 → SQLite 还原）

⚠️ **数据本身不在本仓库**——本仓库只装派生出的 evidence cards。如果需要 raw 原始数据，请参考 [中医世家网站](https://www.zysj.com.cn)。

---

## 🎯 适用场景

- ✅ 中医师临床参考
- ✅ 中医学生复习/考试
- ✅ 中医方剂学/中药学溯源
- ✅ 中医方剂家族演化研究（祖方→变法方）
- ✅ 历代医家论述汇总（按朝代排序）
- ✅ RAG 检索演示（用 MiniMax-M3 / Claude / GPT 都跑得起来）
- ⚠️ **不构成临床诊疗建议**——最终处方需经执业中医师辨证

---

## 📦 相关项目

- **lineage-skill** — 本 skill 的构建框架 ([JuneYaooo/lineage-skill](https://github.com/JuneYaooo/lineage-skill))

---

## 📋 更新日志

### v3.1 (2026-08-17) — 多分支合并 + 2 个新专题补登记

- **合并** `darwin-eval-2026-08-13` (7 commits) + `feat/yantong-literary-history` (3 commits) 到 `main`，冲突矩阵 0，git 自动合并干净
- **新增** `references/yantong_literary_history.md` — 咽痛历代医家论述（24 条 / 战国《灵枢》→ 民国·张锡纯 / 32KB / 380 行）
- **新增** `references/tanpi_zhibian_yanshuo.md` — 痰癖治法演变全库溯源（28 朝代 / 138 TypeID / 379 条原文 / 24KB / 392 行）
- **修改** `.gitignore` 排除 `references/external/*.db` 占位 SQLite
- **修改** `SKILL.md` Reference Priority 22→24（追加 yantong + tanpi 编号）
- **修改** `README.md` 仓库结构树追加 2 行 + v3.1 变更记录
- **沿用** SIMPLE_SYNC.md 8 步大整合 SOP（tag pre-merge → merge --no-ff → drift 检测 → push）

### v3.2 (2026-08-17) — 痰癖文档 10 节全部展开 + 思源同步

- **展开** `references/tanpi_zhibian_yanshuo.md` 10 个未充分章节（按 ④ 孙思邇 532 字模板）：
  - ⑪ 宋·《圣济总录》（TypeID=122）—— 11 条原文 + 4 首方剂 + 病机 4 要点 + 承接 ⑨→⑩→⑫
  - ⑫ 元·东垣《脾胃论》（TypeID=877）—— 3 条药性赋 + 朴硝/芒硝/莱菔精微 + 攻→补转向
  - ⑬ 元·王好古《此事难知》（TypeID=245）—— 4 条药论 + 脏腑辨证精微（气胸膈/血心腹）
  - ⑰ 明·龚氏父子（TypeID=572, 613）—— 4 条原文 + 脾肾双补论 + 6 味核心药
  - ⑲ 清·汪昂《本草备要》/《医方集解》（TypeID=246, 1374, 1375）—— 8+4 条原文 + 半夏天麻白术汤 + 无痰不作疟论
  - ㉑ 清·陈士铎《本草秘录》（TypeID=624）—— 3 条药论 + 奇方思路 + 岭南地理病机论 + 天地相救论
  - ㉓ 清·凌奂《本草害利》（TypeID=775）—— 3 条药害论（首创「药害/药利」双轨论）
  - ㉔ 清·沈金鳌《杂病源流犀烛》（TypeID=720）—— 产后痰癖总治则（先补后攻）
  - ㉕ 清·三书（姚澜 TypeID=764 / 严西亭 TypeID=689 / 黄宫绣 TypeID=619）—— 严西亭 12 经痰辨证 + 黄宫绣积/聚辨证 + 五饮论
  - ㉘ 日·丹波元坚《金匮述义》（TypeID=483）—— 痰 vs 饮金标准 + 积/聚/瘕/癖/结五证分类
  - 转折 5（清→日 朝代演变）—— 4 维度转折标志表 + 中日汇通
- **文档统计**：22KB → 80KB（+260%），392 → 924 行（+136%），10509 → 37016 字符（+252%）
- **数据库**：本地 `references/external/zysj.db` 替换 0 字节占位为 711MB 完整 SQLite（4 表 / 317,580 卡 / 70350 方剂 / 166423 临床理论）
- **脚本修复**：`scripts/_sqlite_utils.py` 三级查找 → 四级查找（加 `references/external/zysj.db` 兜底入口）；`scripts/verify_prescription.py` 删除硬编码 `_DB_PATH`，改用 `find_sqlite_path()` + 加 `--sqlite` 参数 + GBK 解码
- **思源同步**：自动 `fs.write` 到 `/医林独箫斋/总结/痰癖治法演变`（首次 131 块 / 10474 字符 / UUIDv7 requestId 严格模式 / Write Safety Guaranteed）
- **新发现陷阱**（已固化）：`zysjyj` = GBK，`zysjllsj` = UTF-8 — 不能 `text_factory = lambda b: b.decode("gbk")` 一刀切
- **修改** `README.md` tanpi 行体积（24KB → 80KB/924 行）+ 追加 v3.2 变更记录
- **新增** `references/distillation_workflow.md` — 深度蒸馏工作流 SOP（17KB / 12 节 / 3 阶段 9 步 / 5 段模板 / 双编码修复 SOP / UUIDv7 思源严格模式 / 10 大陷阱清单）。实战案例：tanpi 文档 10 节展开。触发词:「展开 XX 节」「补全 XX 章节」「深度蒸馏 XX」「tanpi 全展开」
- **新增** `references/wenyao_bixi_daquan.md` — 闻药·鼻吸·鼻烟方剂大全（29KB / 115 张 / 10 大类 / Top 30 高频药 / 3 张鼻烟壶装药配方 / 《千金》/《外台》鼻疗法溯源 / 朝代沿革轴）。触发词:「闻药」「鼻烟」「鼻烟壶」「鼻疗」「吹鼻」「搐鼻」「灌鼻」「取嚏」「鼻塞」「鼻渊」「鼻衄」「鼻息肉」「中恶急救」
- **新增** `references/wenyao_query_workflow.md` — 方剂专题查询工作流（17KB / 3 阶段 4 步 / 5 大陷阱 / 7 个可扩展主题）。适用任何「X 主题方剂查询」（明目方/安胎方/外科方/喉科方/妇科方/儿科方）。触发词:「方剂专题查询」「查 X 方剂」「X 主题方剂」「全库方剂」「明目方」「安胎方」「外科方」「喉科方」「妇科方」
- **新增** `references/zhongyi_source_citation_principle.md` — 中医方剂引用原文 5 大铁律（10KB）：① 原文不带省略号（Erik 硬性偏好）② SQLite 双编码修复（zysjyj=GBK / zysjllsj=UTF-8）③ 不删减讲师/原文内容（项目愿景「不编造」原则）④ 可溯源（每条引用必有 chunk_id）⑤ 朝代溯源按可查证据分级（A/B/C/D 级）。整合 tanpi v3.2 + wenyao 大全实战。触发词:「中医方剂」「引用原文」「省略号」「溯源」「朝代」「编码」「不编造」「不删减」
- **后续待**：固化 SOP 到 `references/distillation_workflow.md`（Stage 2）

### v3.0 (2026-08-13) — 大整合工程

**详情见 [`CHANGELOG_2026-08-13.md`](CHANGELOG_2026-08-13.md)**

**4 个 feat 分支合并入 main**（14 commits ahead，28 个新文件）：

- **新增** `skills/double-fetch/` 子 skill — L2 蒸馏卡截断时的双源取证（L0 SQLite + L1 books_json + L2 jsonl 三层 fallback）
- **新增** `references/zugfang/` 祖方演化分析 Skill 包 — 张璐《张氏医通》36 方祖 + 384 变法方（Skill A/B/C/C.2）
- **整合** `scripts/formula_query.py` 升级到 **851 行终极版**（13 章节完全数据驱动，融合 ultimate-report + double-fetch + 建中类方专题）
- **新增** 8 个 references 专题：
  - `coverage_audit.md` — 经典覆盖率审计
  - `tcm_research_methodology.md` — 4 步唐宋古方研究方法论
  - `natural_language_query.md` — 5 意图解析模式
  - `known_pitfalls.md` — 10 大 Python/Regex/SQL 陷阱
  - `zero_hit_fallback_workflow.md` — 0 命中时的 SQLite fallback
  - `formula_metadata_table.md` — 方剂元数据 5 大陷阱
  - `formula_curation_workflow.md` — 8 步方剂考据流水线
  - `houshi_heisan_literary_history.md` — 侯氏黑散 11 医家
- **新增** 3 个验证脚本：
  - `verify_prescription.py` (688 行) — 自然语言查询验证
  - `formula_table.py` (392 行) — 含 X 药方剂 5 列表
  - `verify_sqlite_coverage.py` (206 行) — SQLite 烟雾测试
- **新增** 5 个新 references：
  - `jianzhong_family_lineage.md` — 建中类方家族演化谱系
  - `xiongbi_jiu_literary_history.md` — 胸痹第九历代注解 (17 医家)
  - `xiaoluo_dan_literary_history.md` — 消瘰丸/消瘰丹/消疠丸 4 医家化裁专题 (程国彭 1732 / 清 14 味变方 / 张锡纯 / 周次青)
  - `fuling_xingren_ju_zhi_comparison.md` — 茯苓杏仁甘草汤 vs 橘枳姜汤对偶
  - `install-path.md` — 安装路径说明
  - `collations/fuxingjue_dabuxixin2_xinjiaozheng.json` — 异文校勘档案
- **新增** `references/raw/SQLITE_PITFALLS.md` — SQLite 字段位置/编码/反例模式（必读）
- **新增** `external/zysj_index.py` — external SQLite 索引
- **重写** `SKILL.md` v2.0 — 子 Skill 索引 5→6，Reference Priority 14→21，Capability Reading Strategy Step 1-5（新增 19 条高级指引）
- **新增** `CHANGELOG_2026-08-13.md` — 完整大整合记录 (284 行)
- **新增** `SIMPLE_SYNC.md` 「问题 6 多 feat 分支堆积」8 步 SOP — 项目阶段性分支整合标准流程
- **删除** 4 个已合并的远端 feat 分支（feat/double-fetch-skill, feat/ultimate-report, feat/zugfang-evolution-analysis, formula-query-clean）
- **回滚** `formula-query-clean`（已被 double-fetch 取代，SKILL.md 0 行差异 + 公式脚本是 335 行精简版）

### v2.2 (2026-07-26 草案 / 2026-08-13 大整合实现)

> **注**：v2.2 内容在 2026-08-13 大整合中实现并合入 main，本节描述文件创建计划。

- **新增** `scripts/verify_sqlite_coverage.py` — SQLite 烟雾测试与覆盖率探针
- **新增** `references/external/zysj.db` — 1.8 亿字符完整 SQLite (LFS, 710MB)
- **新增** `references/zero_hit_fallback_workflow.md` — 0 命中 fallback 4 步法
- **文档** README 增加 SQLite 部署章节

### v2.1 (2026-07-11)

- **新增** `scripts/formula_query.py --full-report` — 完整报告生成模式
  - 新增 `templates/formula_report_template.md` 报告模板
  - 生成结构化 Markdown 文档（出处溯源、朝代论述、病机归纳、方剂演变、临床应用、剂量换算、证据索引）
  - 报告自动保存为 `{方剂名}历代注解.md`
- **更新** README 文档，增加 `--full-report` 功能说明

### v2.0 (2026-07-01)

- **新增** `scripts/formula_query.py`（原名 `query_formula.py`，2026-08-13 重命名）— 标准化方剂/条文查询工具
  - 搜索 317,580 张证据卡片，自动识别朝代/著作/作者
  - 按年代从古至今排序输出 Markdown 表格
  - 内置 50+ 条 source→(朝代, 著作, 作者) 映射表
  - 覆盖东汉张仲景、金成无己、明张介宾、清黄元御/柯琴/吴谦等十数家、民国曹颖甫及现代医家
  - Windows 终端 UTF-8 编码兼容
- **新增** 安装步骤第 6 步：试用标准化查询脚本
- **更新** 仓库结构图
- **更新** 自定义 Agent 使用说明

---

## 📄 License

MIT — 详见 [LICENSE](LICENSE)