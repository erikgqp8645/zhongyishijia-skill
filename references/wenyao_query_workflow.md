# 中医方剂「专项主题查询」工作流：从自然语言到 115 张方剂全表

> **核心心法**：用户问「X 主题相关方剂」时，按**4 步全库溯源法**，从 zysj.db 70,350 方剂中精筛出所有相关方剂，并按功效分类 + 朝代溯源 + 实战配方输出完整报告。
>
> **适用场景**：任何「中医方剂专题查询」类问题（如「闻药方」「明目方」「安胎方」「外科方」等）—— 实战案例为 2026-08-17「闻药·鼻吸·鼻烟方剂」查询，从 70,350 方剂精筛出 115 张鼻疗法方剂，写成 29KB 专题文档。
>
> ## ⚠️ 引用原文「不带省略号」铁律（Erik 硬性偏好）
>
> **铁律**：所有「引用原文」段（如「处方」「本草溯源」中的 `「...」` 块）必须**展开为完整原文**，禁止保留 `...` / `……` / `六点...` 任何形式的省略号。占位符类（如 `...（共 8 条）`）保留。
>
> **来源**：tanpi 文档 v3.2 实战——79 处省略号全部展开为完整原文（22KB → 90KB / +260%），用户**反复强调**「我需要不带省略号」「这里依然存在好多省略号，这是我不想看到的」。
>
> **反面案例**（绝对禁止）：
> ```python
> # ❌ 用「，...」概括
> new_string = '「风痹身体皆痛...**呕逆痰癖**...」'  # 仍含 ...！
> # ❌ 自行编造内容
> new_string = '「风痹身体皆痛，**呕逆痰癖**」'  # 不是原文！
> # ❌ 批量正则替换（误伤）
> re.sub(r'\.{3,}', '', content)  # 会破坏占位符和正常标点！
> ```
>
> **正面 SOP**（5 步）：
> 1. **量化诊断**：`grep -c '…\|...' references/<topic>.md` 找出所有省略号位置
> 2. **SQL 批量取原文**：`SELECT NeiRong FROM zysjllsj WHERE ID=?` + `decode('utf-8')`（zysjllsj=UTF-8）
> 3. **手工展开**：每条 `old_string` 用完整原文中关键句 + `**加粗重点**` 重写
> 4. **行末重复检测**：同一行内 `grep "关键句" -c` ≥ 2 = 上一轮 patch 没干净 → 手工删除重复段
> 5. **最终验证**：引用块内的省略号必须为 0
>
> 详见 `references/distillation_workflow.md` § 2.3 + `references/zhongyi_source_citation_principle.md`（独立铁律资产）。

---

## 起源

2026-08-17 Erik 问「用鼻子闻能达到治疗效果」+「鼻烟壶里装的药」的中医方剂。按 SKILL.md 4 步研究法（多方归纳 + 高频核心药 + 本草溯源 + 古今对比）扩展为「专题查询工作流」—— 把「问什么」拆成「如何查」的标准化流程。

**最终成果**：
- `references/wenyao_bixi_daquan.md`（29KB / 350+ 行 / 115 张方剂 / 10 大类）
- 30 味核心药本草溯源
- 3 张鼻烟壶装药配方
- 9 个朝代沿革轴

---

## 一、3 阶段 4 步工作流

```
┌─────────────────────────────────────────┐
│ Stage 1: 关键词扩展（用户语言 → 中医术语）│
│  1.1 主题关键词分类                        │
│  1.2 中医专业术语映射                      │
│  1.3 动词 + 名词 + 病证 3 类关键词           │
├─────────────────────────────────────────┤
│ Stage 2: SQL 全库精筛（70,350 → 115 张） │
│  2.1 zysjyj 精筛（方剂库）                │
│  2.2 zysjllsj 溯源（临床理论库）            │
│  2.3 验收：精筛后必须含方剂名/处方/主治   │
├─────────────────────────────────────────┤
│ Stage 3: 分类与文档化（115 → 29KB 文档）  │
│  3.1 按功效分类（10 大类）                  │
│  3.2 朝代溯源（9 个朝代）                  │
│  3.3 高频核心药统计（30 味）                │
│  3.4 实战配方（3 张鼻烟壶装药方）          │
│  3.5 文档化保存（references/<topic>.md）   │
└─────────────────────────────────────────┘
```

---

## 二、Stage 1: 关键词扩展

### 1.1 主题关键词分类（用户语言 → 3 类）

**核心原则**：用户用**自然语言**问，数据库用**中医术语**存。需要做 3 类关键词扩展。

