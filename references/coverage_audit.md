# 知识库覆盖审计参考

## 何时需要审计

当用户问到 **特定古籍/经典** 的具体方剂/条文/医家时，不要直接调 `search_course_notes.py` 就答完。先判断该书在知识库里的覆盖度。覆盖不足时，必须如实告知用户"知识库不完整"并给出补救来源，而不是用模型常识补全伪装成知识库内容。

## 知识库数据源盲点

- 数据源：zysj.com.cn 2012-2014 三个 SQL 表（`zysjyj` 方剂 / `zysjllsj` 临床理论 / `zysjzhsj` 综合医话）+ 678 本古医书 CHM。
- 已收录的代表古籍：伤寒论、金匮要略、本草纲目、黄帝内经、针灸大成、景岳全书、脉经、难经、温病条辨等（CHM 目录里有的）。
- **未收录或极薄** 的代表：敦煌遗书类（辅行诀脏腑用药法要 1988 年才重新面世）、明清以后地方医案、近代医家全集。

## 高效审计方法

**不要**循环跑 `search_course_notes.py` N 次——会超时。改用 `execute_code` 直接流式扫 `references/text_distillation/evidence_cards.jsonl`：

```python
import json
from pathlib import Path

p = Path('<skill_dir>/references/text_distillation/evidence_cards.jsonl')
keywords = ['方剂A','方剂B','方剂C', ...]   # 该书所有核心方名
counts = {k: 0 for k in keywords}

with p.open(encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        try: c = json.loads(line)
        except: continue
        text = ' '.join(str(c.get(k,'') or '') for k in
                       ['card_type','title','summary','quote','source_ref','chunk_id'])
        for kw in keywords:
            if kw in text:
                counts[kw] += 1

for k, v in counts.items():
    print(f"{k:12s}: {v:3d}", "✓" if v > 0 else "✗")
```

## 已审计示例：辅行诀脏腑用药法要

直接命中"辅行诀/辅行决"的 evidence cards 仅 7 张（陶弘景前言 + 张大昌序 + 1988 年马继兴敦煌古医籍考释以来的研究综述）。

按方剂名扫描后，覆盖率约 75%（18/24）：

| 方剂群 | 知识库命中 | 状态 |
|---|---|---|
| 五脏泻方（小泻肝/心/脾/肺/肾汤） | 5/5 | ✓ 完整 |
| 五脏补方（大补肝/心/脾/肺/肾汤） | 5/5 | ✓ 完整（仅大补汤，小补汤多无独立命中） |
| 救诸劳损方（养生补肝/调中补心/建中补脾/宁气补肺/固元补肾汤） | 5/5 | ✓ 完整 |
| 六合正神方 | 4/8 | ⚠ 部分 |
| ├ 阳旦汤（→桂枝汤）| ✓ 31 次 | |
| ├ 阴旦汤 | ✓ 5 次 | |
| ├ 正阳旦汤 | ✓ 3 次 | |
| ├ 小白虎汤（→白虎汤）| ✓ 1 次 | |
| ├ 小朱雀汤（→黄连阿胶汤）| ✗ 0 | |
| ├ 小玄武汤（→真武汤）| ✗ 0 | |
| ├ 小勾陈汤 | ✗ 0 | |
| └ 小螣蛇汤 | ✗ 0 | |

**结论：** 辅行诀原始卷子未进入 zysj 数据库，补全须直接查阅：
- 钱超尘《辅行诀脏腑用药法要校注》（1998/2008）
- 张大昌弟子校订本（卡 `7462af89abcec94c` 引用的 14 个抄本）
- 马继兴《敦煌古医籍考释》（1988）

## 审计应答模板

当用户问"X 经典的所有方剂/条文"时：

1. 先跑上面的扫描脚本，统计覆盖率。
2. 区分"知识库收录"与"通用学术常识"——前者标方名+出处，后者用"（以下为通校本方剂，zysj 未收录）"明示。
3. 列出知识库**未收录**的方剂/条文，提示用户去原书校注本或权威古籍数据库补全。

切勿把通校本/通行方剂列表直接当作 zysj 知识库输出——会违反 skill 规则"区分课程内容与你的推理"。

