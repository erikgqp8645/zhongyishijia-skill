# v3.0 计划：按中药查方剂（query_herb）

> 本计划源于用户提出的两个问题：
> 1. 当前结构是否利于 AI 读取？
> 2. 如何查询某味中药（如细辛）的所有方剂及成书年代、主治？
>
> 经实测，**当前 3 个脚本均无法直接回答**问题 2。本计划落地后，将新增 `query_herb.py` 并对相关基础设施做根本性优化。

---

## 一、当前结构诊断（不利于 AI 读取的 7 个原因）

| # | 问题 | 证据 |
|---|---|---|
| 1 | `card_type` 粒度太粗 | 单味药（细辛）和含细辛的方剂（九味羌活丸）都被标为 `herb`，AI 无法区分 |
| 2 | `source_ref` 是字符串非结构化 | 1,478 种不同书名形态，靠 `if key in source_ref` 模糊匹配 |
| 3 | `tags` 字段含结构化信息但被忽略 | `tags=["中药","TypeID:40"]` 已能精确标识，但 3 个脚本都没用 |
| 4 | `chunk_id`→SQLite 回查路径缺失 | `zysjyj:444` 可定位到 30+ 字段完整记录，但无脚本使用 |
| 5 | 232MB JSONL 全量扫描慢 | 每次查询 8-15 秒；SQLite LIKE 查询仅 80ms |
| 6 | SOURCE_MAP 命中率仅 17.2% | 82.8% 的 source_ref 因不在 53 条 SOURCE_MAP 中被识别为"待考" |
| 7 | 蒸馏丢失了反向索引 | 原始 `zysjyj.FuFang` 字段完整列出"含此药的所有方剂"，蒸馏后被压进 summary 字段 |

---

## 二、当前查询「细辛」的实际结果

```bash
$ python scripts/search_course_notes.py 细辛 | wc -l
5903   # ← 噪音大：药+方混排

$ python scripts/query_formula.py 细辛
# ← 5903 条全识别为"现代"（因 source_ref=《中国药典》）
# 期望：东汉《伤寒论》小青龙汤、明《奇效良方》排风汤、民国《医学衷中参西录》…
```

---

## 三、实施计划（5 个工作流）

> **状态追踪**（2026-07-09 下午第二次更新）：
> - 工作流 1 ✅ 已完成：`_source_map.py` 已交付，`SOURCE_MAP` 已扩展至 80+ 条目
> - 工作流 2 ✅ 已完成：`formula_query.py` 重构完成，向后兼容
> - 工作流 3 ✅ 已完成：`herb_query.py` 已交付（`scripts/herb_query.py`），`esc()` HTML 实体修复
> - 工作流 4 ✅ 已完成：生成 28,576 条，`herb` 字段 UTF-8 解码正确
> - 工作流 5 ✅ 已完成：`dynasty/book/prescribed_herbs` 字段全部正确（东汉《伤寒论》、现代《中国药典》等）
> - **修复记录**：
>   1. SQLite 编码确认是 UTF-8（非 GBK）
>   2. `redistill_cards.py` 新增 `ZhaiLu` 字段读取（真正的来源字段）
>   3. `redistill_cards.py` 修复 Windows 文件锁定问题（改用 bak→tmp→replace 策略）
>   4. `redistill_cards.py` 删除本地 `extract_prescribed_herbs`，改用 `_text_utils.extract_herbs`

### 工作流 1：抽出共用映射模块 + 扩展 SOURCE_MAP ✅ 已完成

**新建** `scripts/_source_map.py`：
- 把 `query_formula.py` 的 `SOURCE_MAP` / `TYPEID_MAP` / `DYNASTY_ORDER` / `identify_source()` / `sort_key()` 抽出
- **新增 25+ 条** SOURCE_MAP 条目（梁/魏/唐/宋/元/明/清/民国/现代全覆盖）

新增条目核心样本：

```python
# 东汉已有
"本草经集注":   ("梁",   "《本草经集注》", "陶弘景"),
"名医别录":     ("梁",   "《名医别录》",   "陶弘景"),
"吴普本草":     ("魏",   "《吴普本草》",   "吴普"),
"新修本草":     ("唐",   "《新修本草》",   "苏敬"),
"千金":         ("唐",   "《备急千金要方》", "孙思邈"),
"外台":         ("唐",   "《外台秘要》",   "王焘"),
"证类本草":     ("宋",   "《经史证类备急本草》", "唐慎微"),
"本草图经":     ("宋",   "《本草图经》",   "苏颂"),
"圣济总录":     ("宋",   "《圣济总录》",   "赵佶"),
"圣惠":         ("宋",   "《太平圣惠方》", "王怀隐"),
"局方":         ("宋",   "《太平惠民和剂局方》", ""),
"汤液本草":     ("元",   "《汤液本草》",   "王好古"),
"本草纲目":     ("明",   "《本草纲目》",   "李时珍"),
"奇效良方":     ("明",   "《奇效良方》",   "方贤"),
"普济方":       ("明",   "《普济方》",     "朱橚"),
"本草经疏":     ("明",   "《本草经疏》",   "缪希雍"),
"医学衷中参西录": ("民国", "《医学衷中参西录》", "张锡纯"),
"中华本草":     ("现代", "《中华本草》",   "国家中医药管理局《中华本草》编委会"),
"中国药典":     ("现代", "《中国药典》",   "国家药典委员会"),
"全国中草药汇编": ("现代", "《全国中草药汇编》", "全国中草药汇编编写组"),
"中药大辞典":   ("现代", "《中药大辞典》", "江苏新医学院"),
"辞典":         ("现代", "《中药大辞典》", "江苏新医学院"),  # 脱敏形式
```