| 用户自然语言 | 主题 | 病证 | 动词 |
|------------|------|------|------|
| 「闻药 / 鼻烟 / 鼻疗」 | 鼻 / 鼻窍 | 鼻塞 / 鼻渊 / 鼻衄 / 鼻息肉 | 吹 / 吸 / 搐 / 取嚏 |
| 「明目方」 | 眼 / 目 | 目翳 / 雀目 / 暴赤 | 点眼 / 熏眼 |
| 「安胎方」 | 胎 / 妊 | 胎动 / 滑胎 / 难产 | 服 / 贴 |
| 「外科方」 | 疮 / 痈 / 疔 | 痈疽 / 瘰疬 / 疔疮 | 敷 / 贴 / 洗 |
| 「明目方」 | 眼 / 目 | 暴赤 / 翳膜 / 雀目 | 点眼 / 熏眼 |

### 1.2 中医专业术语映射

**关键**：同一动作在中医里有多种表达，必须用 OR 包含全部：

| 主题 | 同义词 / 动作同义词 |
|------|---------------------|
| 鼻疗 | 搐鼻 / 吹鼻 / 纳鼻 / 灌鼻 / 嗅 / 取嚏 / 熏鼻 / 鼻烟 / 鼻嗅 |
| 眼疗 | 点眼 / 熏眼 / 洗眼 / 吹眼 / 搐鼻（治眼疾）/ 敷眼 |
| 喉疗 | 含咽 / 噙化 / 点喉 / 吹喉 / 灌喉 |
| 脐疗 | 敷脐 / 贴脐 / 填脐 / 纳脐 / 熏脐 |
| 口疗 | 含化 / 噙服 / 漱口 / 含漱 |
| 阴道疗 | 纳阴 / 坐药 / 塞药 / 坐导 |
| 肛疗 | 纳肛 / 灌肠 / 塞肛 |
| 皮肤疗 | 敷 / 贴 / 涂 / 擦 / 洗 / 熏洗 / 泡 |

### 1.3 实战案例（闻药查询）

**用户问**：「用鼻子闻能达到治疗效果」+「鼻烟壶里装的药」

**3 类关键词扩展**：

| 类别 | 关键词 |
|------|--------|
| **主题** | 鼻 / 鼻窍 / 鼻烟 / 鼻吸 / 鼻塞 / 鼻渊 |
| **病证** | 鼻衄 / 鼻息肉 / 鼻窒 / 鼻渊 / 中恶 / 昏迷 / 急惊风 |
| **动词** | 吹鼻 / 搐鼻 / 纳鼻 / 灌鼻 / 嗅 / 取嚏 / 熏鼻 |

---

## 三、Stage 2: SQL 全库精筛

### 2.1 zysjyj 精筛（方剂库）

**关键**：用 `OR` 拼接所有关键词，覆盖 3 个字段（MingCheng 方名 / ChuFang 处方 / GongNengZZ 主治）。

```python
import sqlite3

DB = 'references/external/zysj.db'  # 711MB / 4 表
conn = sqlite3.connect(DB)

def dec_yj(v):
    """zysjyj = GBK 编码"""
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v

# ========== 第一步：粗筛（宽泛匹配）==========
verbs = ['%吹鼻%', '%纳鼻%', '%灌鼻%', '%嗅%', '%取嚏%', '%熏鼻%', '%鼻烟%', '%搐鼻%']
clauses = []
for v in verbs:
    clauses.append(f"ChuFang LIKE '{v}'")
    clauses.append(f"GongNengZZ LIKE '{v}'")
    clauses.append(f"MingCheng LIKE '{v}'")
where_str = ' OR '.join(clauses)
query = f"SELECT DISTINCT MingCheng, ChuFang, GongNengZZ FROM zysjyj WHERE ({where_str})"
cur = conn.execute(query)
rows = list(cur)
print(f"粗筛: {len(rows)} 条")
# 闻药案例：704 条

# ========== 第二步：精筛（去重 + 验证含真鼻疗动词）==========
output = []
for r in rows:
    name = dec_yj(r[0])
    if not name: continue
    cf = dec_yj(r[1]) or ''
    gz = dec_yj(r[2]) or ''
    # 必须真含至少一个鼻疗动词
    if any(v in cf for v in ['吹', '纳', '灌', '嗅', '取嚏', '熏', '搐']):
        output.append((name, cf, gz))
    elif any(v in gz for v in ['吹', '纳', '灌', '嗅', '取嚏', '熏', '搐']):
        output.append((name, cf, gz))

print(f"精筛: {len(output)} 张方剂")
# 闻药案例：115 张

conn.close()
```