## ⚠️ jsonl 摘要字段截断陷阱（重要）

`evidence_cards.jsonl` 中每张卡的 `summary` 字段**被硬截断到 ~281 字符**（个别 197 字），这是 lineage 蒸馏流程的固定 chunk 大小，**不是查询脚本的限制**。

**实测对比（辅行诀 TypeID=1247，15 条记录）**：

| 章节 | SQLite 原文 | jsonl summary | 损失 |
|---|---|---|---|
| 前言 | 538 字 | 281 字 | -48% |
| 一 辨肝 | 716 字 | 281 字 | -61% |
| 二 辨心 | 1535 字 | 281 字 | **-82%** |
| 七 救劳损 | 1708 字 | 281 字 | **-84%** |
| 八 二旦六神 | 2546 字 | 281 字 | **-89%** ← 最关键的章节 |
| 九 救中恶 | 849 字 | 281 字 | -67% |
| 张大昌 | 1807 字 | 281 字 | -84% |
| 附录二 版本对比 | 6177 字 | 281 字 | -95% |
| **合计** | **27,798 字** | **3,950 字** | **-86%** |

**含义**：
- 即使 jsonl 里"命中"某条记录，实际能读到的只是该条原文的**前 281 字**——后续方剂组成、加减法、剂量全被切掉。
- 对长篇古医书（辅行诀、伤寒论条文注解、医案全集等）影响极大：表面"覆盖"≠ 实质"可用"。
- `search_course_notes.py` 的输出格式可能掩盖这一点：脚本 print 时按 title+quote 拼接，看起来像完整卡片，但 quote 字段本身就被截过。

**当 jsonl 覆盖度报告 + 用户期望差异大时**，按下面这个三步走验证：

### Step 1：定位 SQLite 源表

```bash
# zysjmssqlbak.sqlite / 20120413mssql.sqlite 都在 Downloads/data/
sqlite3 zysjmssqlbak.sqlite ".tables"
# 输出：zysjcell  zysjllsj  zysjyj  zysjzhsj
```

```sql
-- 看一张表的 schema（字段名是拼音首字母，NeiRong=内容，BiaoTi=标题）
.schema zysjllsj
-- CREATE TABLE zysjllsj ("TypeID" INT, "ID" INT, "BiaoTi" VARCHAR(100), "NeiRong" TEXT, ...)
```

### Step 2：按 TypeID 统计原始字符数

```sql
SELECT COUNT(*) AS n,
       SUM(LENGTH(NeiRong)) AS total_chars,
       MAX(LENGTH(NeiRong)) AS max_chars
FROM zysjllsj WHERE TypeID=1247;
-- 15 | 27798 | 8859   ← 真实原文 27,798 字
```

```sql
-- 对比：看每条的标题 + 字数分布
SELECT ID, BiaoTi, LENGTH(NeiRong) AS len
FROM zysjllsj WHERE TypeID=1247 ORDER BY ID;
```

### Step 3：导出完整原文到 jsonl（一次性方案）

```python
import json, sqlite3
con = sqlite3.connect('/Users/applemima1111/Downloads/data/zysjmssqlbak.sqlite')
rows = con.execute(
    "SELECT ID, BiaoTi, NeiRong FROM zysjllsj WHERE TypeID=1247 ORDER BY ID"
).fetchall()
with open('/tmp/auxingjue_full.jsonl', 'w', encoding='utf-8') as f:
    for rid, title, content in rows:
        f.write(json.dumps({
            "card_id": f"zysjllsj:{rid}",
            "card_type": "clinical_theory",
            "title": title,
            "summary": content,            # 完整原文，不截断
            "source_ref": f"zysjllsj TypeID=1247",
            "chunk_id": f"zysjllsj:{rid}",
        }, ensure_ascii=False) + '\n')
```

把导出的 jsonl 放进 `references/text_distillation/full_sources/` 一类的目录，jsonl 检索时优先查这个完整版。

### Step 4（推荐）：就地接入 SQLite 全文补全 — 架构更优

一次性 jsonl 导出会污染 skill 数据源且重复存储。更干净的方案是把 SQLite 副本放进 skill 自带的 `references/external/`，写一个薄封装 + 让 `query_formula.py` 默认用全文。**已实施于本 skill**：

