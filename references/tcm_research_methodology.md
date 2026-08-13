# TCM 古方研究方法论：4 步回查流程

## 起源

公众号文章《关于如何阅读唐宋之前大部头方书的一点经验》（作者：苓苓后的夏陈皮）提出一个核心方法论：

> 唐宋方书（《千金方》《外台秘要》《太平圣惠方》《圣济总录》）大多只罗列方药组成与主治证候，极少阐释组方医理。要读懂这些古方，必须：
> 1. **同病证 → 多方归纳**（不能只看一首方，要看一组方的高频核心药）
> 2. **追溯本草原始功效**（不用现代中药学解读，要回归《本经》《别录》原文）
> 3. **对比古今差异**（同一味药，古代治"皮肤瘙痒"，现代归"行气药"——这种错位就是古方本义的失传点）

此方法论在 zysj.db 知识库上**完全可验证**，且本 skill 提供了 `scripts/verify_prescription.py` 工具一键执行。

---

## 4 步研究流程（机械化版）

| 步骤 | 数据源 | SQL/脚本操作 | 输出 |
|---|---|---|---|
| **Step 1: 同病证多方归纳** | `zysjyj` 表 (MingCheng + ChuFang) | `WHERE ChuFang LIKE '%<病证关键词>%' OR MingCheng LIKE '%<病证关键词>%'` | 病证相关方剂列表（去重） |
| **Step 2: 高频核心药** | 上述方剂的 ChuFang 字段 | 遍历每张方剂，用中药字典（HERBS，长名优先）匹配计数 | 覆盖率排序的核心药列表 |
| **Step 3: 本草原文回查** | `zysjllsj` 表 72xxx 系列 | `WHERE BiaoTi=<药名> AND NeiRong LIKE '%本草%'` 拉章节 → 正则提取"《X》云∶主Y..." | 每味核心药的本经/别录/唐本/蜀本/药性论原文 |
| **Step 4: 古今对比** | 同上 | 对比"本草原始功效"（Step 3 拉到的）vs"现代中药学归类"（zysjllsj 1xxx 章节） | 失传点列表 |

**已验证的成功案例**（公众号文章论点 vs zysj.db 原文）：

| 文章引用 | 数据库章节 | 验证结果 |
|---|---|---|
| 麻黄"破癥坚积聚" | zysjllsj:72076 | ✓ `《本草》云∶主中风伤寒头痛，温疟，发表出汗，去邪热气。止咳逆上气，除寒热，破症坚积聚` |
| 附子"破癥坚积聚血瘕" | zysjllsj:94021 | ✓ `《本草(原文)》: 风寒咳逆，邪气，温中，金疮，破症坚积聚血瘕...` |
| 枳壳"主大风在皮肤中如麻豆苦痒" | zysjllsj:133652 | ✓ 完整一致："本经主大风在皮肤中如麻豆苦痒、除寒热结" |
| 防风"风邪目盲无所见" | zysjllsj:53493 | ✓ 跨病证：兼治"中风"+"目盲"+"皮肤瘙痒"三大病证 |
| 细辛"久服明目，利九窍" | zysjllsj:72073 | ✗ 本经章节未含此句（需要回看更古老的本草版本） |

---

## `scripts/verify_prescription.py` 入口

### 用法

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage

# 4 种自然语言意图（自动识别）
python3 scripts/verify_prescription.py "治疗皮肤瘙痒的核心药" --top 5
python3 scripts/verify_prescription.py "中风的高频药" --top 4
python3 scripts/verify_prescription.py "麻黄的本草功效"
python3 scripts/verify_prescription.py "为什么续命汤用麻黄"
python3 scripts/verify_prescription.py "破癥坚积聚的方剂" --top 5