### 工作流 2：重构 `query_formula.py` ✅ 已完成

- 顶部删除映射定义，改 `from _source_map import …`
- `clean_summary()` 中加 `html.unescape()` 解 `&amp;#236;` 等实体
- 其它逻辑保持不变（向后兼容）

### 工作流 3：新建 `scripts/herb_query.py`（纯 SQLite，80ms）✅ 已完成

**用法**：
```bash
python scripts/query_herb.py 细辛
python scripts/query_herb.py 麻黄 --sqlite C:/Users/Guo/Desktop/20120413mssql.sqlite
```

**核心逻辑**（伪代码）：
```python
def query_herb(herb, sqlite_path, max_cards=20):
    conn = sqlite3.connect(sqlite_path); conn.text_factory = bytes
    rows = []

    # ── 第 1 段：本药历代本草论述 ──
    # TypeID=40 = 中药材单味药
    for r in cur.execute("SELECT MingCheng, ChuChu, LaiYuan, GongNengZZ, XingWei, GuiJing, FuFang "
                          "FROM zysjyj WHERE TypeID=40 AND MingCheng=?",
                          (herb.encode('utf-8'),)):
        for source in extract_sources(clean_gbk(r[1])):  # ChuChu 拆多出处
            dyn, book, author = identify_source_string(source)
            rows.append(HerbRow(kind="herb_self", dynasty=dyn, book=book, author=author,
                                title=herb, indication=clean_gbk(r[3]),
                                nature=clean_gbk(r[4]), meridian=clean_gbk(r[5]),
                                full_prescriptions=clean_gbk(r[6])))

    # ── 第 2 段：含此药的所有方剂 ──
    # TypeID=39 = 中成药（方剂）; ChuFang LIKE '%herb%'
    for r in cur.execute("SELECT ID, MingCheng, ChuFang, GongNengZZ, ChuChu "
                          "FROM zysjyj WHERE TypeID=39 AND ChuFang LIKE ?",
                          (f'%{herb}%'.encode('utf-8'),)):
        dyn, book, author = identify_source_string(clean_gbk(r[4]))
        rows.append(HerbRow(kind="formula", dynasty=dyn, book=book, author=author,
                            title=clean_gbk(r[1]), prescription=clean_gbk(r[2]),
                            indication=clean_gbk(r[3])))

    rows.sort(key=lambda x: (DYNASTY_ORDER.get(x.dynasty, 99), x.dynasty, x.book, x.title))
    return rows
```

**输出格式**（双段 Markdown）：
```markdown
# 「细辛」历代本草与方剂论述汇总

## 一、细辛本药历代本草论述

| 朝代 | 著作 | 作者 | 性味 | 归经 | 功能主治 |
|:----:|:----:|:----:|:----:|:----:|:--------|
| 东汉 | 《神农本草经》 | — | 辛，温 | — | 主咳逆，头痛脑动… |
| 梁 | 《名医别录》 | 陶弘景 | … | … | … |
| 现代 | 《中国药典》 | 委员会 | 辛，温 | 心、肺、肾经 | 祛风散寒，通窍止痛… |

**经典含方**（节选自《*辞典》）：小青龙汤《伤寒论》、麻黄附子细辛汤《伤寒论》…

## 二、含「细辛」的方剂（按朝代排序，共 N 条）

| 朝代 | 著作 | 作者 | 方剂名 | 处方组成 | 主治 |
|:----:|:----:|:----:|:----:|:--------|:----|
| 东汉 | 《伤寒论》 | 张仲景 | 小青龙汤 | 麻黄、芍药、细辛、干姜… | 外寒内饮… |
| 明 | 《奇效良方》 | 方贤 | 排风汤 | … | … |
| 民国 | 《医学衷中参西录》 | 张锡纯 | … | … | … |
| 现代 | 《中国药典》 | 委员会 | 九味羌活丸 | 羌活、防风、苍术、细辛… | 解表，散寒，除湿… |
```