```
references/
├── text_distillation/evidence_cards.jsonl   # 31.7 万卡索引（不动）
└── external/                                # 新建
    ├── zysj.db                              # 684 MB，SQLite 副本
    └── zysj_index.py                        # ~90 行薄封装
```

**薄封装核心**（`zysj_index.py`，精简版）：

```python
import sqlite3
from pathlib import Path

_DB = Path(__file__).resolve().parent / "zysj.db"
_TEXT_FIELD = {
    "zysjyj":   "ChuFang",
    "zysjllsj": "NeiRong",
    "zysjzhsj": "NeiRong",
    "zysjcell": "Cell_NeiRong",
}

def fetch_full(chunk_id: str):
    """chunk_id 形如 'zysjllsj:195484' → 拉完整原文。"""
    if not chunk_id or ":" not in chunk_id:
        return None
    table, _, id_str = chunk_id.rpartition(":")
    if table not in _TEXT_FIELD:
        return None
    tf = _TEXT_FIELD[table]
    con = sqlite3.connect(_DB)
    row = con.execute(
        f"SELECT {tf} FROM {table} WHERE ID = ? LIMIT 1", (int(id_str),)
    ).fetchone()
    return row[0] if row and row[0] else None
```

**消费侧**（`query_formula.py` 默认开启全文模式）：

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "zysj_index",
    Path(__file__).resolve().parent.parent / "references/external/zysj_index.py",
)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def fetch_full_text(chunk_id):
    full = mod.fetch_full(chunk_id)
    return full if full else None

# main() 输出循环里：
if args.full_text:
    full = fetch_full_text(card.get("chunk_id", ""))
    if full:
        summary = full  # 用 SQLite 全文替换 281 字符截断
```

**为何优于 Step 3**：

| 维度 | 一次性 jsonl 导出 | SQLite 副本 + 薄封装 |
|---|---|---|
| 改动现有 jsonl | ✗ 污染（多一份完整数据） | ✓ 不动 31.7 万卡 |
| 磁盘占用 | 重复存储 1.8 亿字符 | 684 MB 单副本 |
| 跨记录引用 | jsonl 内查找 | SQL 任意维度查询 |
| 章节结构 | 丢失（被切碎到 chunk）| 保留 TypeID/ID 完整性 |
| md 数据源关系 | 与 md 平行无关联 | 可作为 md 的 source-of-truth |

**复制 SQLite 时的两个等价文件**（MD5 GROUP_CONCAT 验证：四个表全部哈希一致，可任选其一）：

- `/Users/applemima1111/Downloads/data/zysjmssqlbak.sqlite`（684 MB，bak 文件）
- `/Users/applemima1111/Downloads/data/20120413mssql.sqlite`（692 MB，原 mssql 备份）

二者表结构、记录数、所有字段哈希 100% 相同，是同一数据库的两个时点快照。**复制进 skill 时选 mssqlbak 版**（通常 bak 更可靠）。验证命令：

```sql
SELECT MD5(GROUP_CONCAT(COALESCE(TypeID,' ')||':'||COALESCE(ID,' ')||':'||COALESCE(NeiRong,MingCheng,Cell_NeiRong,'')||':'||COALESCE(BiaoTi,MingCheng,Cell_BiaoTi,''), '|' ORDER BY TypeID, ID)) FROM <table>;
```

**关键发现**：100% 的 evidence_cards.jsonl 卡 `chunk_id` 形如 `zysjllsj:195484`，可 100% 反查 SQLite。即任何 jsonl 命中都能拉到对应的完整原文，**没有任何信息无法补全**（除了 zysj.com.cn 本身没入库的内容）。

**验证脚本（ad-hoc）** — 跑通 5 项再算交付完成：

```python
# T1: 默认全文模式 → 表格行 >400 字符
subprocess.run(['python3', 'scripts/query_formula.py', '小阳旦汤', '--max-cards', '1'])

# T2: --no-full-text 退回旧行为 → 表格行 ≤400 字符
subprocess.run(['python3', 'scripts/query_formula.py', '小阳旦汤', '--no-full-text'])