# 传统关键词模式（保留兼容性）
python3 scripts/verify_prescription.py 皮肤瘙痒 --keywords 痒 瘾疹 风瘙痒 瘙痒
python3 scripts/verify_prescription.py 续命 --no-bencao
```

### 5 种意图自动识别

| 输入示例 | 解析为 | 模式说明 |
|---|---|---|
| "治疗X的核心药" / "X的高频药" | 病证模式 | Step 1+2+3 全跑 |
| "X的本草功效" / "X的药性" | 药模式 | Step 3 单独跑（只查本草章节）|
| "为什么X用Y" | 药模式 | 跳到 Y 的本草章节，给出古代原始功效 |
| "含X的方剂" / "有X的方" / "用X的药方" | **方剂反查** (formula_reverse) | 查方名+处方含 X 药的所有方剂 |
| "破X的方剂" / "X积聚" | 主治反查模式 | 查本草章节里"破X"的药物（SQLite 字段 Chufang 通常不含本经原文）|
| 病证名（无修饰）| 病证模式 | 默认 |

### 别名归一

脚本内置了 `_DISEASE_ALIAS` 表，把同义病证名归一：

| 输入 | 归一为 | 搜索关键词 |
|---|---|---|
| 皮肤瘙痒 / 瘙痒 / 痒 | 皮肤瘙痒 | 痒 瘾疹 风瘙痒 瘙痒 |
| 中风 / 续命 / 偏枯 | 中风 | 中风 续命 偏枯 |
| 目系 / 目盲 / 青盲 / 目翳 / 明目 | 目系 | 青盲 目盲 目翳 明目 目暗 雀目 |
| 疟 / 疟疾 | 疟疾 | 疟 |
| 心悸 / 怔忡 | 心悸 | 心悸 怔忡 惊悸 |
| 痹 / 痹证 / 历节 | 痹证 | 痹 历节 痛痹 着痹 行痹 |
| ... | ... | ... |

需要新增病证时直接编辑脚本里的 `DISEASE_KEYWORD_MAP` 和 `_DISEASE_ALIAS` 两个字典。

---

## zysjllsj 章节 ID 范围编码（关键约定）

本草章节的 TypeID 和 ID 范围承载着**来源语义**，未来查询本草原文会反复用到：

| 章节 ID 范围 | 内容类型 | 本草特征 | 检索价值 |
|---|---|---|---|
| `zysjllsj:1xxx`（如 1086 甘草、1083 山药、1103 菟丝子）| 现代中药学 | 含【功效】【临床应用】【使用注意】 | 现代归类 |
| `zysjllsj:70xxx`-`zysjllsj:72xxx`（如 72076 麻黄、72145 苦参、72104 甘草）| **本草原始文献汇编** | 含《本草》云/《本经》/《别录》/《唐本》/《蜀本》原文 | ✓ **本草验证（首选）** |
| `zysjllsj:89xxx`（如 89012 白术、89059 菊花、89041 细辛）| 各家论述（医案/方论）| 包含"痘疹合参""临证指南"等后世医家 | 临床应用 |
| `zysjllsj:1xxxx`（如 108225 生地黄、115805 竹沥）| 单味药专章 | 古代名医 + 古代本草 | 药物专论 |
| `zysjllsj:133xxx`（如 133652 枳壳、133723 蛇床子）| 历代各家注解 | 含本经疏证、证类本草 | 关键本草考证 |

**经验法则**：
- 查"X 药的本经功效" → 优先查 `zysjllsj:7xxxx` 系列
- 查"X 药的现代功效/临床应用" → 查 `zysjllsj:1xxx` 系列
- 查"古代医家怎么论 X 药" → 查 `zysjllsj:89xxx` 或 `133xxx` 系列

**headless 模式识别**（章节开头没有《X》云字样、整段就是本经原文的）：
- `zysjllsj:53493` 防风 = `味甘、辛，温，无毒。主大风头眩痛，恶风...`（整段本经 + 别录原文）
- `zysjllsj:94021` 附子 = 同上
- `zysjllsj:89012` 白术 = `治（痘疹合参） 健脾止泻...`（后世医家）

**章节 ID 推断来源的伪代码**（在 `verify_prescription.py` 的 `_fetch_bencao` 中）：

```python
if 70000 <= id_ < 80000:
    src = "本草经集注"  # 70xxx-79999 范围 = 古代本草原始文献