### 工作流 4：新建反向索引 `herb_index.jsonl`

**新建** `scripts/build_herb_index.py`（一次性）：
- 扫 SQLite zysjyj.ChuFang 字段
- 反向索引「每味药 → 含此药的方剂 ID 列表」

**输出** `references/text_distillation/herb_index.jsonl`（纳入 git-lfs）：
```json
{"herb": "细辛", "sqlite_id": 25999, "type": "material", "in_formula_ids": [5358, 1613, 1237, ...]}
{"herb": "麻黄", "sqlite_id": 25789, "type": "material", "in_formula_ids": [...]}
```

预计 ~5-10MB / ~18,000 条。

### 工作流 5：重蒸馏 `evidence_cards.jsonl`，加结构化字段

**新建** `scripts/redistill_cards.py`（一次性）：
- 读老 jsonl + SQLite 映射 + 写新 jsonl

**每张 card 新增 4-5 个字段**：

```json
{
  "card_id": "f7ff2891e750cff8",
  "card_type": "herb",
  "card_kind": "herb_material",       // ← 新增：herb_material / formula / clinical_theory / synthesis
  "title": "细辛",
  "dynasty": "现代",                    // ← 新增：结构化朝代
  "book": "《中国药典》",                 // ← 新增：结构化著作
  "author": "",                         // ← 新增：结构化作者
  "prescribed_herbs": [],               // ← 新增：方剂含的药材列表（仅 formula 有）
  "summary": "...",
  "source_ref": "《中国药典》",
  "chunk_id": "zysjyj:444",
  "tags": ["中药", "TypeID:40"],
  "alias": null,
  "pinyin": "Xi Xin"
}
```

**注意**：
- evidence_cards.jsonl 是 git-lfs 文件（232MB），重蒸馏后需重新 push
- 备份原文件到 `evidence_cards.jsonl.bak` 防回滚

### 工作流 6：更新 README.md

在「标准化方剂查询」小节后新增「按中药查方剂」章节。

---

## 四、文件改动清单

| # | 文件 | 动作 | 优先级 | 依赖 |
|---|---|---|:---:|:---:|
| 1 | `scripts/_source_map.py` | **新建** | 必须 | — |
| 2 | `scripts/query_formula.py` | 改 | 必须 | #1 |
| 3 | `scripts/query_herb.py` | **新建** | 必须 | #1 |
| 4 | `scripts/build_herb_index.py` | **新建** | 必须 | #3 |
| 5 | `references/text_distillation/herb_index.jsonl` | **新建**（git-lfs） | 必须 | #4 |
| 6 | `scripts/redistill_cards.py` | **新建** | 必须 | #1 |
| 7 | `references/text_distillation/evidence_cards.jsonl` | 重蒸馏覆盖 | 必须 | #6 |
| 8 | `README.md` | 改 | 必须 | #3 |

---

## 五、验证方案

```bash
# ── 工作流 1+2：向后兼容 ──
python scripts/query_formula.py 桂枝人参汤
# 期望：README Q1 测试通过，5+ 行朝代排序表格

# ── 工作流 3：核心功能 ──
python scripts/query_herb.py 细辛
# 期望：
#   第一段"细辛本药"≥3 行（神农本草经/中华本草/中国药典）
#   第二段"含细辛的方剂"≥50 行，跨东汉-现代多朝代
#   总输出 ≤200 行（vs search_course_notes 的 5903 行）

# ── 朝代分布验证 ──
python scripts/query_herb.py 细辛 | grep -E '^\| (东汉|梁|魏|唐|宋|元|明|清|民国|现代)' | wc -l
# 期望：≥10 个不同时代的命中行

# ── 噪音对比 ──
python scripts/search_course_notes.py 细辛 | wc -l   # 5903
python scripts/query_herb.py 细辛 | wc -l            # ≤200

# ── 工作流 4：索引构建 ──
python scripts/build_herb_index.py
python -c "import json; print(len(open('references/text_distillation/herb_index.jsonl',encoding='utf-8').readlines()))"
# 期望：~18,000 条

# ── 工作流 5：结构化字段 ──
python -c "
import json
with open('references/text_distillation/evidence_cards.jsonl', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 100: break
        card = json.loads(line)
        assert all(k in card for k in ('card_kind','dynasty','book','author')), f'line {i} missing fields'
print('✓ All 100 sampled cards have new fields')
"

# ── 端到端：复现 README Q1 ──
python scripts/query_herb.py 桂枝      # 桂枝参与的所有方剂
python scripts/query_formula.py 桂枝人参汤  # 仍正常工作（向后兼容）
```

---

## 六、风险与回滚

