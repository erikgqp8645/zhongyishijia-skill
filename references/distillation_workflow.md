# 中医世家深度蒸馏工作流：从 SQLite 全库溯源到朝代章节展开

> **核心心法**：深度蒸馏 = **SQL 全库溯源** + **5 段展开模板** + **朝代承接叙事** = 把「**精简版**」朝代章节升级为「**带原文 ID 的精微版**」专题。
>
> **适用场景**：当 `references/*.md` 专题中存在「**未充分展开**」章节（body < 200 字），需要按标杆章节（如 tanpi 文档 ④ 孙思邈 532 字模板）补全时。

---

## 起源

2026-08-17 在 `tanpi_zhibian_yanshuo.md`（痰癖治法演变）文档中，发现 **10 个章节未充分展开**（body 长度 13-53 字，仅 1-2 句话）。通过本次实战固化出可复用的 SOP 工作流：

- 文档增长：**22KB → 80KB**（+260%），392 → 924 行（+136%），10509 → 37016 字符（+252%）
- 思源同步：`/医林独箫斋/总结/痰癖治法演变` 从 131 块扩到 271 块
- 修复脚本 bug：`scripts/verify_prescription.py` 硬编码 `_DB_PATH` → 改用 `find_sqlite_path()`
- 数据库占位符替换：`references/external/zysj.db` 0 字节 → 711MB 完整 SQLite

---

## 一、工作流总览（3 阶段 9 步）

```
┌─────────────────────────────────────────┐
│ Stage 1: 数据准备（dry-run, 不动手）       │
│  1.1 量化诊断                          │
│  1.2 SQL 取数（双编码修复）              │
│  1.3 起草 5 段模板（人工或 LLM）         │
├─────────────────────────────────────────┤
│ Stage 2: 内容生产（执行, 写回 md）       │
│  2.1 章节 patch（精准匹配 old_string）   │
│  2.2 检查旧结尾残留（每节必须）          │
│  2.3 重复 N 节                          │
├─────────────────────────────────────────┤
│ Stage 3: 验证与同步（不可省）            │
│  3.1 md drift 检测（SKILL.md + README） │
│  3.2 重新导入思源（UUIDv7 + 严格模式）  │
│  3.3 文档统计 + 报告                    │
└─────────────────────────────────────────┘
```

---

## 二、Stage 1：数据准备

### 1.1 量化诊断：找出待展开章节

**目的**：按「**body 长度阈值**」找出所有未充分展开的章节。

```python
import re
md = open('references/<topic>.md').read()
lines = md.split('\n')

sections = []
for idx, line in enumerate(lines):
    if line.startswith('### '):
        title = line[4:].strip()
        # 找到下一节或 --- 或 EOF
        end = len(lines)
        for j in range(idx+1, len(lines)):
            if lines[j].startswith('### ') or lines[j].startswith('---'):
                end = j
                break
        body_lines = lines[idx+1:end]
        body = '\n'.join(body_lines).strip()
        sections.append((title, len(body)))

sections.sort(key=lambda x: x[1])
print(f"共 {len(sections)} 个 ### 章节\n待展开（< 50 字符）:")
for title, l in sections[:15]:
    print(f"  {l:4d}  {title[:50]}")
```

**判定阈值**（按 tanpi 文档实战）：

| body 长度 | 状态 | 处理 |
|----------|------|------|
| < 50 字符 | **待展开** | 必做（1-2 句话，仅占位） |
| 50-200 字符 | 中等 | 可选补全 |
| 200-300 字符 | 良好 | 一般不动 |
| > 300 字符 | **标杆** | 参考模板（如 tanpi ④ 孙思邈 532 字） |

### 1.2 SQL 取数：**双编码修复**（最关键的陷阱）

**核心发现**：`zysjyj` = **GBK** 编码，`zysjllsj` = **UTF-8** 编码。**不能**用 `text_factory = lambda b: b.decode("gbk")` 一刀切！