**关键陷阱**：
- **zypjyj = GBK** 编码（不是 UTF-8）—— `decode_yj` 必须用 `gbk`
- 不要用 `text_factory = lambda b: b.decode("gbk")` 一刀切（zysjllsj = UTF-8）
- `DISTINCT` 必加（同一张方剂多个版本会出现多次）
- `OR` 包含 MingCheng + ChuFang + GongNengZZ 三字段

### 2.2 zysjllsj 溯源（临床理论库）

**目的**：从理论库溯源**朝代** + **经典** 出处（如《千金要方》《外台秘要》）。

```python
def dec_llsj(v):
    """zysjllsj = UTF-8 编码"""
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

# 搜《千金》《外台》中含鼻疗的条文
cur = conn.execute("""
    SELECT ID, BiaoTi, NeiRong FROM zysjllsj
    WHERE (NeiRong LIKE '%千金%' OR NeiRong LIKE '%外台%')
    AND (NeiRong LIKE '%吹鼻%' OR NeiRong LIKE '%纳鼻%' OR NeiRong LIKE '%灌鼻%'
         OR NeiRong LIKE '%取嚏%' OR NeiRong LIKE '%熏鼻%' OR NeiRong LIKE '%搐鼻%')
""")
for r in cur:
    bid = r[0]
    title = dec_llsj(r[1])
    content = dec_llsj(r[2]) or ''
    # 提取含鼻疗的段落
    for p in content.split('\r'):
        if '鼻' in p and any(v in p for v in ['吹', '纳', '灌', '末', '嗅', '取嚏', '熏', '搐']):
            print(f"ID={bid}  {title}\n  {p.strip()[:200]}")
```

### 2.3 验收：精筛后必须含方剂名/处方/主治

**3 个必含字段**：
1. **方名**（MingCheng）—— 用于方剂编号
2. **处方**（ChuFang）—— 完整药物组成
3. **主治**（GongNengZZ）—— 临床应用

任何一张方剂如果缺其中一个字段，要在文档中标注「（未提取）」。

---

## 四、Stage 3: 分类与文档化

### 3.1 按功效分类（10 大类）

**关键**：**按功效分类**比按朝代分类更实用（用户使用场景导向）。

| 类别 | 闻药案例 | 其他主题类比 |
|------|---------|-------------|
| 1. **急救通关** | 中风 / 昏迷 / 中恶 | 安神 / 镇静 |
| 2. **通鼻窍** | 鼻塞 / 鼻渊 / 鼻炎 | 明目 / 通耳 |
| 3. **出血** | 鼻衄 | 吐血 / 便血 |
| 4. **痛症** | 头痛 / 头风 | 胃痛 / 腹痛 |
| 5. **眼疾** | 暴赤 / 翳障 | - |
| 6. **口喉** | 喉痹 / 牙关紧急 | - |
| 7. **小儿** | 疳 / 惊风 | 痘疹 / 麻疹 |
| 8. **杂证** | 黄疸 / 水肿 | 消渴 / 虚劳 |
| 9. **专用主题** | 鼻烟（鼻烟壶装药）| 鼻烟 / 香囊 / 药枕 |
| 10. **局部** | 鼻息肉 | 痔疮 / 瘿瘤 |

### 3.2 朝代溯源（9 个朝代）

**按朝代溯源**给文档**学术权威**：

| 朝代 | 闻药案例代表 | 溯源方法 |
|------|------------|---------|
| 东汉 | 张仲景《金匮》| zysjllsj 找"伤寒"+"金匮"关键词 |
| 唐 | 孙思邈《千金》/王焘《外台》| 找「千金同」「外台同」标注 |
| 宋 | 圣惠/圣济总录 | zysjllsj 找"圣惠"+"圣济总录" |
| 金元 | 东垣/王好古学派 | 找"东垣"+"脾胃论" |
| 明 | 医学纲目/证治准绳 | 找"楼英"+"王肯堂" |
| 清 | 张璐/汪昂/严西亭/黄宫绣 | 找"张氏医通"+"本草备要"+"得配本草"+"本草求真" |
| 清·赵学敏 | **鼻烟**（本草纲目拾遗 1765）| 直接找"鼻烟"+"本草纲目拾遗" |
| 日·江户 | 丹波元简/元坚 | 找"金匮辑义"+"金匮述义" |
| 现代 | 中成药 | 直接搜现代方剂名 |