# T3: --max-text-len 0 = 不限（修复后的关键边界）→ 表格行 >1000 字符
subprocess.run(['python3', 'scripts/query_formula.py', '小阳旦汤', '--max-text-len', '0'])

# T4: 边界场景
fetch_full_text('')                      # → None
fetch_full_text('bogus:999')             # → None（未知表）
fetch_full_text('zysjllsj:99999999')     # → None（未知 ID）
fetch_full_text('zysjllsj:195484')       # → 2546 字符（辅行诀第八章全文）

# T5: 多记录查询 → 平均行 >400 字符
subprocess.run(['python3', 'scripts/query_formula.py', '白虎加人参汤', '--max-cards', '5'])
```

**常见 bug**：`clean_summary(text, max_len=0)` 时，`if len(text) > max_len` 把 0 当 falsy，会截到 0 字符。**必须**写成 `if max_len > 0 and len(text) > max_len`。

## 本草原文检索（`verify_prescription.py` 的本草章节模式）

本草正条文必须严格按"《X》云∶主Y..."格式匹配——本草章节里混着异名/采收/性味/注释，不严格过滤会全污染。`scripts/verify_prescription.py` 的 `_fetch_bencao` 函数是当前 skill 唯一实现这种严格过滤的入口。

### 本草章节 ID 范围编码（关键约定）

本草章节的 ID 范围承载**来源语义**，未来查询本草会反复用到：

| 章节 ID 范围 | 内容类型 | 特征字段示例 | 检索价值 |
|---|---|---|---|
| `zysjllsj:1xxx`（如 1086 甘草、1103 菟丝子、1083 山药）| 现代中药学 | "【功效】""【临床应用】""【使用注意】" | 现代归类 |
| `zysjllsj:70xxx`-`72xxx`（如 72076 麻黄、72145 苦参、72104 甘草、72064 防风）| **本草原始文献汇编** | "《本草》云∶主X..." 或 "《本经》《别录》《唐本》《蜀本》" | ✓ **本草验证首选** |
| `zysjllsj:89xxx`（如 89012 白术、89059 菊花、89041 细辛）| 各家医家论述 | "（痘疹合参）""（临证指南）" | 临床应用 |
| `zysjllsj:1xxxx`（如 108225 生地黄、115805 竹沥）| 单味药专章 | 古代名医 + 古代本草 | 药物专论 |
| `zysjllsj:133xxx`（如 133652 枳壳、133723 蛇床子）| 历代各家注解 | "本经疏证""证类本草" | 关键本草考证 |

**headless 模式**：章节开头没有"《X》云"字样、整段就是本经原文的章节。`_fetch_bencao` 按 ID 范围自动推断来源标签：

```python
if 70000 <= id_ < 80000: src = "本草经集注"  # 古代本草原始
elif 1 <= id_ < 10000: src = "本草(现代)"   # 现代中药学
else: src = "本草(原文)"  # 其他
```

### 主条文正则（关键 bug 修复经验）

本草正条文必须满足"主"字开头 + 贪婪到下一个《X》引用标记。两种错误实现 vs 正确实现：

```python
# 错误 1: 截到第一个句号 → 漏掉"破癥坚积聚"等多句连用
re.compile(r"《本草》\s*云\s*[∶:]?\s*主\s*([^。；\n]{10,300}?)(?=[。；\n]|$)")
# 只匹配到"中风伤寒头痛，温疟，发表出汗，去邪热气"就停

# 错误 2: 宽松匹配 → 把异名/采收/性味/注释都误当主治
re.compile(r"《本草》\s*云\s*([^。；\n]+)")
# "云∶叉头者，令人发狂"（防风采收注）会被误当主治
# "云∶一名铜芸..."（异名）会被误当主治
# "云∶味苦、辛..."（性味）会被误当主治

