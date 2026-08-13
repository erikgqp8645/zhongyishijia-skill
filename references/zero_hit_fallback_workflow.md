---
name: zero_hit_fallback_workflow
purpose: When verify_prescription.py or query_formula.py returns 0 hits for a colloquial TCM query, the working fallback is direct SQLite LIKE on zysj.db. Verified 2026-07-26 with "小儿健脾".
trigger: 「0 hit」「verify_prescription 没结果」「query_formula 没匹配」「数据库没有这条」「口语化查询」「找不到这个方子」
date_verified: 2026-07-26
---

# 0-Hit Fallback 工作流

## 问题

`verify_prescription.py` 和 `query_formula.py` 的**意图解析**(`natural_language_query.md`)对规范化术语工作良好,但对**口语化/症状描述型查询**会返回 0 hit。

**典型踩坑**(已验证 2026-07-26):

| 用户查询 | verify_prescription 命中 | SQL 直接 LIKE 命中 |
|---|---|---|
| 「小儿健脾」 | 0 | 8+ (肥儿丸系列) |
| 「小儿脾胃虚弱」 | 0 | (类似)|
| 「小儿疳积」 | 0 (debug OK 但搜索 0) | (需 SQL 直查)|
| 「健脾丸」(规范) | ✅ 84 条 | 46 条 |
| 「小儿健脾丸」(规范) | 2 条(synthesis 综述) | 0 条(MingCheng 不含)|

**根因**:脚本的关键词提取从用户原句拆词,但口语化表达会拆出多个分散词,SQLite 的 WHERE 不会匹配 MingCheng。

## 4 步兜底流程

```
Step 1 · 确认是 0-hit 不是意图解析错误
        │
        ├─ 跑 verify_prescription.py --debug 看意图解析
        │  例: 小儿疳积 → disease_verify, 小儿健脾 → 0 (colloquial, 跳过意图)
        │
Step 2 · 试规范化术语 + Layer 1 evidence_cards
        │
        ├─ 换规范化病证名(疳积/积滞/慢惊风/食积)
        ├─ 跑 query_formula.py "规范病证名"
        │
Step 3 · Layer 3 直查 SQLite(主战场)
        │
        ├─ 打开 zysj.db,用 LIKE 模糊匹配
        │  例: SELECT * FROM zysjyj WHERE MingCheng LIKE '%肥儿丸%'
        │
Step 4 · 总结报告 + 给 Erik 选择
        │
        └─ 列出所有命中方剂 + 来源(TypeID/朝代),让 Erik 挑
```

## 实战命令模板(直接复制)

### Step 3 主战场:SQLite 直查

```bash
cd ~/.hermes/skills/zhongyishijia-expert-mentor-lineage

# 3.1 看表结构
sqlite3 references/external/zysj.db ".schema zysjyj" | head -10
# zysjyj 表核心列:MingCheng(方名), ChuFang(处方)

# 3.2 直查「健脾丸」系列
sqlite3 references/external/zysj.db \
  "SELECT MingCheng, ChuFang FROM zysjyj WHERE MingCheng LIKE '%健脾丸%' LIMIT 5"

# 3.3 直查「肥儿丸」系列(小儿健脾的主战场)
sqlite3 references/external/zysj.db \
  "SELECT MingCheng, ChuFang FROM zysjyj
   WHERE MingCheng LIKE '%肥儿丸%'
   ORDER BY MingCheng LIMIT 10"

# 3.4 复合条件(找所有含「小儿」+「健脾」类的方)
sqlite3 references/external/zysj.db \
  "SELECT MingCheng, ChuFang FROM zysjyj
   WHERE (MingCheng LIKE '%肥儿%' OR MingCheng LIKE '%小儿健脾%')
     AND (MingCheng LIKE '%健脾%' OR MingCheng LIKE '%肥儿%' OR MingCheng LIKE '%疳%')
   ORDER BY MingCheng"
```

### Python 等价(更稳,可控制 LIMIT 和分页)

