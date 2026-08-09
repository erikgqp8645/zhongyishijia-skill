---
name: formula_curation_workflow
purpose: How to curate a "X 方剂 历代医家论述" topic bank from raw zhongyishijia queries — from jsonl 截断卡 → 8-TypeID 反查 → 11-医家固化专题 + 双端同步 (local skill + GitHub push)
trigger: 「固化方剂专题」「方剂溯源」「方剂论述汇总」「朝代排序的医家论述」「TypeID 反查」「固化到 skill」
date_verified: 2026-08-03
canonical_example: 侯氏黑散 → references/houshi_heisan_literary_history.md (本地) + erikgqp8645/zhongyishijia-skill commit 7569033 doc/侯氏黑散历代注解.md (远端)
---

# 方剂专题固化工作流

## 适用场景

Erik 问"**X 方剂的历代医家论述**"时（如侯氏黑散、桂枝人参汤、茯苓甘草汤），用 `scripts/query_formula.py` 只能拿到 jsonl 截断到 281 字的卡片，**所有"待考"作者归属都拿不到**。本工作流固化这一过程：把 281 字截断 → 反查 zysjllsj TypeID → 锁定作者/朝代/章节 → 写成 1 个完整专题文件 → 本地 + GitHub 双端同步。

## 端到端流程

```
用户问「X 方剂的历代医家论述」
         │
         ↓
Step 1: query_formula.py (jsonl 截断层)
         │
         ↓ (得到 N 条证据卡 + M 个"zysjllsj TypeID=xxx"待考条目)
Step 2: zysjllsj TypeID 反查 (作者溯源层)
         │
         ↓ (得到 M 个 TypeID 的真实作者/章节 ID/章节名)
Step 3: 整理成 11-医家结构 + 3-论争对照表 + TypeID 溯源表
         │
         ↓
Step 4: 写本地 references/<formula>_literary_history.md
         │
         ↓
Step 5: SKILL.md line 61 末尾追加 1 行指引 (不改 Reference Priority)
         │
         ↓
Step 6: 推送 GitHub erikgqp8645/zhongyishijia-skill 到 doc/<formula>历代注解.md
         │
         ↓
Step 7: 验证 (远端 raw.githubusercontent.com + 本地文件大小一致)
         │
         ↓
Step 8: 清理 /tmp/<formula>-push
```

## Step 1 — query_formula.py (jsonl 截断层)

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage
python3 scripts/query_formula.py "侯氏黑散" > /tmp/<formula>_raw.md
```

**输出格式**（朝代排序 Markdown 表）：每条带 `# 朝代 | 著作 | 作者 | 原文论述摘要 | 卡片类型`。**关键**：每条 evidence_cards.jsonl 卡的 source_ref 字段含 `zysjllsj TypeID=XXX` 标记（待考条目），其他条目已含作者/朝代。

**典型输出**（侯氏黑散样例）：14 条证据卡 + 8 个 zysjllsj TypeID（125/160/238/625/633/722/738/822）= 7 条已署名 + 7 条"待考"。

## Step 2 — zysjllsj TypeID 反查 (作者溯源层)

```python
import sqlite3
con = sqlite3.connect('references/external/zysj.db')
cur = con.cursor()

# 1. 看 TypeID 第一条 BiaoTi — 经常是"作者：XXX 朝代：XXX"或书名
cur.execute("SELECT ID, BiaoTi FROM zysjllsj WHERE TypeID=? ORDER BY ID LIMIT 5", (tid,))
for r in cur.fetchall():
    print(r[0], '|', r[1])

# 2. 找含"<关键词>"的 NeiRong 行 → 拿到真实章节 ID
rows = cur.execute(
    "SELECT ID, BiaoTi, length(NeiRong) FROM zysjllsj WHERE TypeID=? AND NeiRong LIKE '%关键词%'",
    (tid,)
).fetchall()

# 3. 拉章节前 600 字符看是否含自序署款（确认作者）
for r in rows:
    intro = cur.execute("SELECT substr(NeiRong,1,800) FROM zysjllsj WHERE ID=?", (r[0],)).fetchone()[0]
    print('--- ID', r[0], '| BiaoTi:', r[1], '|', r[2], '字 ---')
    print(intro[:600])
```

