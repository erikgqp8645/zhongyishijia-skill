# 中医方剂引用原文 5 大铁律

> **核心心法**：引用中医古籍原文 = **「不编造 + 不删减 + 可溯源」**。这是 zhongyishijia-skill 整个项目愿景的**执行层铁律**（参见根级 CLAUDE.md §"项目愿景"）。
>
> 适用范围：所有 `references/*.md` 专题文档的「处方」「本草溯源」「临床应用」等章节，**所有引用块 `「...」` 内部**。

---

## 铁律 1：原文「不带省略号」

**Erik 硬性偏好**（2026-08-17 反复强调，tanpi v3.2 + wenyao 实战验证）：

> 「我需要不带省略号」「这里依然存在好多省略号，这是我不想看到的」

**具体规则**：

| 形式 | 含义 | 处理 |
|------|------|------|
| `「...原文内容...」` | **引用原文有省略** | **必须用 SQL 拿到完整原文，展开替换** |
| `「...（共 8 条）` | **占位符** | 保留（不是引用省略号）|
| `中文「……」` | 中文省略号 | 同上：真原文用 SQL 展开，占位符保留 |
| `英文「...」` | 英文 3 点 | 同上 |

**反面案例**（绝对禁止）：

```python
# ❌ 错误做法 1：用「，...」概括（仍含省略号）
new_string = '「风痹身体皆痛...**呕逆痰癖**...」'  # 仍含 ...！

# ❌ 错误做法 2：自行编造内容
new_string = '「风痹身体皆痛，**呕逆痰癖**」'  # 不是原文！

# ❌ 错误做法 3：批量正则替换（误伤）
re.sub(r'\.{3,}', '', content)  # 会破坏占位符和正常标点！

# ❌ 错误做法 4：用「……」概括
new_string = '「……治风痒鼻塞……」'  # 占位符但语义模糊
```

**正面 SOP**（5 步）：

```python
# 1. 量化诊断
import re
md = open('references/<topic>.md').read()
verbs_zh, verbs_en = '……', r'\.{3,}'
print(f"中文省略号: {md.count(verbs_zh)}, 英文省略号: {len(re.findall(verbs_en, md))}")

# 2. SQL 批量取原文
import sqlite3
conn = sqlite3.connect('references/external/zysj.db')
def dec_llsj(v):  # zysjllsj = UTF-8
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v
ids = set(re.findall(r'ID=(\d+)', md))
content_map = {iid: dec_llsj(conn.execute("SELECT NeiRong FROM zysjllsj WHERE ID=?", (iid,)).fetchone()[0]) for iid in ids}

# 3. 手工展开（精确 patch，每条单独）
# 4. 行末重复检测（关键陷阱：patch 末尾截断 → 内容重复拼接）
# 5. 最终验证（引用块内省略号必须为 0）
```

**实战数据**（tanpi 文档 v3.2）：
- 引用省略号：79 → **0**
- 替换原文条目：35 条
- 文档增长：80KB → 90KB（+12.5%）

---

## 铁律 2：SQLite 双编码修复

**核心发现**（`scripts/_sqlite_utils.py` 已固化）：

| 表 | 编码 | 修复 |
|---|------|------|
| `zysjyj`（方剂）| **GBK** | `dec_yj(v) = v.decode('gbk', errors='replace')` |
| `zysjllsj`（临床理论）| **UTF-8** | `dec_llsj(v) = v.decode('utf-8', errors='replace')` |
| `zysjzhsj`（综合）| 待测试 | `dec_zhsj(v) = v.decode('utf-8', errors='replace')` |
| `zysjcell`（细胞）| 待测试 | `dec_cell(v) = v.decode('utf-8', errors='replace')` |

**绝对禁止**：