### 3.3 高频核心药统计

```python
# 闻药案例：HERBS 长名优先匹配
herbs = ['麝香', '冰片', '薄荷', '细辛', '辛夷', '苍耳子', '鹅不食草', '川芎', '白芷',
         '藜芦', '瓜蒂', '皂荚', '雄黄', '朱砂', '硼砂', '芒硝', '胆矾',
         '附子', '没药', '乳香', '蟾酥', '半夏', '南星', '牛黄',
         '牙皂', '甘草', '生姜', '葱白', '藿香', '佩兰', '麻黄', '桂枝', '防风']

from collections import Counter
herb_counter = Counter()
for name, cf, gz in output:
    for h in sorted(herbs, key=lambda x: -len(x)):  # 长药名优先
        if h in cf:
            herb_counter[h] += 1

for i, (h, c) in enumerate(herb_counter.most_common(30), 1):
    print(f"{i}. {h}: {c} 次")
```

### 3.4 实战配方（按安全度分级）

**3 张配方**（安全/救急/峻烈）：

```python
# 安全级（日常保健）
safe = {
    '鹅不食草': 1.5,  # 通鼻圣药
    '青黛': 1,         # 清肝明目
    '川芎': 0.5,       # 上行头目
    # ...
}

# 救急级（中风昏迷）
emergency = {
    '牙皂': 0.5,       # 取嚏通关
    '半夏': 0.3,       # 醒神化痰
    # ...
}

# 峻烈级（医师指导）
dangerous = {
    '藜芦': 0.2,       # 涌吐风痰（有毒）
    '麝香': 0.05,      # 醒神开窍
    '巴豆霜': 0.05,    # 开关通窍（大毒）
    # ...
}
```

### 3.5 文档化保存

```bash
# 文件命名
references/<topic>_daquan.md
例：references/wenyao_bixi_daquan.md
```

**文档结构**（10 大节）：

1. 起源（实战案例 + 触发问题）
2. 115 张方剂全表（按 10 大功效分类）
3. 朝代溯源（9 个朝代）
4. Top 30 高频核心药（本草溯源）
5. 实战配方（3 张鼻烟壶装药）
6. 《千金》《外台》专项溯源
7. 安全使用要点
8. 与本 skill 的关联
9. 查询方法记录（可复现）
10. 变更记录

**Drift 修复（3 处同步登记）**：

```python
# 1. SKILL.md Reference Priority（追加编号）
# 2. README.md 仓库结构树（追加 1 行）
# 3. README.md 更新日志（追加 1 行）
```

---

## 五、实战案例：闻药查询

### 输入

「用鼻子闻能达到治疗效果」+「鼻烟壶里装的药」

### 输出

`references/wenyao_bixi_daquan.md`（29KB / 350+ 行 / 115 张方剂）

### 关键数据

| 项 | 数值 |
|---|---|
| 粗筛方剂数（zysjyj）| 704 |
| 精筛方剂数（含真鼻疗动词）| 115 |
| 朝代覆盖 | 9 个 |
| 核心药统计 | 30 味 |
| 实战配方 | 3 张（安全/救急/峻烈）|

### 关键溯源发现

- **唐·《千金要方》** 中恶方：「**捣皂荚细辛屑，吹两鼻孔中**」（孙思邈 652）
- **唐·《千金要方》** 自缢死方：「**皂荚末葱叶吹两鼻孔中**」+「半夏一两捣筛，吹一大豆许纳鼻孔中」—— **孙思邈五绝急救**
- **清·《本草纲目拾遗》** 「鼻烟」：「**通关窍，治惊风，明目，定头痛，辟疫**」（赵学敏 1765）—— **「鼻烟」一词正式出现**

---

## 六、5 大陷阱与解决方案

| # | 陷阱 | 解决方案 |
|--:|------|----------|
| 1 | **编码一刀切**（zysjyj=GBK vs zysjllsj=UTF-8）| 按表用 `dec_yj` / `dec_llsj`（**不同函数**）|
| 2 | **关键词不够宽**（漏掉古方）| 同义词+动作同义词 OR 拼接（8+ 关键词）|
| 3 | **不含真动词**（只描述症状）| 精筛必须含「吹/纳/灌/嗅/取嚏/熏/搐」动作词 |
| 4 | **数据库归类特殊**（千金 TypeID=221=0 条）| 用 zysjllsj 找「千金同」+「外台同」标注 |
| 5 | **重复方剂**（同一首方不同版本）| `SELECT DISTINCT` + 按方名去重 |

---

## 七、扩展应用：其他主题查询工作流