**反查 5 大信号**（按优先级）：

| # | 信号 | 例子 | 用途 |
|---|------|------|------|
| 1 | BiaoTi 第一行明载"作者：XXX 朝代：XXX" | "作者：张璐 朝代：清 年份：公元1617－1700年" | 100% 锁定 |
| 2 | BiaoTi 第一行是书名 + 朝代 | "汉·张仲景" / "金匮要略方论序" | 锁定作者/朝代 |
| 3 | 章节内含自序署款 | "乾隆丁丑秋七月洞溪徐大椿书于吴山之半松书屋" | 100% 锁定 |
| 4 | 章节体例独特性 | 《医门法律》"望色论（附律一条）" → 喻嘉言 | 风格佐证 |
| 5 | TypeID 第一条 BiaoTi 是问号 | "作者：？ 朝代：？" | ⚠️ 需要靠序文/体例反推 |

**典型输出**（侯氏黑散样例）：8 个 TypeID 全部锁定到具体作者（袁体庵/喻嘉言/张璐/徐大椿/陈修园/费伯雄），1 个 TypeID=822 存疑（database metadata 标费伯雄/《医方论》但论述似唐容川）。

## Step 3 — 整理成固化专题结构

固化专题文件结构（按 references/houshi_heisan_literary_history.md 模板）：

1. **东汉书源**（张仲景原方 + 章节 ID）
2. **按朝代排列的医家论述**（明末 → 清初 → 清中 → 清末），每条标 TypeID + 章节 ID + 章节名 + 锁定方式
3. **3 大论争对照表**（按争点分组：是不是主方 / 冷服机制 / 菊花君药）
4. **TypeID 反查溯源表**（每一行可复现的 TypeID + 章节 ID + 锁定方式）
5. **核心反查路径**（可复现 SQL + Python）
6. **一句话核心心法**（强制要求，如"读懂侯氏黑散，等于读懂半部中风学"）

**filename 选择**：
- 本地：`references/<formula>_literary_history.md` (snake_case 英文，如 `houshi_heisan_literary_history.md`)
- 远端：`doc/<formula>历代注解.md` (中文 + 既有风格，如 `doc/桂枝人参汤历代注解.md`)

## Step 4 — 写本地 references/<formula>_literary_history.md

```bash
# 写文件
write_file path=~/.hermes/skills/zhongyishijia-expert-mentor-lineage/references/<formula>_literary_history.md content=...
```

**首行格式**（参考 houshi_heisan_literary_history.md）：

```
# <方剂名>历代医家论述溯源

> 共检索到 **N 条** 相关证据卡片 + M 个 TypeID 反查条目，以下按朝代从古至今排列
> 数据来源：中医世家知识库 `references/text_distillation/evidence_cards.jsonl`（317,580 张卡片）+ zysjllsj 数据库 TypeID 反查
> 关键溯源：所有"待考"条目已通过 zysjllsj 表 TypeID/ID/BiaoTi/NeiRong 自序反查锁定到具体作者与著作
> 配套工具：`scripts/query_formula.py "<方剂>"` 列出 jsonl 命中条目；本文件已固化所有反查结果
> 同源远端：`https://github.com/erikgqp8645/zhongyishijia-skill/blob/main/doc/<方剂>历代注解.md`
```

## Step 5 — SKILL.md line 61 末尾追加 1 行指引

**插入位置**：SKILL.md line 61（`scripts/query_formula.py <关键词>` 那行）末尾。

**插入格式**（参考已加的侯氏黑散指引）：

```markdown
- For "ancient formula listing" queries (e.g. "X 方剂的历代医家论述"), use `scripts/query_formula.py <关键词>` — outputs 朝代排序的医家论述汇总 from `evidence_cards.jsonl` (281-char truncated cards). For <方剂名> specifically, the full N-医家 + M-TypeID-反查 trace is pre-cured at `references/<formula>_literary_history.md` (covers <作者1>/<作者2>/... + <论争1>/<论争2>/...).
```

**绝对不要做**：
- ❌ **不要**改 Reference Priority 段（1..N 严格编号，那是工具/基础设施，固化方剂专题不属于该范畴）
- ❌ **不要**插到 Capability Reading Strategy 列表中间（会破坏现有"## For xxx" 模式）
- ❌ **不要**新增独立段（"## 已固化方剂专题" 会让 SKILL.md 越来越碎）

## Step 6 — 推送 GitHub erikgqp8645/zhongyishijia-skill

```bash
# 1. 浅 clone（避免深 clone 慢）
cd /tmp
rm -rf <formula>-push
GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=3000 clone --depth 1 \
  https://github.com/erikgqp8645/zhongyishijia-skill.git /tmp/<formula>-push