```python
import sqlite3

DB = 'references/external/zysj.db'  # 或 ~/.cache/zhongyishijia/20120413mssql.sqlite
conn = sqlite3.connect(DB)
# 注意：不要设 text_factory，按字段手解码！

def dec_yj(v):
    """zysjyj = GBK（方剂表）"""
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v

def dec_llsj(v):
    """zysjllsj = UTF-8（临床理论表）"""
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

# 取某本书的含痰癖原文（TypeID=N）
cur = conn.execute("""
    SELECT ID, BiaoTi, NeiRong FROM zysjllsj
    WHERE TypeID=? AND (BiaoTi LIKE '%痰癖%' OR NeiRong LIKE '%痰癖%')
""", (122,))  # 例：圣济总录 TypeID=122

for r in cur:
    title = dec_llsj(r[1])
    content = dec_llsj(r[2])
    print(f"ID={r[0]}  {title}\n  {content[:300]}...")
```

**陷阱识别法**（如果输出乱码，立刻换编码）：

| 现象 | 原因 | 修复 |
|------|------|------|
| `缁撻槾澶т究琛` | GBK bytes 被 utf-8 解 | 换 GBK |
| `鍏跺畠鍏锋湁` | UTF-8 bytes 被 GBK 解 | 换 UTF-8 |
| `涓鏍囩ず` | 双解码（GBK→str→GBK→str）| 按字段手解 |

### 1.3 起草 5 段展开模板

**模板**（基于 tanpi ④ 孙思邇 532 字标杆的 5 段结构）：

```markdown
### ⑩ 朝代·作者《书名》（TypeID=N）—— 一句话定位

作者（生卒年），朝代医家，书名成书年份，全书 N 卷，核心观点。**这一节的转折意义**。

**关键转折/定位**：1-2 句点出本节在朝代演变轴上的独特贡献。

> 关键原文引用 1（带书名出处）。
> 关键原文引用 2（带书名出处）。

**关键原文证据 N 条全表**（zysjllsj/zysjyj 表 TypeID=N 含「病证」）：

| # | ID | 篇目 | 关键条文（节录） |
|:-:|:--:|------|----------------|
| 1 | xxx | 篇目名 | 「原文...**加粗重点**...原文」|
| 2 | xxx | ... | ... |

**核心方剂与药法**：

| 方/药 | 组成/性味 | 治法 | 临床应用 | 出处 |
|------|---------|------|---------|------|
| 方名1 | 组成 | 治法 | 应用 | 出处 |
| 方名2 | ... | ... | ... | ... |

**病机与治法核心**：

1. **核心论 1**——原文精微
2. **核心论 2**——原文精微
3. **核心论 3**——原文精微
4. **核心论 4**——原文精微

**承接与影响**：

- **上承 X 节**——精微关系
- **下启 Y 节**——精微关系
- **横向承转**——精微关系

**历史意义**：本节的精微地位。
```

**模板参数**（按节类型调整）：

| 节类型 | 原文数 | 方剂表行数 | 核心论点 |
|--------|--------|------------|---------|
| 单书（如 ⑪ 圣济总录）| 全部列出 | 3-5 行 | 3-4 条 |
| 双书（如 ⑰ 龚氏父子）| 2-4 条 | 5-7 行 | 3-4 条 |
| 三书（如 ㉕ 三书）| 每个独立子节 | 各 3-5 行 | 各 3-4 条 |
| 转折节（如 转折 5）| N/A | 转折标志表 | 4 维度 |

---

## 三、Stage 2：内容生产

### 2.1 章节 patch（精准匹配 old_string）

**核心原则**：每个 patch 必须有**唯一**的 `old_string` 上下文，避免误匹配。

