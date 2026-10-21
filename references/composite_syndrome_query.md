# 复合主题检索工作流(病机 × 部位 × 症状)

> **适用提问**：「中焦痰瘀互结的阻滞有没有相关的论述?」「库里有没有同时讲 X 和 Y 的段落?」
> 「上热下寒 × 中焦 有没有」「痰瘀 × 胃脘 的条文」
> **一句话心法**:**先做邻近窗口复核再报数字** —— 一行库记录是一篇长文,同行命中 ≠ 主题相关。

---

## 一、为什么需要单独一份工作流

本 skill 既有工作流覆盖的是「单主题」检索:

| 已有工作流 | 检索形状 | 入口 |
|---|---|---|
| `wenyao_query_workflow.md` | 单主题方剂全集 | `scripts/` + SQL |
| `gaoyao_query_workflow.md` | 单主题外用膏药 | 同上 |
| `modern_classical_tcm_term_expansion.md` | 现代病名 → 古籍病名 | 词典扩展 |
| `tcm_research_methodology.md` | 病证 → 核心药 → 本草原文 | `verify_prescription.py` |

**缺的那一类**是「**两个以上维度拼在一起的复合主题**」:病机 × 部位 × 症状 × 结局。
这类提问不能用单关键词脚本跑,因为:

1. 关键词必须 **AND**(痰 AND 瘀 AND 中焦),不是 OR
2. AND 之后仍然会**严重虚高** —— 必须加邻近窗口复核
3. 结论需要**按 TypeID 分组**(同一本书的多个章节要归并),并标出书名

---

## 二、三段式方法(可直接跑)

### 段 1 — SQL 预筛(粗命中)

```python
import sqlite3
conn = sqlite3.connect('references/external/zysj.db')
kws = ['痰瘀', '中焦']
where = " AND ".join(f"NeiRong LIKE ?" for _ in kws)
rows = conn.execute(
    f"SELECT TypeID, ID, BiaoTi, NeiRong FROM zysjllsj WHERE {where}",
    [f"%{k}%" for k in kws],
).fetchall()
```

### 段 2 — 邻近窗口复核(收敛)

**这是本工作流的核心,不能省。** 一行 = 一篇长文,「痰」「瘀」「中焦」常出现在
互不相干的段落(前半章讲痰、后半章讲瘀、末尾提一句中焦)。AND 命中里绝大部分是这种
"同行不同段",直接报这个数字会严重高估主题密度。

```python
def positions(text, kw):
    out, i = [], text.find(kw)
    while i != -1:
        out.append(i); i = text.find(kw, i + 1)
    return out

def proximity_ok(text, kws, window=300):
    pos = {k: positions(text, k) for k in kws}
    if any(not v for v in pos.values()):
        return False
    for p in pos[kws[0]]:
        if all(any(abs(q - p) <= window for q in pos[k]) for k in kws[1:]):
            return True
    return False
```

**窗口怎么选**:`--window 300` 覆盖一个自然段,是最常用值;段落级论述用 300,
跨小节论述用 500~800,只关心同一句用 150。

### 段 3 — 分组 + 出处解析 + 摘录

按 TypeID 聚合 → 解析书名 → 围绕最密集处切原文摘录。书名解析见 § 四。

**一键跑**:`scripts/composite_query.py`(本文件配套脚本)

```bash
python3 scripts/composite_query.py --llsj 痰瘀 中焦
python3 scripts/composite_query.py --llsj 痰瘀 中焦 --window 500 --top 10
python3 scripts/composite_query.py --yj 痰瘀
python3 scripts/composite_query.py --variants 窸囊
python3 scripts/composite_query.py --llsj 痰瘀 中焦 --json
```

---

## 三、变体陷阱:0 命中 ≠ 库里没有

库内写法常与通行写法不一致,同一个词两种字形命中数可差到 0。

**实测对照**(本地 711MB 部署):

| 词 | 库内实作 | 通行写法 | zysjllsj 命中 |
|---|---|---|---|
| 痰瘀成囊 | **窠囊** | 窸囊 | 窠囊 **128** / 窸囊 **0** |
| 鼓胀 | 臌胀 | 鼓胀 | 同源,需并检 |
| 痰饮 | 淡饮 / 留饮 | 痰饮 | 古籍分名 |

**规则**:复合主题检索 0 命中时,先跑 `--variants <词>` 探写法,再换同义词重试;
确认过所有变体仍为 0,才可以说"库里没有"。**不要**在第一次 0 命中就下"未覆盖"结论。

内置变体表在 `scripts/composite_query.py` 的 `VARIANTS`,可按需扩写。

---

## 四、TypeID → 书名(出处必须能落到书)

`zysjllsj.TypeID` 是书级主键。三层解析:

| 来源 | 覆盖 | 可靠性 |
|---|---|---|
| `references/books_json/*.json` 的 `cell_id` → `title` | 689 本 | ✅ 权威映射 |
| 同 TypeID 下 `BiaoTi` 里形似书名的条目 | 无子集覆盖时 | ⚠️ 候选(需人工确认) |
| 都没有 | — | ❌ 只报 TypeID + 章节样例,**不要猜书名** |

**已知覆盖边界**:books_json 是全库的子集 —— 全库 `zysjllsj` 有 1105 个 distinct TypeID,
books_json 只有 689 本。查不到的 TypeID **不代表数据缺失**,只代表该书没被抽成 json。
此时诚实输出「TypeID=xxxx(章节样例:…) 书名未映射」。

**库容实测**(本地部署,便于判断规模):

| 表 | 行数 | 内容列 |
|---|---|---|
| `zysjllsj` 临床理论 | 206,245 | `NeiRong` |
| `zysjyj` 方剂 | 70,350 | `ChuFang` / `GongNengZZ` |
| `zysjzhsj` 综合 | 80,809 | `NeiRong` |
| `zysjcell` 单元格 | 1,390 | — |

方剂侧病证关键词几乎只出现在 `GongNengZZ`(功能主治),不是 `ChuFang` —— 见
`references/sqlite_deployment_recipe.md` 陷阱 #2。

---

## 五、输出形状(Erik 偏好)

Erik 要求「精确数据决策」,不接受模糊结论。复合主题的标准输出顺序:

1. **数据盘点表** —— 每个检索项的命中数(粗命中 / 收敛命中 双数字并列,标明口径)
2. **核心论述** —— 按病机分层,每条给 TypeID + 章节 + 原文摘录
3. **方剂表** —— 方名 / 出处 / 原文主治 / 组成
4. **可提炼治则** —— 从原文归纳,标明是归纳而非原文
5. **缺口与建议** —— 现有专题覆盖了什么、缺什么、下一步做什么
6. **git 状态** —— 本 skill 的同步铁律要求主动报告 + 询问是否推送

**原文引用铁律**:引用不带省略号(见 `references/zhongyi_source_citation_principle.md`),
要么给完整原文,要么写在引号外作概述。

---

## 六、相关文件

- `references/modern_classical_tcm_term_expansion.md` —— 病名维度的主题扩展(本文件是**病机+部位**维度的姊妹篇)
- `references/known_pitfalls.md` 坑 11 / 坑 12 —— 邻近窗口 + 变体写法两条硬规则
- `references/sqlite_deployment_recipe.md` —— 表级编码差异(按值手解码,勿设全局 text_factory)
- `references/tcm_research_methodology.md` —— 病证 → 核心药 → 本草原文的 4 步法
- `scripts/composite_query.py` —— 本工作流的配套脚本