cd /tmp/<formula>-push

# 2. 关键安全检查：远端 SKILL.md 可能是子 skill 重构版（5 子 skill 框架），
#    跟本地 94 行 Reference Priority 框架结构不同。
#    ⚠️ 绝对不能直接覆盖远端 SKILL.md！只新增文件。
```

**3 个绝不能**（避免 2026-08-03 侯氏黑散推送时的"删除 757 个文件"事故）：

1. **绝不能** `git add -A` 或 `git add .`（会误带已 staged 的"删除项"）
2. **绝不能** `git reset --hard HEAD`（会触碰 206MB books_json/ 库导致 60s+ 超时）
3. **绝不能** 远端 SKILL.md 用本地完整版覆盖（会破坏远端 5 子 skill 重构）

**正确推送流程**：

```bash
# 3. 写远端 doc/<方剂>历代注解.md（基于本地版本，但首行加"远端版本"标识）
write_file path=/tmp/<formula>-push/doc/<方剂>历代注解.md content=...

# 4. ⚠️ 关键：用 md5 备份新文件，防止误操作
md5 -q /tmp/<formula>-push/doc/<方剂>历代注解.md  # 记下 hash

# 5. 单文件 add（必须 explicit 文件名，不能用 -A 或 .）
cd /tmp/<formula>-push
git status -s  # 确认只有新文件是 untracked，没有"deleted" 残留
git add doc/<方剂>历代注解.md
git status -s  # 确认 staged 只有 1 个 new file，没有 D 文件被带进 commit

# 6. 提交
git -c user.name=hermes -c user.email=hermes@erikgqp8645.local commit \
  -m "doc: add <方剂>历代注解 (N 医家 + M TypeID 反查 + 论争)"

# 7. 推送
git push origin main
```

## Step 7 — 验证

```bash
# 1. 远端 raw.githubusercontent.com 拉文件
curl -sL "https://raw.githubusercontent.com/erikgqp8645/zhongyishijia-skill/main/doc/<方剂>历代注解.md" | wc -c
# 应 = 本地 bytes

# 2. md5 二次确认
diff <(md5 -q /tmp/<formula>-push/doc/<方剂>历代注解.md) \
     <(md5 -q <(curl -sL "https://raw.githubusercontent.com/erikgqp8645/zhongyishijia-skill/main/doc/<方剂>历代注解.md"))
# 期望: 空 (无 diff)

# 3. git log 确认 commit
git log --oneline -3
# 顶部应是新 commit, 第二行是 d4bbd22 docs: 更新 v2.1 changelog
```

## Step 8 — 清理

```bash
cd /
rm -rf /tmp/<formula>-push /tmp/<formula>_raw.md
```

## 已知陷阱（2026-08-03 侯氏黑散实战验证）

### 陷阱 1: git add 误带"D"状态导致删除 757 个文件

**症状**：`git status -s` 显示所有远端文件为 "D"（deleted）状态，工作区所有本地文件为 "?? untracked"。

**原因**：浅 clone 期间网络中断 + shell pwd 卡在已删 `/tmp/<formula>-push/`，导致 git 工作区处于"颠倒"状态——index 指向某次中断前的版本（包含所有远端文件），工作区实际只有新加的 doc/<方剂>.md。

**修复**（不要 git reset --hard！会超时）：
```bash
# 1. 先备份新文件
cp /tmp/<formula>-push/doc/<方剂>历代注解.md /tmp/<formula>_backup.md
md5 -q /tmp/<formula>_backup.md  # 记下 hash