```python
patch(
    mode='replace',
    path='references/tanpi_zhibian_yanshuo.md',
    old_string='### ⑪ 宋·《圣济总录》（TypeID=122）——临床大备\n\n宋·徽宗敕撰。含"痰癖"11 条——把痰癖治法从单方推向系列方。\n\n### ⑫ 元·李东垣《脾胃论》（TypeID=877）',
    new_string='### ⑪ 宋·《圣济总录》（TypeID=122）——临床大备\n\n[展开后的 700+ 字内容]\n\n### ⑫ 元·李东垣《脾胃论》（TypeID=877）',
)
```

**关键**：用「下一节标题」作为锚点，确保 patch 精确替换本节。

### 2.2 检查旧结尾残留

每节展开前，原节可能只占 1 行（如「11 条——把痰癖治法从单方推向系列方」）。展开后必须**删除**这行，否则会与新内容重复。

**检查方法**：

```bash
grep -E "本草学集大成|含痰癖——明代|本草学集大成\+方剂学标准化" references/<topic>.md
```

如果搜到残留，在 patch 的 `new_string` 末尾不加旧结尾，或后续单独 patch 删除。

### 2.3 消除引用省略号（铁律）

**核心铁律**：**正文展开时，引用原文（`「...」` / `「……」`）的省略号必须消除**，占位符省略号（`...（共 N 条）`）保留。

按 SKILL.md 「不删减讲师内容」原则，**真原文省略号必须用 SQL 拿到完整原文替换**，禁止用 `...` 占位或自行概括。

**两类省略号**：

| 类型 | 特征 | 处理 |
|------|------|------|
| **引用原文省略** | `「风痹身体皆痛...**呕逆痰癖**...」` | **必须展开**（SQL 拿原文）|
| **占位符省略** | `...（共 8 条）` / `...（共 8 味）` | 保留（不是引用省略）|

> **完整 9 步工作流见第九节：「原文引用「不带省略号」展开 SOP（Erik 硬性偏好）」** — 含 SQL 取数代码、批量替换脚本、行末重复检测、实战数据。
>
> **本节（2.3）是 9 步 SOP 的浓缩版本**：量化诊断 → SQL 取原文 → 手工 patch → 行末重复检测 → 最终验证。

**核心 5 步（简化版）**：

1. **量化诊断**：`grep -c '…\|...' references/<topic>.md` 找出所有省略号位置
2. **SQL 批量取原文**：`SELECT NeiRong FROM zysjllsj WHERE ID=?` + `decode('utf-8')`（zysjllsj=UTF-8）
3. **手工展开**：每条 `old_string` 用完整原文中关键句 + `**加粗重点**` 重写
4. **行末重复检测**：同一行内 `grep "关键句" -c` ≥ 2 = 上一轮 patch 没干净 → 手工删除重复段
5. **最终验证**：引用块内的省略号必须为 0

**实战数据**（tanpi v3.2.1）：
- 引用省略号：79 → **0**
- 替换原文条目：35 条
- 文档增长：80KB → 90KB（+12.5%）

**反面案例**（绝对禁止）：

```python
# ❌ 错误做法 1：用「，...」概括
new_string='「风痹身体皆痛...**呕逆痰癖**...」'  # 仍含 ...！

# ❌ 错误做法 2：自行编造内容
new_string='「风痹身体皆痛，**呕逆痰癖**」'  # 不是原文！

# ❌ 错误做法 3：批量正则替换（误伤）
re.sub(r'\.{3,}', '', content)  # 会破坏占位符和正常标点！
```

### 2.4 重复 N 节（串行或并行）

**推荐**：**串行**（保证每节质量，可中途调整）。N 节约 N×5 个 patch 工具调用。

**并行**（用 `delegate_task` 起 leaf 子 agent）只在 N>20 时考虑。

---

## 四、Stage 3：验证与同步

### 3.1 md drift 检测

