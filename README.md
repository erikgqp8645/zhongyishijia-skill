# 中医世家知识库 Skill (zhongyishijia-skill)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Skill size](https://img.shields.io/badge/size-233MB-blue)](references/text_distillation/evidence_cards.jsonl)
[![Evidence cards](https://img.shields.io/badge/evidence_cards-317K-brightgreen)](references/text_distillation/evidence_cards.jsonl)
[![Source](https://img.shields.io/badge/source-zysj.com.cn-orange)](https://www.zysj.com.cn)

> **课程驱动的中医世家网站离线知识库**，已转化为 lineage-skill 格式，可直接安装到 Hermes / OpenClaw / Codex / Claude 等任何支持 lineage-skill 的 Agent runtime。

---

## 📖 这是什么？

将中医世家网站（zysj.com.cn）2012-2014 年的完整离线数据（678 本古医书 CHM + 两个 SQL 数据库，共 5.7GB 原始数据）**蒸馏**为：

- **31.7 万张结构化 evidence cards**（平均 766 字节/张）
- 每张卡包含方剂名 / 病证名 / 中药名 / 主治 / 处方 / 各家论述 / 出处
- 引用关系可追溯到《伤寒论》《金匮要略》《本草纲目》等具体古籍

LLM 通过 `search_course_notes.py` 在 cards 里检索关键词 + 来源，**不会编造**，回答可验证。

---

## 📊 数据规模

| 类别 | 来源表 | 卡片数 | 代表内容 |
|---|---|---|---|
| herb（中药/方剂） | `zysjyj` | **70,350** | 麻黄汤、桂枝人参汤、人参… |
| clinical_theory（临床理论） | `zysjllsj` | **166,421** | 协热下痢、痞证表里、伤寒六经… |
| synthesis（综合医话/方论） | `zysjzhsj` | **80,809** | 历代各家注解、现代临床应用 |

**总计 317,580 张** · **231.9 MB** · **横跨东汉-现代 1800 多年**

---

## 🚀 安装

### 方式一：作为 Hermes Skill（推荐）

```powershell
# 1. 克隆仓库
git clone https://github.com/erikgqp8645/zhongyishijia-skill.git
cd zhongyishijia-skill

# 2. 安装 git-lfs（首次需要）
git lfs install

# 3. 拉取大文件 (231MB LFS)
git lfs pull

# 4. 复制到 hermes skill 目录
Copy-Item -Recurse . "$env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage"

# 5. 验证
python "$env:USERPROFILE\.hermes\skills\zhongyishijia-expert-mentor-lineage\scripts\search_course_notes.py" '桂枝人参汤'
```

### 方式二：作为 OpenClaw Skill

```bash
# SKILL.md 兼容 OpenClaw 规范
cp -r . ~/.openclaw/skills/zhongyishijia-expert-mentor-lineage
```

### 方式三：自定义 Agent（任何支持 lineage-skill 的 runtime）

把 `SKILL.md` + `references/` + `scripts/` 路径告诉你的 Agent 即可：

- 把 `references/` 当作 Agent 的 lookup path
- 任何时候需要查证方剂/病证/中药时，运行 `scripts/search_course_notes.py <关键词>`

---

## 🧪 验证测试

4/4 测试全部通过 — hermes 用 MiniMax-M3 + zysj skill 跑的实际回答：

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

---

## 🏗️ 仓库结构

```
zhongyishijia-skill/
├── SKILL.md                     # Agent 入口描述
├── lineage_manifest.json        # 元数据（schema_version, roles, etc.）
├── agents/
│   ├── openai.yaml              # OpenAI/Codex 接口配置
│   └── openclaw.yaml            # OpenClaw 接口配置
├── references/
│   ├── course_digest.md         # 课程摘要
│   ├── course_package.json      # 课程包元数据
│   ├── concept_glossary.md      # 概念词典
│   ├── evidence_map.json        # 证据映射（按类别）
│   ├── full_transcript.md       # 源文件索引（1232 条 lesson）
│   ├── lesson_index.json        # 课程路径索引
│   ├── quote_index.md           # 金句索引
│   ├── study_paths.md           # 学习路径
│   ├── mentor_playbook.md       # 导师剧本
│   ├── learner_progress.json    # 学习进度
│   ├── okf/                     # OKF 渐进式阅读框架
│   │   ├── index.md
│   │   ├── study-paths/
│   │   └── boundaries/
│   └── text_distillation/
│       └── evidence_cards.jsonl # 🎯 核心: 317K 张卡片 (LFS, 231MB)
└── scripts/
    ├── search_course_notes.py   # 关键词检索（Agent 主入口）
    ├── fetch_course_evidence.py # 按 chunk_id 取证据
    └── search_md.py             # 全 markdown 文件检索（可选）
```

---

## 🔧 自己重建（可选）

如果你有自己的 zysjmssqlbak.sqlite 数据，可以重新生成 `evidence_cards.jsonl`：

```python
# scripts/build_evidence_cards.py 内含：
# - 从 zysjyj (中药字典) 生成 herb cards
# - 从 zysjllsj (临床理论) 生成 clinical_theory cards
# - 从 zysjzhsj (综合数据) 生成 synthesis cards
# - 摘要截断 280 字符 / 卡片平均 766 字节
```

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
- ✅ RAG 检索演示（用 MiniMax-M3 / Claude / GPT 都跑得起来）
- ⚠️ **不构成临床诊疗建议**——最终处方需经执业中医师辨证

---

## 📦 相关项目

- **lineage-skill** — 本 skill 的构建框架 ([JuneYaooo/lineage-skill](https://github.com/JuneYaooo/lineage-skill))

---

## 📄 License

MIT — 详见 [LICENSE](LICENSE)
