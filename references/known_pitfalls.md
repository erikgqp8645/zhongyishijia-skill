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

## 坑 11: 多关键词 AND 命中 ≠ 主题相关(必须邻近窗口复核)

`zysjllsj` 一行 = 一篇长文(常是整章病机论述)。多个关键词用 `AND` LIKE 拼起来后,
「痰」「瘀」「中焦」常落在互不相干的段落,粗命中数严重虚高。

**规则**:复合主题检索必须做**邻近窗口复核** —— 所有关键词须落在彼此 ±N 字符内
(默认 300 字覆盖一个自然段)才算共现;报告时**粗命中与收敛命中两个数字并列**。

```python
# 收敛判据(星形邻接):第一个关键词的某个位置,与其余每个关键词的某个位置相距 ≤ window
def proximity_ok(text, kws, window=300):
    pos = {k: [i for i in range(len(text)) if text.startswith(k, i)] for k in kws}
    if any(not v for v in pos.values()):
        return False
    return any(all(any(abs(q - p) <= window for q in pos[k]) for k in kws[1:])
               for p in pos[kws[0]])
```

**为什么**:漏掉这步会让"库里有没有这个论述"的结论建立在虚高计数上,回答看起来有数据、
实际无依据。完整方法见 `references/composite_syndrome_query.md`。

---

## 坑 12: 库内实作写法 ≠ 通行写法(0 命中不等于库里没有)

同一个词两种字形,命中数可差到 0。**实测:库内「窠囊」128 条,「窸囊」0 条。**

**规则**:任何关键词 0 命中时,先探库内写法变体(字形异体 + 古籍分名 + 异体同义词),
再换同义词重试;所有变体都试过仍为 0 才可报"未覆盖"。**禁止**第一次 0 命中就下结论。

```bash
python3 scripts/composite_query.py --variants 窸囊   # 一次列出各写法命中数
```

**为什么**:数据库是古籍离线抓取,收录用的是原书用字(窠/窸、臌/鼓、淡饮/痰饮),
按现代通行字形检索会得到假阴性。

---

## 坑 10: HERBS 字典要"长药名优先匹配"

```python
HERBS = sorted([...], key=lambda x: -len(x))  # 关键: 按长度降序

# 错: 先匹配 "黄" → 误判
HERBS = ["黄", "黄芩", "黄芪"]  # 错

# 对: 长药名优先 → "黄芩" 不会误匹配 "黄"
HERBS = ["黄芩", "黄芪"]  # ✓
```

**`_extract_herbs()` 内部用 `for h in HERBS` 遍历，长药名先匹配。

---

## 坑 13: 外用方的病机信号不在主治列 —— 只扫 GongNengZZ 会漏掉整类方

**症状**：问「痰瘀互结的**外敷**方有哪些」，用 `GongNengZZ LIKE '%痰瘀%'` 只得 **16** 首，
但实际库里外用方的病机描述大量落在**组成/制法/用法/按语**列，
最终正确命中是**数十倍**于此。

**为什么**：`zysjyj` 表的「主治」列对外用方写的是**成品形态**（「治症瘕痞块」「治痰核瘰疬，未穿破者」），
而不是病机；病机（痰、瘀）藏在 `ChuFang`（白芥子/莪术/三棱/阿魏/麝香）、
`ZhiFa`（熬膏/摊贴/收膏）、`HuaXueCF`（贴脐上/以热手磨擦）、`ZhuYi`（按语释义）里。
同一个方主治写「痞块」，机制却是痰瘀互结 —— 只扫主治列等于只扫了它的一半。

**规则**：方剂表检索**病机关键词**时，病机列与主治列要**取并集**筛，不是只看主治：

| 列 | 承载什么 | 典型命中 |
|---|---|---|
| `ChuFang` 组成 | 药味即病机 | 白芥子/莪术/三棱/鳖甲/阿魏 |
| `ZhiFa` 制法 | 剂型与工艺 | 熬成膏/摊贴/狗皮摊/收膏 |
| `HuaXueCF` 用法 | **给药途径** | 贴脐上/以热手磨擦/外敷/熨之 |
| `ZhuYi` 按语 | 释义与机制 | 活血祛瘀，化积消痞 |
| `GongNengZZ` 主治 | 成品适应症 | 症瘕痞块 / 痰核瘰疬 |

**部位/病名关键词**（痞块/积聚/症瘕/痰核/瘰疬）反过来主要在主治列 —— 所以两类关键词
要各自扫各自的列组，**组内 OR、组间 AND**，不要用同一列集合筛所有词。

**姊妹坑**：方剂表**一行 = 一张方剂 = 一个完整语义单元**，
所以**行级 AND 合法，不需要邻近窗口复核**；窗口规则（坑 11）是 `zysjllsj` 专有的
（那边一行 = 一整章论述）。两层粒度不同，别把窗口规则套到方剂表上。

**配套脚本**：`scripts/external_formula_query.py`（病机列/主治列分列扫描 + 给药途径识别 + 同名多版本并陈）。

---

## 坑 14: 同名方在方剂表可能有多版本 —— 必须按方名分组并陈，不能只取一条

**症状**：`MingCheng LIKE '%加减紫金丹%'` 返回 2 行，
一行《金鉴》卷八十九（「消热化痰，理气健脾，润肌定喘」），
一行《医宗金鉴》卷七十三（「健脾养血，化痰消瘀」）—— **主治方向不同，不是重复条目**。

**为什么**：方剂库按「书 × 卷 × 条」录入，同名方在不同书里各自成条，
古籍版本之间常有一方衍化/改名的关系；把它们当重复条目去重会丢掉版本谱系信息。

**规则**：方剂表检索命中后，按方名聚合并**把所有版本一并列出**（各带 ID + 出处 + 各自主治），
版本数多于 1 时在输出里显式标注。静默只取一条会让读者以为库里只有这一方。

**同类方**（库内已确认有多版本）：`加减紫金丹`(2) / `消核膏`(2) / `化核膏`(2) / `化痞膏`(3+)
/ `冲和膏`(3) / `阳和解凝膏`(2) / `金丝万应膏`(6) / `马兰膏`(2) / `大黄膏`(8+) / `琥珀膏`(10+)。

**注意**：这与 `references/gaoyao_query_workflow.md` 约束 B（同名方家族化呈现）是同一条规则的两种口径 ——
膏药专题按「方根家族」讲，这里按「版本并陈」讲，都是**保留全部变方 + 标注出处**，不是去重丢弃。