按此 SOP 可直接查询任何中医方剂主题：

| 主题 | 关键词（同义词）| 预期方剂数 | 实战案例 |
|------|-----------------|-----------|---------|
| **闻药 / 鼻烟** | 吹鼻 / 搐鼻 / 灌鼻 / 嗅 / 取嚏 | 115 | ✅ wenyao_bixi_daquan.md |
| **明目方** | 点眼 / 熏眼 / 洗眼 / 吹眼 | 估算 200+ | 待做 |
| **安胎方** | 安胎 / 固胎 / 胎动 | 估算 80+ | 待做 |
| **外科方** | 敷 / 贴 / 涂 / 擦 / 洗 / 熏洗 | 估算 500+ | 待做 |
| **喉科方** | 含咽 / 噙化 / 点喉 / 吹喉 | 估算 100+ | 待做 |
| **妇科方** | 纳阴 / 坐药 / 塞药 | 估算 150+ | 待做 |

---

## 八、查询方法记录（可复现）

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage

# 1. 粗筛（替换 verbs 和 path）
python3 -c "
import sqlite3
conn = sqlite3.connect('references/external/zysj.db')
def dec(v, enc='gbk'):
    if v is None: return None
    return v.decode(enc, errors='replace') if isinstance(v, bytes) else v
verbs = ['%你的关键词1%', '%你的关键词2%', ...]  # 替换为新主题
where = ' OR '.join([f\"ChuFang LIKE '{v}' OR GongNengZZ LIKE '{v}' OR MingCheng LIKE '{v}'\" for v in verbs])
cur = conn.execute(f'SELECT DISTINCT MingCheng, ChuFang, GongNengZZ FROM zysjyj WHERE {where}')
for r in cur: print(dec(r[0]), '|', dec(r[1])[:80])
"

# 2. 精筛（验证含真动作词）
python3 -c "
import sqlite3
conn = sqlite3.connect('references/external/zysj.db')
def dec(v, enc='gbk'):
    if v is None: return None
    return v.decode(enc, errors='replace') if isinstance(v, bytes) else v
verbs = ['%你的关键词1%', ...]
where = ' OR '.join([f\"ChuFang LIKE '{v}' OR GongNengZZ LIKE '{v}' OR MingCheng LIKE '{v}'\" for v in verbs])
cur = conn.execute(f'SELECT DISTINCT MingCheng, ChuFang, GongNengZZ FROM zysjyj WHERE {where}')
for r in cur:
    cf = dec(r[1]) or ''; gz = dec(r[2]) or ''
    if any(v in cf for v in ['你的动作词1', ...]):
        print(dec(r[0]), '|', cf[:100])
    elif any(v in gz for v in ['你的动作词1', ...]):
        print(dec(r[0]), '|', gz[:100])
"
```

---

## 九、与本 skill 的关联

- **SKILL.md Reference Priority #26（wenyao_bixi_daquan）**: 本工作流的实战案例文档
- **SKILL.md Reference Priority #2-4（tcm_research_methodology）**: 4 步研究方法论（基础）
- **SKILL.md Reference Priority #20（zero_hit_fallback_workflow）**: 0 命中时的 fallback 流程
- **SKILL.md Reference Priority #21（distillation_workflow）**: 文档化工作流（参考格式）
- **SKILL.md Reference Priority #3（formula_curation_workflow）**: 单方深度考据

---

## 十、变更记录

### v1.0 (2026-08-17) — 首次固化

- **新增工作流**：从「闻药查询」提取的「中医方剂专题查询工作流」
- **3 阶段 4 步流程**：关键词扩展 → SQL 精筛 → 分类与文档化
- **5 大陷阱与解决方案**
- **7 个可扩展应用主题**（明目/安胎/外科/喉科/妇科等）
- **可复现查询代码**（Python inline）
- **触发词**：「方剂专题查询」「闻药方」「明目方」「安胎方」「外科方」

---

**【相关文件】**

- `references/wenyao_bixi_daquan.md` — 本工作流的实战案例
- `references/distillation_workflow.md` — 文档化工作流（参考格式）
- `references/tcm_research_methodology.md` — 4 步研究方法论（基础）
- `references/zero_hit_fallback_workflow.md` — 0 命中 fallback
- `references/formula_curation_workflow.md` — 单方深度考据

---

**【触发词】**

「方剂专题查询」「查 X 方剂」「X 主题方剂」「全库方剂」「闻药方」「明目方」「安胎方」「外科方」「喉科方」「妇科方」「儿科方」