| 风险 | 缓解 |
|---|---|
| 重蒸馏 evidence_cards.jsonl 失败 | 备份为 `evidence_cards.jsonl.bak`；脚本失败时保留原文件 |
| SQLite 路径硬编码 | `--sqlite` 参数可覆盖；找不到时打印提示 |
| SOURCE_MAP 新旧 key 冲突 | `identify_source` 用 `first match`；新条目 key 与旧条目不重叠 |
| GBK 编码丢失字符 | `errors='replace'` 容错；输出时 `html.unescape()` |

---

## 七、时间预估

| 工作流 | 预计耗时 |
|---|---|
| #1 _source_map.py + 25+ 新映射 | 30 分钟 |
| #2 query_formula.py 重构 | 15 分钟 |
| #3 query_herb.py（纯 SQLite） | 90 分钟 |
| #4 herb_index.jsonl + build_herb_index.py | 60 分钟 |
| #5 evidence_cards.jsonl 重蒸馏 | 90 分钟 |
| #6 README.md 更新 | 30 分钟 |
| 测试 + 修复 | 60 分钟 |
| **总计** | **约 5-6 小时** |

---

## 八、变更日志预告

### v3.0（计划中）

- **新增** `scripts/_source_map.py` — 共用朝代/作者映射模块（25+ 新增条目）
- **新增** `scripts/query_herb.py <中药名>` — 按中药查本药历代本草 + 含此药的所有方剂
- **新增** `scripts/build_herb_index.py` + `references/text_distillation/herb_index.jsonl` — 反向索引（git-lfs）
- **重构** `scripts/query_formula.py` — 改 import `_source_map`
- **重蒸馏** `references/text_distillation/evidence_cards.jsonl` — 加 `card_kind/dynasty/book/author/prescribed_herbs` 结构化字段
- **修复** GBK→UTF-8 HTML 实体编码（`&amp;#236;` → `ì`）
- **更新** README.md — 新增「按中药查方剂」章节
---

## 九、待补录 SOURCE_MAP 条目（暂存）

> 以下条目导致"抵当汤"等方剂 dynasty="待考"，暂存于此，待后续批次修复。

| key | 朝代 | 著作 | 作者 | 备注 |
|-----|:----:|:----:|:----:|:-----|
| 伤寒全生集 | 清 | 《伤寒全生集》 | 待考 | 明清之际伤寒著作 |
| 杂病源流犀烛 | 清 | 《杂病源流犀烛》 | 沈金鳌 | 《沈氏尊生书》组成部分 |
| 嵩崖尊生 | 清 | 《嵩崖尊生》 | 待考 | |
| 云岐子注脉诀 | 待考 | 《云岐子注脉诀》 | 云岐子 | 元代？待考 |
| 血证论 | 清 | 《血证论》 | 唐宗海 | 清末血证专著 |
| 医宗必读 | 明 | 《医宗必读》 | 李中梓 | |
| 医宗金鉴 | 清 | 《医宗金鉴》 | 吴谦 | 已部分存在（TypeID=337） |
| 本草备要 | 清 | 《本草备要》 | 汪昂 | 已部分存在 |
| 本经逢原 | 清 | 《本经逢原》 | 张璐 | |
| 伤寒论条辨 | 明 | 《伤寒论条辨》 | 方有执 | 已存在 |
| 伤寒悬解 | 清 | 《伤寒悬解》 | 黄元御 | 已存在 |
| 伤寒来苏集 | 清 | 《伤寒来苏集》 | 柯琴 | 已存在 |
| 伤寒论本旨 | 清 | 《伤寒论本旨》 | 章楠 | |
| 伤寒论辨证广注 | 清 | 《伤寒论辨证广注》 | 汪昂 | |
| 伤寒大白 | 清 | 《伤寒大白》 | 秦之桢 | |
| 伤寒缵论 | 清 | 《伤寒缵论》 | 张璐 | |
| 伤寒论纲目 | 清 | 《伤寒论纲目》 | 沈金鳌 | |
| 伤寒论类方 | 清 | 《伤寒论类方》 | 徐灵胎 | |
| 伤寒温疫条辨 | 清 | 《伤寒温疫条辨》 | 杨栗山 | |
| 伤寒论经解 | 清 | 《伤寒论经解》 | 待考 | |
| 伤寒论集成 | 清 | 《伤寒论集成》 | 待考 | |
| 得心录 | 清 | 《得心录》 | 待考 | |
| 经方实验录 | 民国 | 《经方实验录》 | 曹颖甫 | 已存在 |
| 伤寒金匮发微 | 民国 | 《伤寒金匮发微》 | 曹颖甫 | 已存在 |
| 曹颖甫 | 民国 | 《伤寒金匮发微》 | 曹颖甫 | 已存在 |
| 医垒元戎 | 元 | 《医垒元戎》 | 王好古 | |
| 此事难知 | 元 | 《此事难知》 | 王好古 | 已存在 |