elif 1 <= id_ < 10000:
    src = "本草(现代)"  # 1xxx 范围 = 现代中药学章节
else:
    src = "本草(原文)"  # 其他
```

---

## 本草正条文提取正则（关键 bug 修复经验）

本草章节里的字段是脏的，**不能简单截到第一个 `。`**，必须严格匹配"《X》云∶主Y..."格式：

```python
# 错误做法 1: 截到第一个句号 → 把"破癥坚积聚"截掉了
re.compile(r"《本草》\s*云\s*[∶:]?\s*主\s*([^。；\n]{10,300}?)(?=[。；\n]|$)")
# → 只匹配到"中风伤寒头痛，温疟，发表出汗，去邪热气"就停

# 错误做法 2: 宽松匹配 (不要求"主"字) → 把异名/采收/性味/注释都误当主治
re.compile(r"《本草》\s*云\s*([^。；\n]+)")
# → "云∶叉头者，令人发狂"（防风采收注）会被误当主治

# 正确做法: 贪婪到下一个《X》引用标记 + 要求"主"字开头
re.compile(r"《本草》\s*云\s*[∶:]?\s*主\s*(.+?)(?=\s*《[一-鿿]{1,5}》|\s*$)", re.DOTALL)
# → 完整保留 "主中风伤寒头痛...破症坚积聚" 整段
```

**主条文必须以"主"开头**的过滤原则（排除噪音）：
- "云∶叉头者..." → 不是主条文，是采收/性状注释
- "云∶一名铜芸..." → 不是主条文，是异名
- "云∶二月、十月采根..." → 不是主条文，是采收时间
- "云∶味苦、辛..." → 不是主条文，是性味
- **"云∶主X..."** → 才是主条文（X 是病证/功效）

**多章节合并**：同一药可能有多张本草章节卡（如防风在 `53493`、`72064`、`72064+1`、`164640` 等），需去重 + 按来源优先级合并。`verify_prescription.py` 自动处理，输出 `(+N 个章节)` 提示。

---

## 常见误区

| 误区 | 实际 |
|---|---|
| "麻黄/附子 现代中药学归为辛温解表" → 古代只是发汗药 | 古代本草有"破癥坚积聚血瘕"等治积聚癥瘕的功效 |
| "枳壳 现代归为单一的行气药" → 古代只是破气消积 | 古代本草有"主大风在皮肤中如麻豆苦痒"治皮肤瘙痒 |
| "细辛 现代归为祛风散寒通窍" → 古代只是止痛药 | 古代本草有"久服明目，利九窍"治目疾 |
| "黄芩 现代归为清热燥湿" → 古代只是清热药 | 古代本草有"主诸热黄疸...逐水...下血闭"等多重功效 |

这些"古今错位"是 zysj.db 验证古代方剂本义的关键抓手。公众号文章方法论的实质就是：**绕过现代中药学框架，直接回查本经原文。**

---

## 公众号验证脚本调用示例

执行完整 4 步研究流程，验证公众号文章的全部论点：

```bash
cd ~/.herplem/skills/zhongyishijia-expert-mentor-lineage

# 1. 续命汤系列方 → 32 首方剂, 高频核心药: 甘草(66%) 麻黄(50%) 防风(50%) 附子(47%) 人参(39%) 川芎(36%)
python3 scripts/verify_prescription.py "中风的高频药" --keywords 中风 续命 偏枯 --top 6

# 2. 麻黄的本草原文 → "破癥坚积聚" 完整呈现
python3 scripts/verify_prescription.py "麻黄的本草功效"

# 3. 为什么续命汤用麻黄 → 跳转麻黄本草, 揭示"中风伤寒头痛, 温疟, 发表出汗, 去邪热气, 止咳逆上气, 除寒热, 破癥坚积聚"
python3 scripts/verify_prescription.py "为什么续命汤用麻黄"