# 正确: 贪婪到下一个《X》引用标记 + 要求"主"字开头
re.compile(r"《本草》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL)
# 完整保留 "主中风伤寒头痛...破症坚积聚" 整段
```

**主条文必须以"主"字开头**的过滤原则（这些都不是主条文）：

- "云∶叉头者..." → 采收/性状注释 ✗
- "云∶一名铜芸..." → 异名 ✗
- "云∶二月、十月采根..." → 采收时间 ✗
- "云∶味苦、辛..." → 性味 ✗
- **"云∶主X..."** → 才是主条文（X 是病证/功效）✓

### 多章节合并去重

同一药可能有多张本草章节卡（如防风在 `53493` 临床应用章 + `72064` 本草原始章 + `143726`/`164640`/`199725` 历代各家章），需去重 + 按来源优先级合并：

```python
# 来源优先级（_SOURCE_PRIORITY）
["本经", "本草", "别录", "唐本", "蜀本", "药性论"]

# 多章节去重：按 (来源, 前50字) 哈希去重, 然后按优先级排序
seen = set()
merged = []
for chapter in bc_list:
    for quote in chapter["quotes"]:
        key = (quote["src"], quote["text"][:50])
        if key not in seen:
            seen.add(key)
            merged.append(quote)
merged.sort(key=lambda q: _SOURCE_PRIORITY.index(q["src"]) if q["src"] in _SOURCE_PRIORITY else 99)
```

### 公众号方法论的可验证清单

公众号文章《关于如何阅读唐宋之前大部头方书的一点经验》的方法论，**在 zysj.db 上 100% 可验证**。完整方法论与脚本工具见 `references/tcm_research_methodology.md`：

| 公众号引用 | zysj.db 章节 | 验证结果 |
|---|---|---|
| 麻黄"破癥坚积聚" | zysjllsj:72076 | ✓ `《本草》云∶主中风伤寒头痛...破症坚积聚` |
| 附子"破癥坚积聚血瘕" | zysjllsj:94021 | ✓ `《本草(原文)》: 风寒咳逆，邪气，温中，金疮，破症坚积聚血瘕` |
| 枳壳"主大风在皮肤中如麻豆苦痒" | zysjllsj:133652 | ✓ 完整一致 |
| 防风"风邪目盲无所见" | zysjllsj:53493 | ✓ 跨病证：兼治"中风"+"目盲"+"皮肤瘙痒" |
| 细辛"久服明目，利九窍" | zysjllsj:72073 | ✗ 本经章节未含此句（需更古老的本草版本）|

执行 4 步研究流程用 `scripts/verify_prescription.py`（支持自然语言 + 关键词双入口，4 种意图自动识别）。

## 章节元数据检索路径

keyword 搜索会漏掉"按章节组织的结构性记录"。例如辅行诀的 15 张章节卡（标题=「一 辨肝脏病证文并方」「八 二旦六神大小汤」等）不在任何关键词命中里，但通过下面两种方式可拿到完整章节结构：

```python
# 方式 A：按 source_ref 检索（推荐）
import json
from pathlib import Path
p = Path('<skill_dir>/references/text_distillation/evidence_cards.jsonl')
hits = []
with p.open(encoding='utf-8') as f:
    for line in f:
        try: c = json.loads(line)
        except: continue
        if 'TypeID=1247' in c.get('source_ref',''):
            hits.append(c)
hits.sort(key=lambda x: x.get('chunk_id',''))
for c in hits:
    print(f"[{c.get('chunk_id')}] {c.get('title','')}")
```

```sql
-- 方式 B（最权威）：直接看 SQLite 章节结构
SELECT ID, BiaoTi FROM zysjllsj WHERE TypeID=1247 ORDER BY ID;
-- 这就是辅行诀的完整目录
```

**何时用**：当用户问"X 经典的所有方剂/章节"时，先 keyword 扫一遍看命中率（可能有"看起来很少"的误导），再按 TypeID 拉完整章节结构。**两者要交叉验证**才能给出准确覆盖报告。

## 已纠正的旧错误结论

⚠️ `coverage_audit.md` 旧版的"辅行诀覆盖率约 75%（18/24）"结论**只基于关键词扫描**，未发现 TypeID=1247 实际有 15 条结构化记录（旧版只数到 7 张命中卡）。正确认识：

- **结构性覆盖**：15 张章节卡全在 jsonl 里，每张的标题完整还原了原书目录
- **内容性覆盖**：每张实际只有前 281 字 → 86% 内容丢失，最关键的"八 二旦六神"章节只剩 11% 原文
- **结论**：知识库"知道辅行诀有哪些章节"（结构性 ✅），但"知道每章具体方剂"（内容性 ❌）。回答时必须明确区分这两层。

## 第三个数据源：CHM→md 镜像（与 SQLite 平行，可能有额外覆盖或缺口）

`/Users/applemima1111/Downloads/data/markdown/` 是与 SQLite 平行的第三个数据源——CHM 转 md 后的镜像。结构：

```
markdown/
├── chm/中医词典.md            # CHM 中医词典整体
├── 中医教材/                  # 教材合集
├── 中医著作/*.md              # 按书名拆分的古医书全集（约 670 本）
├── 中药字典/                  # 按拼音/类别拆分的中药字典
├── 临床理论/TypeID_XXXX.md    # 按 TypeID 拆分，每文件合并该 TypeID 所有记录
├── 综合数据/
└── ...
```

**关键陷阱**：md 镜像 ≠ SQLite 的简单导出。它是一套独立的 CHM→md 转换，**可能保留 SQLite 没有的内容，也可能丢失 SQLite 有的内容**。审计任何古籍时三个数据源都要交叉验证：

1. `evidence_cards.jsonl`（蒸馏卡，受 281 字符截断限制）
2. SQLite 源（`zysjmssqlbak.sqlite` / `20120413mssql.sqlite`，完整但依赖对方是否入库）
3. md 镜像（`/Users/applemima1111/Downloads/data/markdown/`，与 SQLite 平行，可能独有内容或独有缺口）

**实测对照（辅行诀脏腑用药法要）**：

| 数据源 | 章节覆盖 | 字符数 |
|---|---|---|
| SQLite zysjllsj TypeID=1247 | ✅ 完整 9 章 + 附录 | 27,798 字 |
| Markdown `中医著作/《辅行诀脏腑用药法要》.md` | ⚠️ 仅前言 + 序言 + 附录研究综述（14 个抄本对比） | 50,675 字节 |
| skill `evidence_cards.jsonl` | ❌ 截断 86% | 3,950 字 |

**诡异现象**：md 镜像里 50KB 的"辅行诀"——前言 + 序言 + 附录研究综述全有，但 9 章正文（七、八、九章等核心方剂）全部丢失。这是 CHM→md 转换时按 zysj.com.cn 网站上"中医著作"的目录顺序提取，CHM 源文件本身在该书页就只列了前言+附录。**所以单看 md 镜像会误判该书未收录核心内容**。

**md 镜像的核心价值**：收录 SQLite 没入库的古医书整本（如某些地方医案、近代医家全集）。如果一本书在 SQLite 找不到 TypeID，**先 grep md 镜像的 `中医著作/` 目录看有没有整书收录**。

**实测命令**：

```bash
# 看 md 镜像覆盖了哪些古医书
ls /Users/applemima1111/Downloads/data/markdown/中医著作/ | grep -i "辅行"
# → /Users/applemima1111/Downloads/data/markdown/中医著作/《辅行诀脏腑用药法要》.md

# 看某书在 md 镜像里的体量
wc -l -c /Users/applemima1111/Downloads/data/markdown/中医著作/《辅行诀脏腑用药法要》.md
# → 271 行 / 50675 字节

# 验证某章节是否在 md 镜像里
grep -n "小阳旦\|小青龙\|大朱雀" /Users/applemima1111/Downloads/data/markdown/中医著作/《辅行诀脏腑用药法要》.md
# → 命中 0 行说明该书在 md 镜像里也未收录核心章节
```

**何时查 md 镜像**：

- 一本古籍**既不在 evidence_cards 里、SQLite 也找不到对应 TypeID** 时——可能在 md 镜像里以整书形式收录
- 需要书的**完整原文**做引用时——md 镜像通常比 evidence_cards 完整（无 281 字符截断）
- 验证 SQLite 是否完整——交叉对比看是否漏章

**何时不查**：

- 已知有结构化 TypeID（如 1247）的古籍——直接走 SQLite 最快
- 只想搜关键词命中——evidence_cards 已够用
