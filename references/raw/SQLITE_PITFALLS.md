# SQLite 访问陷阱与真相

> **目的**：纠正 references/raw/CLAUDE.md 中关于 SQLite 编码和字段位置的错误描述，作为后续查询的事实基线。
> **发现时间**：2026-07-27（查询"旋覆花丸"时实测）

---

## 🔴 陷阱 1：不要加 `text_factory = lambda b: b.decode('gbk')`

CLAUDE.md 的"Python 连接模板"明确写着：

```python
# ❌ 错误 — 会把已经是 UTF-8 的 str 重新当 GBK 字节流解码，产生乱码
conn.text_factory = lambda b: b.decode('gbk', errors='replace')
```

**实测真相**：当前 `20120413mssql.sqlite` 中的文本字段（`MingCheng` / `ChuFang` / `ZhaiLu` 等）**已经是 UTF-8 str**，不需要任何解码。直接 `sqlite3.connect(path)` 即可。

**症状**：加上 GBK text_factory 后输出乱码（如"娆惧啲鑺变父"），并且所有 `LIKE '%中文%'` 查询返回 0 条结果——因为 LIKE 是按字节比对的，编码不一致就匹配不上。

**正确用法**：

```python
# ✅ 正确
conn = sqlite3.connect('references/raw/20120413mssql.sqlite')
cur = conn.cursor()
# 不要设置 text_factory
```

或者想防御性写也行（虽然没必要）：

```python
conn = sqlite3.connect(path)
cur = conn.cursor()
# Python 3 默认 str 已经是 unicode，无需额外解码
```

---

## 🔴 陷阱 2：`ChuChu` 字段几乎全是 NULL，出处在 `ZhaiLu`

CLAUDE.md 把 `ChuChu`（出处）映射为 `source_ref`，但**实测 `ChuChu` 是 NULL**——所有方剂记录的出处信息都塞在 **`ZhaiLu`（摘录）** 字段里。

### zysjyj（方剂/中药字典）字段真相

| 字段 | 实际状态 | 真实含义 |
|------|---------|---------|
| `MingCheng` | ✅ 有值 | 方剂名/中药名 |
| `ChuFang` | ✅ 有值 | 处方组成 |
| `GongNengZZ` | ✅ 有值 | 功能主治 |
| `ChuChu` | ⚠️ **几乎全 NULL** | 出处（仅作占位，**不要查这个**） |
| **`ZhaiLu`** | ✅ **真正出处** | 摘录/原始出处，如"《太平圣惠方》卷三" |
| `XingWei` | ⚠️ 部分 NULL | 性味（方剂无此字段，仅中药有） |
| `GuiJing` | ⚠️ 部分 NULL | 归经（方剂无） |
| `TypeID` | ✅ 有值 | 类别码（39=方剂 / 40=单味药） |

### 错误查询 vs 正确查询

```sql
-- ❌ 错：查 ChuChu，返回 0 条
SELECT MingCheng FROM zysjyj WHERE TypeID=39 AND ChuChu LIKE '%太平圣惠方%'

-- ✅ 对：查 ZhaiLu
SELECT MingCheng FROM zysjyj WHERE TypeID=39 AND ZhaiLu LIKE '%太平圣惠方%'
-- 返回 420 条《太平圣惠方》方剂
```

### 实际行数实测

- 《太平圣惠方》方剂：`ZhaiLu LIKE '%太平圣惠方%'` → **420 条**
- 简记为"《圣惠》"：`ZhaiLu LIKE '%《圣惠》%'` → **514 种来源**
- 含"旋覆花"的方剂：`ChuFang LIKE '%旋覆花%'` → **259 条**
- 其中《圣惠方》的：`ZhaiLu LIKE '%《圣惠》%' AND ChuFang LIKE '%旋覆花%'` → **58 条**

---

## 🔴 陷阱 3：`text_search.py` 只查 JSONL，会漏掉 SQLite 独有的方剂

当用户问"《太平圣惠方》旋覆花丸"时，`text_search.py` 在 `evidence_cards.jsonl` 里**完全搜不到**（因为蒸馏时这一条被丢弃或根本没纳入）。但 SQLite 原始库里有 4927 个《圣惠方》方剂。

**判断规则**：

| 查询类型 | 优先用 |
|---------|--------|
| 用户给方剂名，问"组成 / 主治 / 历代注解" | `formula_query.py`（基于 JSONL） |
| **用户说"《XX》YY方/丸/散/汤"，问特定古籍方剂** | **直接查 SQLite（`ZhaiLu LIKE '%XX%'` + `ChuFang LIKE '%YY%'`）** |
| 含某药的所有方剂 | `herb_query.py` 或 SQLite（`ChuFang LIKE`） |
| 关键词检索 | `text_search.py` |

### SQLite 直查常用模式

```python
import sqlite3
conn = sqlite3.connect('references/raw/20120413mssql.sqlite')
cur = conn.cursor()

# 1. 某书 + 某方剂名
cur.execute("""
    SELECT MingCheng, ChuFang, GongNengZZ, ZhaiLu
    FROM zysjyj
    WHERE TypeID=39
      AND MingCheng = '旋覆花丸'      -- 精确方剂名
      AND ZhaiLu LIKE '%太平圣惠方%'  -- 真实出处字段
""")

# 2. 某书 + 含某药
cur.execute("""
    SELECT MingCheng, ChuFang, ZhaiLu
    FROM zysjyj
    WHERE TypeID=39
      AND ZhaiLu LIKE '%太平圣惠方%'
      AND ChuFang LIKE '%旋覆花%'
""")

# 3. 按 ZhaiLu 卷号分组（例：圣惠方各卷含某药）
# 见 /tmp/shenghui_xfh.py（实战脚本）
```

---

## ✅ 实战模式：用户问"《XX》YY"时的工作流

```
1. 先尝试 evidence_cards.jsonl → formula_query.py / text_search.py
   └─ 找到 → 输出
   └─ 找不到 → 进 SQLite

2. SQLite 直查：
   - 字段位置：ZhaiLu（出处）/ ChuFang（处方）/ GongNengZZ（主治）
   - 不要加 text_factory=gbk
   - LIKE 用普通中文字符串（Python 3 sqlite3 默认 UTF-8）

3. 如果 SQLite 也找不到：
   - 明确告诉用户"该方剂未收录"或"可能方名有出入"
   - 不要硬造答案

4. 找到数据后：
   - 按朝代 / 出处 / 卷号分组输出
   - 标注"来源：xxx"
   - 区分【原文引用】vs 【推断整理】
```

---

## 📚 已知"会查不到"的常见方名

| 查询 | 结果 | 原因 |
|------|------|------|
| 《太平圣惠方》旋覆花丸 | ❌ 0 条 | 精确方名不在库；"圣惠方"在数据库中简记为"《圣惠》" |
| 桂枝人参汤 / 小柴胡汤 | ✅ 充足 | 蒸馏充分 |
| 麻黄汤 | ✅ 充足 | 蒸馏充分 |
| 旋覆花（作为药物查询） | ✅ 中国药典有 | 中药字典 TypeID=40 |

**规律**：精确的方剂名（如"X丸/X汤"）查询，如果没结果，先到 SQLite 用 `ZhaiLu LIKE '%书名%' AND ChuFang LIKE '%药名%'` 看看是否其实收录了相关方剂，只是方名略有出入。