# 4. 破癥坚积聚的方剂 → 反查本草章节, 找到 29 条含"破癥坚积聚"的药物 (含麻黄、附子、曾青、甘遂、心...)
python3 scripts/verify_prescription.py "破癥坚积聚的方剂" --top 5
```

**输出**会显示：
- 续命汤系列 32 首方剂的**完整方名列表**
- 核心药**条形图**（覆盖率可视化）
- 每味核心药的本经/别录/唐本/蜀本/药性论**原始主治条文**
- 总结行：核心药覆盖度、本草章节数、引文来源

→ 公众号文章的所有论点都能在 zysj.db 里机械化验证，无需依赖任何外部本草权威数据库。

---

## 方剂反查模式 (formula_reverse) — 注意事项

**"含 X 的方剂"** 是这一轮新增的意图，用于回答"麻黄/细辛/附子 等药在哪些方剂里出现"。但实现时踩了几个坑，未来扩展同类查询时务必注意：

### 坑 1：MingCheng 字段混着药名条目

`zysjyj.MingCheng` 字段同时存**方名**和**药名**（一药多章节结构）。查"含麻黄的方剂"时 `MingCheng LIKE '麻黄%'` 会先匹配到 MingCheng = "麻黄" 的纯药名章节，把真正的方剂（"麻黄汤""小续命汤"）排到后面。

**修复**：在 SQL 里加 `AND MingCheng != ?` 排除 MingCheng 字段等于 herb 本身的纯药名条目：

```python
"SELECT DISTINCT MingCheng, ChuFang FROM zysjyj "
"WHERE MingCheng LIKE ? AND MingCheng != ? "
"ORDER BY MingCheng"
```

### 坑 2：DISTINCT 必加

`zysjyj` 表同一方名有多个章节（不同来源/版本），不 DISTINCT 会看到 30 个"附子丸"占满 top N。

### 坑 3（最隐蔽）：SQL `ORDER BY + LIMIT N` + Python sort 会丢失目标

如果用 `WHERE ... ORDER BY MingCheng LIMIT 60` 然后 Python 端按 name_priority 重排，**SQL 的 LIMIT 60 截断会丢失按 Python 排序本应排前的项**。

**实测**：查"含附子的方剂"，"附子汤"（3字短名经典方）在 SQL 排序里以"附"开头，被排到第 99 位 —— `LIMIT 60` 根本取不到，Python 端怎么重排都找不到它。

**正确做法**：**不依赖 SQL 排序**，让 SQL 一次返回所有 DISTINCT 记录（去掉 `ORDER BY` 和 `LIMIT`），Python 端按 name_priority 完整排序后再 `[:top]`：

```python
# 错误：SQL 排序 + LIMIT 会丢目标
"SELECT DISTINCT MingCheng, ChuFang FROM zysjyj "
"WHERE MingCheng LIKE ? AND MingCheng != ? "
"ORDER BY MingCheng LIMIT 60"

# 正确：全量取，Python 端排序
"SELECT DISTINCT MingCheng, ChuFang FROM zysjyj "
"WHERE MingCheng LIKE ? AND MingCheng != ?"
# Python: name_matches.sort(key=lambda x: (name_priority(x[0]), x[0]))
```

**name_priority 排序策略**（让"麻黄汤""附子汤""三痹汤"等经典方优先于"麻黄丸"等变方）：

```python
def name_priority(name):
    suffixes = ('汤', '散', '丸', '饮', '丹', '膏')
    if len(name) <= 4 and name.endswith(suffixes):  return 0  # 经典方
    if len(name) <= 6 and name.endswith(suffixes):  return 1
    if name.startswith(('加味', '加减', '加')):    return 2
    return 3
```

### 坑 4：DB 局限（不属于脚本 bug）

"四逆汤/真武汤"等经典方在 DB 里**没有独立的 MingCheng = "四逆汤"**，只有"附子四逆汤"（变方）"真武汤"倒是独立的 7 条。所以"含附子的方剂"反查"四逆汤"是 DB 真实情况（被合并到附子四逆汤），不是脚本 bug。