# 2. soft reset 撤销错 commit（如果已经提交）
git reset --soft HEAD~1

# 3. 清 staged
git reset HEAD

# 4. 用 mixed reset 同步 index（不碰工作区大文件）
git reset --mixed HEAD  # 关键：--mixed 不动 working tree
```

**验证已恢复**：
- `git log` 顶部回到 `d4bbd22`（远端原始 commit）
- `doc/<方剂>历代注解.md` 还在（md5 匹配备份）
- `git status -s` 只剩新文件 + 1 个 D (evidence_cards.jsonl lfs pointer，正常)

### 陷阱 2: 远端 SKILL.md 与本地结构不同，强行覆盖会破坏远端

**症状**：本地 SKILL.md 是 94 行 Reference Priority 框架版；远端 SKILL.md 是 125 行 5 子 skill 重构版（formula-query / herb-query / symptom-query / evidence-fetch / text-search）。

**解决**：**绝对不要覆盖远端 SKILL.md**。只新增 `doc/<方剂>历代注解.md`，与既有 `doc/桂枝人参汤历代注解.md` 风格一致。

### 陷阱 3: LFS 跟踪大文件让 git status 报"D"

**症状**：`references/text_distillation/evidence_cards.jsonl` 和 `references/books_json/*.json` 被 `.gitattributes` LFS 跟踪，工作区里实际只有 LFS pointer（几十字节），不是真实 200MB+ 文件。`git status` 可能报"D"。

**解决**：这些"D"是正常的，**不要尝试 git restore 这些文件**（会触发 60s+ 超时下载 LFS）。直接 add 自己的新文件即可。

### 陷阱 4: 文件名含中文，URL 编码会乱

**症状**：`https://raw.githubusercontent.com/.../侯氏黑散历代注解.md` 中文 URL 必须用 `%E4%BE%AF%E6%B0%8F...` 编码。

**解决**：
```bash
# 用 curl --data-urlencode 或直接 URL 编码
ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('侯氏黑散历代注解.md'))")
curl -sL "https://raw.githubusercontent.com/.../${ENCODED}" | wc -c
```

### 陷阱 5: SKILL.md line 61 patch 失败时整篇 SKILL.md 被读

**症状**：patch 工具在 read_file 部分加载时如遇 offset/limit 截断，patch 后会"re-read the whole file"。

**解决**：patch 之前先 read_file 整篇 SKILL.md（94 行）一次性读完。

## 验证命令（固化完成后跑一次）

```bash
# 1. 本地专题文件存在
ls -la ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/references/<formula>_literary_history.md

# 2. SKILL.md 已加 1 行
grep -n "references/<formula>_literary_history.md" \
  ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/SKILL.md

# 3. 远端 doc/ 文件已推
curl -sIL "https://github.com/erikgqp8645/zhongyishijia-skill/blob/main/doc/<方剂>历代注解.md" 2>&1 | head -3

# 4. 远端 raw 内容大小匹配
REMOTE_BYTES=$(curl -sL "https://raw.githubusercontent.com/erikgqp8645/zhongyishijia-skill/main/doc/<方剂>历代注解.md" | wc -c)
LOCAL_BYTES=$(wc -c < ~/.hermes/skills/zhongyishijia-expert-mentor-lineage/references/<formula>_literary_history.md)
[ "$REMOTE_BYTES" = "$LOCAL_BYTES" ] && echo "✅ bytes match: $REMOTE_BYTES"
```

## 一句话核心心法

**方剂专题固化 = 8 步流水线（query_formula.py → zysjllsj TypeID 反查 → 整理结构 → 本地 + GitHub 双端同步 → 验证）。最危险的不是数据，是 git 工作区状态：浅 clone 中断、shell pwd 卡死、LFS pointer 干扰、远端 SKILL.md 框架不同——4 个陷阱都要用 explicit 单文件 `git add` + 备份 md5 + mixed reset 兜底，绝不 `git add -A` 或 `git reset --hard`。**
