># 已知陷阱与防错配方 (Cross-cutting pitfalls for verify_prescription.py + formula_table.py)

踩过的坑。每条都是真实 bug 修复后留下的，未来脚本扩展时一定要看。

---

## 坑 1: Python `or` 优先级 — TypeError 风险

```python
# ❌ 错 — `or` 在 any() 内返回 bool 而非 iterable
if any(name.startswith(s) or name.startswith(s) for s in [...]): pass

# ✅ 对 — 用 str.startswith((tuple))
if name.startswith(('汤', '散', '丸')): pass

# ✅ 或 — 用 str.endswith((tuple)) 配合 any
if any(name.endswith(s) for s in ('汤', '散', '丸')): pass
```

**症状**：`TypeError: 'bool' object is not iterable`
**原因**：`or` 在生成器内会**先短路**返回单值，再传给 `any()`，而 `any()` 需要 iterable

---

## 坑 2: `re.search` 前瞻 vs 贪婪

```python
# ❌ 错 — 前瞻 `(?=...)` 在第一个句号就停下
# 原文: "主中风伤寒头痛，温疟，发表出汗，去邪热气。止咳逆上气，除寒热，破癥坚积聚。"
re.search(r"主\s*(.{2,80}?)(?=[。；\n]|$)", content)
# 匹配到: "中风伤寒头痛，温疟，发表出汗，去邪热气" (在第一个 。 处停下)
# 漏掉: "止咳逆上气，除寒热，破癥坚积聚"

# ✅ 对 — 贪婪到下一个《X》引用标记
re.search(r"主\s*(.+?)(?=\s*《[^》]+》|\s*$)", content, re.DOTALL)
# 匹配到完整本经主治

# ✅ 通用模式 — 截到第二个句号
text = m.group(1)
periods = list(re.finditer(r"[。；]", text))
if len(periods) >= 2:
    text = text[: periods[1].start()]
```

**本经条文特征**：`主X。X。X。` 多句连用，需贪婪匹配到下一个引用标记或第二个句号。

---

## 坑 3: 字符类漏 `·` 和 `○`

```python
# ❌ 错 — 数字编号正则
re.match(r'^\d+[\.．、]', '一七○○七·华佗')
# 失败！中点 · (U+00B7) 和圆圈零 ○ (U+25CB) 不在字符类中

# ✅ 对 — 包含常见分隔符
re.match(r'^\d+[\.．、·]', '一七○○七·华佗')  # ✓
re.match(r'^[一二三四五六七八九十百○]+[\.．、·]', '一七○○七·华佗')  # ✓
```

**典型数据源**：
- `1.` `1、` `18、` `18.` `1.7·` — 数字 + 句点/顿号/中点
- `一、``二、``十、``一七·` `一○○·` — 中文数字 + ○ + 句点/顿号/中点

---

## 坑 4: `patch` 工具误删/误改

```python
# ❌ 错 — patch 工具如果 old_string 不够唯一，会破坏性替换
# 多个 "def _connect():" 都被删掉 → SyntaxError: name '_connect' is not defined
```

**防御**：
- 每次 patch 前 `read_file()` 看完整上下文
- patch 后立即 `python3 -c "import sys; sys.path.insert(0, 'scripts'); import formula_table"` 验证导入
- 大量重构时用 `write_file()` 全量重写，不要用 patch 做"小范围修改"

---

## 坑 5: SQL `ORDER BY` 排序被"1./2./3."数字章节挤掉

```sql
-- 错 — 默认 ORDER BY MingCheng 把 "1.益肺消积汤" 排到 "理中汤" 前
SELECT BiaoTi FROM zysjllsj WHERE NeiRong LIKE '%白术%'
ORDER BY BiaoTi
LIMIT 500
-- 结果: top 20 全是 "1.XXX/2.XXX" 临床方, 经典方 "理中汤" 在 #2087
```

**修复**：Python 端按启发式优先级排序（不要依赖 SQL ORDER BY）：

```python
priority = -1 if title in PURE_NAME_MAP else 0  # ... 见 formula_metadata_table.md
results.sort(key=lambda r: (r["_priority"], r["title"]))
```

---

## 坑 6: 数据库章节的"数字·华佗..."型

zysj.com.cn 的章节编号用 `○○○七·` (圆圈零 + 中点)，不是 ASCII 数字。需要：

```python
# 数字编号方应排到 priority 2 (排最后), 但常被认成纯名方 (priority 3)
has_numeric_prefix = bool(
    re.match(r'^\d+[\.．、·]', title)             # 数字 + 任意分隔符
    or re.match(r'^[一二三四五六七八九十百○]+[\.．、·]', title)  # 中文数字 + 圆圈零 + 任意分隔符
)
```

**如果忘了 `·` 和 `○`**，"1.7·华佗救卒魇神方" 会被误判为纯名方 (priority 3) → 排前。

---

## 坑 7: Python `len("喉痹")` = 2

```python
# ❌ 错
if len(text) >= 3: return text  # 过滤掉 "喉痹" "中风" 等 2 字主治
# ✅ 对
if len(text) >= 2: return text  # 中文字符算 1 字符
```

---

## 坑 8: zysjllsj 表字段名 ≠ zysjyj

| 表 | 方名字段 | 内容字段 |
|---|---|---|
| zysjyj (方剂库) | `MingCheng` | `ChuFang` |
| zysjllsj (临床理论库) | `BiaoTi` | `NeiRong` |

**坑点**：脚本里跨表查询时，**两个表字段名不一样**。例如想"列含细辛的方剂 + 临床应用"：

```python
# 错: 错用 MingCheng 查 zysjllsj
cur.execute("SELECT * FROM zysjllsj WHERE MingCheng LIKE ?")  # 报错

# 对: zysjllsj 用 BiaoTi
cur.execute("SELECT * FROM zysjllsj WHERE BiaoTi LIKE ?")
```

---

## 坑 9: 公众号文章方法论需要 4 步流水线

`scripts/verify_prescription.py` 的核心 4 步：

1. **同病证多方归纳**：`--keywords` 多关键词 OR 查询
2. **高频核心药**：用 HERBS 字典（~80 味）去重 + Counter.most_common
3. **本草原文**：BiaoTi = 药名 → zysjllsj:72xxx 系列 → 正则提取 `主X...`
4. **总结**：4 步结果聚合到 Markdown 表格

**不要**只跑步骤 1-2（仅看高频药）就返回结果，**要**跑完整 4 步。
**也不要**把 4 步拆给多个脚本（`step1.py` / `step2.py`），会让用户来回切。

---

## 坑 10: HERBS 字典要"长药名优先匹配"

```python
HERBS = sorted([...], key=lambda x: -len(x))  # 关键: 按长度降序

# 错: 先匹配 "黄" → 误判
HERBS = ["黄", "黄芩", "黄芪"]  # 错

# 对: 长药名优先 → "黄芩" 不会误匹配 "黄"
HERBS = ["黄芩", "黄芪"]  # ✓
```

`_extract_herbs()` 内部用 `for h in HERBS` 遍历，长药名先匹配。