```python
import sqlite3
conn = sqlite3.connect('references/external/zysj.db')
c = conn.cursor()

# 例:查肥儿丸系列
c.execute("""
    SELECT MingCheng, ChuFang
    FROM zysjyj
    WHERE MingCheng LIKE '%肥儿丸%'
    ORDER BY MingCheng
    LIMIT 15
""")
for name, fang in c.fetchall():
    print(f'【{name}】')
    print(fang[:300])  # 截断避免输出过长
    print()
```

## 命名法规范速查表(Erik 验证常用)

口语化查询 → 应该替换成的规范 MingCheng 关键词:

| 用户口语 | 应试规范关键词 | 数据库命中系列 |
|---|---|---|
| 小儿健脾 | 肥儿丸 / 小儿健脾散 / 健脾肥儿丸 | 肥儿丸系列(8+ 方) |
| 小儿脾胃虚弱 | 健脾丸 + 参苓白术散 | 健脾丸系列(20+ 方) |
| 小儿疳积 | 肥儿丸 / 疳积方 / 集圣丸 | 肥儿丸 + 疳积类方 |
| 健脾 | 健脾丸 / 参苓白术散 / 资生健脾丸 | 健脾丸系列 |
| 补气 | 四君子汤 / 补中益气汤 | (直查) |
| 治感冒 | 桂枝汤 / 麻黄汤 / 银翘散 | (直查) |
| 风湿 | 羌活胜湿汤 / 麻杏苡甘汤 | (直查) |
| 健脾祛湿 | 参苓白术散 / 健脾丸 | (直查) |

**通用兜底模板**(当你不确定命名时):
```sql
SELECT MingCheng, ChuFang FROM zysjyj
WHERE ChuFang LIKE '%健脾%'      -- 在处方里搜
   OR MingCheng LIKE '%健脾%'    -- 在方名里搜
LIMIT 20
```

## Step 4 报告模板

跑完 fallback 后,给 Erik 的标准报告:

```
═══════════════════════════════════════
zhongyishijia 0-hit fallback 完成
═══════════════════════════════════════

口语化查询: 「___」
脚本查询:    ___ 条 (verify_prescription / query_formula)
SQLite 直查: ___ 条 (MingCheng LIKE / ChuFang LIKE)

匹配系列(前 N 个):
  1. 【方名1】    出处/朝代    主治摘要
  2. 【方名2】    出处/朝代    主治摘要
  ...

推荐: 用方名 X 作为进一步查询的锚点
        (因为数据库有 X 这个 MingCheng)

═══════════════════════════════════════
```

## 已知局限性

### 1. `ChuFang LIKE '%X%'` 会扫到无关方
方剂组成包含 X 药的所有方都会命中。例:搜 `健脾` 会扫到含「健脾」二字的方+所有方组成里有人参/白术/茯苓的方(因为这些都是「健脾」要药)。需要二次过滤。

### 2. `MingCheng` 命名法不规范
同名异方(如「健脾丸」就有 20+ 个不同朝代的不同组成),不能假定 `WHERE MingCheng='健脾丸'` 单条结果。要用 LIKE + LIMIT。

### 3. TypeID 不直观
zysjyj 表没有 TypeID,但 zysjllsj / zysjzhsj / zysjcell 表有。要按方查出处需要 JOIN:

```sql
-- 暂未实现,需要的话查 zysj_index.py 看 TypeID 映射
```

### 4. 历史方 vs 现代中成药混合
「小儿健脾丸」是现代中成药(中国药典/中药部颁标准),古代数据库 zysjyj 收录较少,但「健脾丸」(古方)有 46 条。**给 Erik 报告时要明确区分古今方**。

## 一句话核心心法

**口语化查询(如「小儿健脾」)让 verify_prescription.py 返回 0 hit 是常态,不是 bug;正确兜底是直查 zysj.db 的 MingCheng LIKE(肥儿丸系列),规范术语用 query_formula.py,方剂完整组成则要靠 ChuFang LIKE;0 hit ≠ 没数据,只是意图解析器对口语化表达保守。**