```python
# ❌ 一刀切（最常见错误）
conn = sqlite3.connect('references/external/zysj.db')
conn.text_factory = lambda b: b.decode('gbk', errors='replace')  # 只对 zysjyj 正确！

# 后果：zysjllsj 全部乱码
# 现象：输出「缁撻槾澶т究琛」之类（GBK 字节被 utf-8 解）
# 现象：输出「涓鏍囩ず」之类（双解码）
```

**正确做法**：

```python
# ✅ 不设 text_factory，按字段手解码
conn = sqlite3.connect('references/external/zysj.db')

def dec_yj(v):  # zysjyj
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v

def dec_llsj(v):  # zysjllsj
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

cur = conn.execute("SELECT MingCheng, ChuFang, GongNengZZ FROM zysjyj WHERE ...")
for r in cur:
    name = dec_yj(r[0])
    cf = dec_yj(r[1])  # 每个字段单独解码
    gz = dec_yj(r[2])
```

**诊断方法**（如果出现乱码，立刻识别）：

| 现象 | 原因 | 修复 |
|------|------|------|
| `缁撻槾澶т究琛` | GBK bytes 被 utf-8 解 | 换 GBK |
| `鍏跺畠鍏锋湁` | UTF-8 bytes 被 GBK 解 | 换 UTF-8 |
| `涓鏍囩ず` | 双解码（GBK→str→GBK→str）| 按字段手解 |

---

## 铁律 3：不删减讲师/原文内容

**项目愿景原则**（根级 CLAUDE.md）：

> **不编造** — 所有回答都可追溯到具体古籍 / 方剂 / 条文

**Erik 反复强调**（memory 已固化）：

> 「校对后字数必须 >= 原始字数，绝不允许删减讲师内容」

**操作规则**：

| 场景 | 错误做法 | 正确做法 |
|------|---------|---------|
| 原文 100 字 | 「**精简为 30 字**」 | **保留 100 字**，可加**加粗重点**或**分段排版** |
| 原文有 5 条 | 「**只列 2 条**」 | **保留 5 条**，可按朝代/功效**分类展示** |
| 原文方剂组成 | 「**只写君药**」 | **保留全部组成**（含剂量） |
| 古文/繁体 | 「**译为简体即可**」 | **保留原文（繁体）+ 简体译注** |

---

## 铁律 4：可溯源（每条引用必有 chunk_id）

**项目愿景原则**（根级 CLAUDE.md）：

> **能溯源** — 每张 evidence card 引用具体《伤寒论》《本草纲目》等古籍

**操作规则**：

| 引用类型 | 必须包含 | 示例 |
|---------|---------|------|
| **方剂引用** | `（方名）` + `（朝代/出处）` + ID 锚点 | 「**千金紫丸**（唐·孙思邈，TypeID=221，ID=993131）」 |
| **本草引用** | `（药名）` + `（本经/别录/纲目等）` + ID 锚点 | 「**鹅不食草**（《本草拾遗》，ID=575）」 |
| **条文引用** | `（经典名）` + `（卷数/篇名）` + ID 锚点 | 「**《伤寒论·辨太阳病脉证并治中篇》**（ID=188843）」 |
| **医家引用** | `（医家）` + `（著作/朝代）` + ID 锚点 | 「**朱丹溪**《丹溪心法》（金元）」 |

**反面案例**：

```markdown
# ❌ 模糊引用（无法溯源）
- 「张景岳论痰」
- 「《本草纲目》记载...」
- 「某医家认为...」

# ✅ 精确引用（可溯源）
- 「张景岳《景岳全书》卷十九：「痰之本……」（ID=14302）」
- 「《本草纲目》卷二十二：「鹅不食草，微辛，性温……」（TypeID=575）」
- 「李东垣《脾胃论·脾胃虚则九窍不通论》（金元）」
```

---

## 铁律 5：朝代溯源按可查证据分级

**可信度等级**（按 SKILL.md `references/source_map.py` 已有 53 条 SOURCE_MAP + 29 条 TYPEID_MAP）：