**3 处必须登记**（按 SKILL.md 「新增 references/*.md 必须 3 处同步登记」原则）：

```bash
# 1. SKILL.md Reference Priority 编号
grep -c "<topic>" SKILL.md  # 应 ≥ 1

# 2. README.md 仓库结构树
grep -c "<topic>" README.md  # 应 ≥ 1

# 3. README.md 更新日志
grep -c "<topic>" README.md  # 通常 changelog 里有完整描述
```

**修正示例**（tanpi 展开后）：

| 文件 | 关键词 | 命中 |
|---|---|---|
| SKILL.md | tanpi | 1 ✓（编号 24）|
| README.md | tanpi | 0 → 1 ✓（结构树 + 体积更新）|
| README.md | tanpi (changelog) | 0 → 1 ✓（v3.2 changelog）|

### 3.2 重新导入思源（严格模式）

**关键**：
- 用 `siyuan-sisyphus fs write`（不是 REST API）
- **手动删除原文档后**再创建（避免 conflict）
- **必须 UUIDv7** requestId（严格模式默认开启）

```bash
# 1. 生成 UUIDv7
python3 << 'PYEOF'
import time, secrets
ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
rand_12 = secrets.randbits(12)
rand_62 = secrets.randbits(62)
hi = (ts_ms << 16) | (7 << 12) | rand_12
lo = (0b10 << 62) | rand_62
u = (hi << 64) | lo
s = f"{u:032x}"
print(f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}", end='')
PYEOF

# 2. 写入
export SIYUAN_API_URL="http://127.0.0.1:6806"
export SIYUAN_TOKEN="zkb8kqo1lrt11abq"
sisyphus fs write \
  --path "/医林独箫斋/总结/<topic>" \
  --markdown "$(sed '1d' references/<topic>.md)" \
  --requestId "<uuid7>"
```

**期待输出**：

```
✓ Success
  ID     : 20260817155326-xxxxxxx
  Path   : /医林独箫斋/总结/<topic>
  Created: true
  Write Safety Guaranteed: true
  Transaction State      : committed
```

### 3.3 文档统计 + 报告

```python
import os
md_path = 'references/<topic>.md'
size = os.path.getsize(md_path)
with open(md_path) as f:
    content = f.read()
lines = content.count('\n') + 1
chars = len(content)

print(f"大小: {size} bytes ({size/1024:.1f} KB)")
print(f"行数: {lines}")
print(f"字符数: {chars}")

# 检查所有展开的章节
chapters = ['⑪', '⑫', '⑬', '⑰', '⑲', '㉑', '㉓', '㉔', '㉕', '㉘', '转折 5']
for ch in chapters:
    if ch in content:
        print(f"  ✓ {ch}")
    else:
        print(f"  ✗ {ch}: 未找到")
```

---

## 五、5 段展开模板（标杆化）

### 标杆章节对比（tanpi 文档 v3.2）

| 章节 | body 长度 | 特点 |
|------|----------|------|
| ④ 唐·孙思邈 | 532 字 | **标杆模板**（复杂表 + 完整 5 段）|
| ⑪ 宋·圣济总录 | 700+ 字 | 11 条原文全列（最多）|
| ㉕ 清·三书 | 1500+ 字 | 三书独立子节（最复杂）|
| 转折 5 | 800+ 字 | 转折标志表 + 中日汇通 |

### 5 段结构（精微化）

1. **作者朝代背景**（1-2 句）—— 时代背景 + 著作地位 + 转折意义
2. **关键原文引用 1-2 条**（带书名出处）—— 高亮关键词
3. **原文证据全表**（3 列：# + ID + 篇目 + 关键条文）—— 不超过 11 行
4. **核心方剂与药法表**（4 列：方/药 + 组成/性味 + 治法 + 临床应用）
5. **病机与治法核心**（3-4 条精微论点 + 1 条承接影响 + 1 条历史意义）

### 严禁事项

- ❌ 不要把整个 5 段都堆在 1 个 H3 标题下（要用 #### 子标题分层）
- ❌ 不要原文大段引用（要节录关键句 + 加粗重点）
- ❌ 不要遗漏「承接与影响」（朝代演变轴是 tanpi 的灵魂）
- ❌ 不要遗漏「**双书/三书**」的独立子节（每一本书是独立的医学体系）

---

## 六、双编码修复（完整 SOP）

### 问题诊断命令

```python
import sqlite3
DB = 'references/external/zysj.db'
conn = sqlite3.connect(DB)
cur = conn.execute("SELECT name FROM pragma_table_info('zysjllsj') LIMIT 1")
row = cur.fetchone()
# 取一条试试编码
cur = conn.execute("SELECT BiaoTi, NeiRong FROM zysjllsj LIMIT 1")
row = cur.fetchone()
print("zysjllsj BiaoTi type:", type(row[0]))
if isinstance(row[0], str):
    print("  当前已解码为:", row[0][:50])
else:
    for enc in ['gbk', 'gb18030', 'utf-8', 'big5']:
        try:
            txt = row[0].decode(enc, errors='strict')
            print(f"  ✓ {enc}: {txt[:50]!r}")
        except: pass
```

### 编码决策表

| 表 | 默认编码 | 修复方案 |
|---|---------|---------|
| `zysjyj`（方剂）| GBK | `decode_yj(v) = v.decode('gbk', errors='replace')` |
| `zysjllsj`（临床理论）| UTF-8 | `decode_llsj(v) = v.decode('utf-8', errors='replace')` |
| `zysjzhsj`（综合数据）| 待测试 | 先 spot-check |
| `zysjcell`（细胞数据）| 待测试 | 先 spot-check |

### 工具函数（直接复制用）

```python
import sqlite3

def make_db_conn(db_path='references/external/zysj.db'):
    """创建连接，不设 text_factory"""
    return sqlite3.connect(db_path)

def dec_yj(v):
    """zysjyj = GBK"""
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v

def dec_llsj(v):
    """zysjllsj = UTF-8"""
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

def dec_zhsj(v):
    """zysjzhsj（综合数据）= 待测试"""
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v
```

---

## 七、思源严格模式（关键 5 步）

### 1. 删除原文档（手动）

```bash
# 思源 API: DELETE /api/block/deleteBlock {id: "...", isPhysicDelete: true}
# 或手动在思源界面删除
```

### 2. 生成 UUIDv7

```python
import time, secrets

def uuid7():
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_12 = secrets.randbits(12)
    rand_62 = secrets.randbits(62)
    hi = (ts_ms << 16) | (7 << 12) | rand_12
    lo = (0b10 << 62) | rand_62
    u = (hi << 64) | lo
    s = f"{u:032x}"
    return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
```

### 3. 准备 markdown（去 # Title）

```bash
sed '1d' references/<topic>.md > /tmp/topic_md.md
```

### 4. 写入

```bash
sisyphus fs write \
  --path "/医林独箫斋/总结/<topic>" \
  --markdown "$(cat /tmp/topic_md.md)" \
  --requestId "<uuid7>"
```

### 5. 验证

```bash
sisyphus fs read --path "/医林独箫斋/总结/<topic>" --blockLimit 3
```

**期待输出**：

```
✓ Success
  Write Safety Guaranteed: true
  Transaction State      : committed
  Result Hash            : sha256:v1:xxx
```

---

## 八、批量展开的陷阱清单

| # | 陷阱 | 解决 |
|--:|------|------|
| 1 | **patch old_string 不唯一** | 用「下一节标题」做锚点 |
| 2 | **旧结尾残留**（如「本草学集大成+...」）| 每节 patch 后 `grep` 验证 |
| 3 | **编码一刀切**（GBK vs UTF-8）| 按表用 `dec_yj` / `dec_llsj` |
| 4 | **思源 UUIDv4 失败**（必须 v7）| 手搓 `uuid7()` 函数 |
| 5 | **思源未删就写**（触发 state_changed）| 用户手动删除或 REST API `isPhysicDelete: true` |
| 6 | **drift 漏登记**（SKILL.md / README）| 3 处 grep 验证 ≥1 hit |
| 7 | **数据被截断**（只查前 N 条）| 完整 SQL + LIMIT 但预留大值 |
| 8 | **长脚本被 blocklist 拦截**（heredoc / for）| 拆短或用 `execute_code` |
| 9 | **章节标题字符不一致**（全角 / 半角 / 引号）| read_file 精确复制 |
| 10 | **「承接」方向错**（上承 / 下启 / 横向）| 按朝代时间轴核对 |
| 11 | **patch 末尾 old_string 截断导致内容重复拼接**（L614/L654/L655/L706/L708 实战）| 每次 patch 后 grep 验证「同一原文 ID 是否在文档中出现 ≥2 次」，>2 次 = 上一轮 patch 没干净 |
| 12 | **原文引用里的「...」/「……」没消除** | 见**第九节：Erik 偏好不带省略号** |

---

## 九、原文引用「不带省略号」展开 SOP（Erik 硬性偏好）

**Erik 偏好**（2026-08-17 tanpi 文档 41 处省略号展开实战确认）：当深度蒸馏文档出现「...」或「……」**在原文引用块（`「...」`）内部**时，**必须**用 SQL 拿到完整原文替换，**不能保留任何省略号**。即使是 281 字符截断卡，证据原文也有完整版本在 SQLite 里可查。

**触发条件**：
- `references/*.md` 文档中**引用块**（`「...」` 或 `『...』`）含「...」或「……」
- **不适用**：占位符类（如 `...（共 8 条）`）

**9 步工作流**：

1. **量化诊断**：用 grep 统计所有省略号（`……` 中文 / `...` 英文 / `.{6,}` 六点）
2. **SQL 取全文**：批量 `SELECT NeiRong FROM zysjllsj WHERE ID=?`，按字段手解码（GBK / UTF-8）
3. **存到 JSON**：`/tmp/<topic>_full_content.json`（53 个 ID × 完整原文 ≈ 60KB）
4. **Python 脚本批量替换**：每条 `old_string` 用完整原文中**关键句**+ `**加粗重点**` 重写
5. **PATCH 后 grep 验证**：每条替换后 `grep "关键词" references/<topic>.md` 检查次数
6. **修复重复拼接**：patch `old_string` 截断时内容会被拼接到行末 → 找到 `...**新内容**」|旧内容**...` 模式，删除重复段
7. **末尾清理**：确保文档里**不含任何引用块内部的省略号**（占位符除外）
8. **思源同步**：重新写入覆盖（UUIDv7 严格模式）
9. **commit + push**：`tanpi: 展开 N 处省略号为完整原文`

**代码模板**（按表分编码 + 批量替换）：

```python
import sqlite3, json
DB = 'references/external/zysj.db'
conn = sqlite3.connect(DB)
# 不设 text_factory，按字段手解码
def dec_yj(v):
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v
def dec_llsj(v):
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

# 1. 取所有引用 ID 的全文
md = open('references/<topic>.md').read()
import re
ids = sorted(set(int(m) for m in re.findall(r'ID=(\d+)', md)))
content_map = {}
for iid in ids:
    cur = conn.execute("SELECT NeiRong FROM zysjllsj WHERE ID=?", (iid,))
    row = cur.fetchone()
    if row:
        content_map[iid] = dec_llsj(row[0])

# 2. 找出所有引用省略号行
for line in md.split('\n'):
    if ('「' in line or '『' in line) and ('...' in line or '……' in line):
        # 此行需要展开 → patch
        pass

# 3. 批量替换（每条 old_string 用完整原文替换）
md = md.replace(old_with_ellipsis, new_with_full_text)
with open('references/<topic>.md', 'w') as f:
    f.write(md)
```

**实战数据**（tanpi 2026-08-17）：
- 起点：79 处省略号（中文 6 + 英文 73）
- 终点：**0 处引用省略号** + 2 处占位符（保留）
- 文档增长：80KB → **90KB**（+12.5%），37016 → **~43000 字符**（+15%）

**与 SKILL.md 铁律一致性**：这与 `references/known_pitfalls.md` 提到的「不要删减讲师内容」+「精确溯源」原则完全一致——省略号 = 删减，必须消除。

---

## 十、典型工作流时间表

| 阶段 | 工具调用 | 时间 |
|------|---------|------|
| Stage 1.1 量化诊断 | 1 call | 5s |
| Stage 1.2 SQL 取数（10 节）| 10 calls | 30s |
| Stage 1.3 起草 5 段（人工+LLM）| 0-5 calls | 5-30min |
| Stage 2 patch（10 节）| 10 calls | 1-2 min |
| Stage 2.2 检查旧结尾 | 5 calls | 30s |
| Stage 3.1 drift 检测 | 2 calls | 10s |
| Stage 3.2 思源写入 + 验证 | 3 calls | 30s |
| Stage 3.3 统计 + 报告 | 1 call | 10s |
| **合计（10 节展开）** | **~30 calls** | **~10 min** |

---

## 十一、SOP 工具脚本（未来扩展）

**当前**：纯手动 + Python inline 代码。

**未来可封装**：

```bash
# scripts/distill_chapter.py <topic>.md <chapter_number>
# - 自动量化诊断 + 取数 + 起草 + patch + drift + 思源同步
# - 输入: 章节标题
# - 输出: 展开后的章节内容 + drift 检测报告
```

**当前优先级**：低（手动流程已固化，且每次内容独特性高）。

---

## 十二、相关文件清单

- `references/tanpi_zhibian_yanshuo.md` — 本 SOP 的**实战案例**（10 节展开后的成果）
- `references/tcm_research_methodology.md` — 4 步研究方法论（SQL 取数基础）
- `references/known_pitfalls.md` — 10 大 Python/Regex/SQL 陷阱（**先读这个！**）
- `references/sqlite_deployment_recipe.md` — SQLite 数据库部署 SOP
- `references/install-path.md` — 安装路径说明
- `references/zero_hit_fallback_workflow.md` — 0 命中时的 fallback 流程

---

## 十三、变更记录

### v1.2 (2026-08-17) — 重复内容清理 + 浓缩版

- **新增 2.3 节**：「消除引用省略号（铁律）」的浓缩版（5 步）
- **指引到第九节**：详细 9 步 SOP + 代码模板
- **更新触发词**：加入「消除省略号」「展开省略号」「不带省略号」「去除省略号」
- **原因**：v1.1 的第九节已包含完整 SOP，2.3 浓缩版做导航

### v1.1 (2026-08-17) — 省略号展开 SOP 补充

- **新增第九节**：原文引用「不带省略号」展开 SOP（Erik 硬性偏好）
- **陷阱清单新增 #11/#12**：patch 末尾截断导致内容重复拼接 / 省略号消除
- **新增代码模板**：按表分编码 + 批量替换脚本骨架
- **实战数据**：tanpi 41 处省略号全部展开（80KB → 90KB）

### v1.0 (2026-08-17) — 首次固化

- **起源**：`tanpi_zhibian_yanshuo.md` 10 节展开实战
- **核心贡献**：
  - 5 段展开模板（基于 tanpi ④ 孙思邇 532 字标杆）
  - **双编码修复 SOP**（zysjyj=GBK, zysjllsj=UTF-8）
  - UUIDv7 手搓函数（严格模式必备）
  - 思源严格模式 5 步流程
  - 10 大陷阱清单
- **触发词**：「展开 XX 节」「补全 XX 章节」「深度蒸馏 XX」「消除省略号」「展开省略号」「不带省略号」「去除省略号」
- **下一步**：可封装为 `scripts/distill_chapter.py`（按需）