| 等级 | 溯源方式 | 适用 |
|------|---------|------|
| **A 级（高可信）** | SOURCE_MAP 命中（key in source_ref / title / summary）| 17.2% 命中率 |
| **B 级（中可信）** | TYPEID_MAP 命中（`re.search(r"TypeID=(\d+)", source_ref)`）| 中等 |
| **C 级（低可信）** | SQLite 字段 `ChuChu` 直接解析 | 较低 |
| **D 级（待考）** | 标记为「待考」 | 不可用，禁用 |

**操作规则**：

```python
import re

# 1. SOURCE_MAP 优先
def identify_source(source_ref):
    for k, v in SOURCE_MAP.items():
        if k in source_ref:
            return v  # A 级
    # 2. TYPEID_MAP
    m = re.search(r"TypeID=(\d+)", source_ref)
    if m and int(m.group(1)) in TYPEID_MAP:
        return TYPEID_MAP[int(m.group(1))]  # B 级
    # 3. SQLite 字段
    return "待考"  # C/D 级
```

**绝对禁止**：

- ❌ 在没有 SOURCE_MAP 命中时**编造朝代/作者**
- ❌ 把 `source_ref` 当朝代直接用（17.2% 命中率）
- ❌ 训练记忆生成的朝代（必须查数据库）

---

## 5 大铁律应用清单

每次写 `references/<topic>.md` 之前，对照检查：

- [ ] **铁律 1（省略号）**：grep `…\|...` 看有没有引用块的省略号
- [ ] **铁律 2（编码）**：用 `dec_yj` / `dec_llsj` 分表解码（不要 text_factory）
- [ ] **铁律 3（不删减）**：原文 ≥ 数据库原文（可分段可加粗，但不删字）
- [ ] **铁律 4（可溯源）**：每条引用都带 `（方名+朝代+ID）` 锚点
- [ ] **铁律 5（朝代）**：用 SOURCE_MAP / TYPEID_MAP 查，不编造

---

## 与本 skill 已有资产的关系

| 资产 | 关系 |
|------|------|
| 根级 `CLAUDE.md` §"项目愿景" | 「不编造」「能溯源」原则的源 |
| `references/distillation_workflow.md` § 2.3 | 「消除引用省略号（铁律）」详细 SOP（5 步+反面案例+补丁代码）|
| `references/wenyao_query_workflow.md` | 头注引用本文（专题查询版铁律）|
| `references/known_pitfalls.md` | 10 大 Python/Regex/SQL 陷阱（编码已含）|
| `scripts/_sqlite_utils.py` | `dec_yj` / `dec_llsj` 函数实现（铁律 2 落地）|
| `references/source_map.py` | 53 条 SOURCE_MAP（铁律 5 落地）|

---

## 实战验证案例

| 案例 | 文档 | 铁律应用 |
|------|------|---------|
| 2026-08-17 tanpi 文档 v3.2 | `tanpi_zhibian_yanshuo.md` | 5 大铁律全部应用，79 处省略号展开为完整原文 |
| 2026-08-17 wenyao 大全 | `wenyao_bixi_daquan.md` | 115 张方剂全部用 SQL 原文溯源，3 张鼻烟壶配方可溯源 |
| 2026-08-17 yantong 专题 | `yantong_literary_history.md` | 24 条证据全部带 ID 锚点 |

---

## 变更记录

### v1.0 (2026-08-17) — 首次固化

- **整合 5 大铁律**：
  1. 原文「不带省略号」Erik 硬性偏好
  2. SQLite 双编码（zysjyj=GBK vs zysjllsj=UTF-8）
  3. 不删减讲师/原文内容
  4. 可溯源（每条引用必有 chunk_id）
  5. 朝代溯源按可查证据分级
- **来源**：
  - tanpi v3.2 实战（79 处省略号展开）
  - wenyao 大全实战（115 张方剂全库溯源）
  - distillation_workflow.md v1.2 SOP
- **触发词**：「中医方剂」「引用原文」「省略号」「溯源」「朝代」「编码」
