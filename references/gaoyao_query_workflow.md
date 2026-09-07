# 中医外科膏药方专题查询工作流

> **核心心法**：膏药方（薄贴/摊贴/贴之/敷之）是中医外治法的核心载体之一。本工作流继承 `references/wenyao_query_workflow.md`（闻药·鼻吸·鼻烟方剂大全）的 3 阶段 4 步骨架，但**额外**为膏药方这一类**双重模糊边界**主题新增 **3 大专属约束**：① 皮肤痹痛 vs 筋骨痹痛 去重；② 古今同名方剂（如狗皮膏/虎骨膏 14+ 变方）去重；③ 现代中成药 vs 古籍原方分层。
>
> **实战案例**：2026-09-07 Erik 问「中医世家 skill 收集一下 关于颈肩腰腿痛的膏药方」→ 从 70,350 张方剂库精筛出 **121 张**膏药方剂（76KB / 524 行），与 `wenyao_bixi_daquan.md`（闻药）/ `kouqiang_kuiyang_zhenjiu.md`（口腔溃疡针灸）共同组成**中医外治法三大专题**。
>
> **⚠️ 与 `wenyao_query_workflow.md` 关系**：本文档是**姊妹专题文档**，**不修改**母工作流，而是为膏药方这一**双向歧义**（外用贴膏既治筋骨痹痛也治皮肤痹痛）类查询提供**额外约束扩展**。母工作流的核心 3 阶段 4 步骨架详见 `references/wenyao_query_workflow.md`。

---

## 一、本工作流新增的 3 大专属约束（vs wenyao_query_workflow.md 母工作流）

### 约束 A：皮肤痹痛 vs 筋骨痹痛 去重（核心陷阱）

**问题本质**：膏药方的**主治字段**经常同时出现「痹」字，但意义完全不同：
- **筋骨痹痛**：「痹在筋骨」（腰/腿/膝/肩/颈部位）→ 颈肩腰腿痛膏药
- **皮肤痹痛**：「抓搔顽痹不知痛痒」「风癣」「鹅掌风」「血风疮」→ 皮肤病膏药

**症状**：单纯用「MingCheng LIKE '%膏%' AND GongNengZZ LIKE '%痹%'」会同时命中两类方剂，结果过宽（150+ 条混入皮肤病膏药）。

**实战命中案例**（2026-09-07 颈肩腰腿痛查询）：
  - ❌ 错入：`川槿皮膏`（治风癣顽痹）`马齿苋膏`（治两足血风疮）`马齿苋膏`（血风疮）
  - ❌ 错入：`曼荆实丸`（皮痹不仁）`大青膏`（小儿急惊抽搐）`蓖麻膏`（打扑肿毒）
  - ✅ 正确：`蠲痛五汁膏`（寒湿腰背痛）`集宝疗痹膏`（风寒湿痹）`虎骨膏`（腰腿痛）

**解决 SOP（Python 端精筛）**：

```python
# 步骤 1：皮肤病痹痛关键词黑名单（命中即排除）
skin_disease_kw = ['顽癣', '瘙痒', '抓搔', '疥', '鹅掌风', '皮癣', '风癣',
                   '湿癣', '血风疮', '肤痒', '痒搔', '脓水', '黄水',
                   '浸淫', '湿疹', '阴蚀', '狐惑']

# 步骤 2：筋骨痹痛部位白名单（必须命中至少 1 个）
body_parts_required = ['颈', '项', '肩', '臂', '腰', '腿', '膝', '足',
                       '脚', '背', '脊', '骱', '筋骨', '骨节', '肢节',
                       '关节', '筋脉', '筋络']

# 步骤 3：精筛逻辑
for r in rows:
    blob = r['chufang'] + '||' + r['gongnengzz'] + '||' + r['name']
    # 同时命中皮肤+筋骨 → 按白名单部位是否明确决定保留/排除
    has_skin = any(k in blob for k in skin_disease_kw)
    has_body_part = any(k in blob for k in body_parts_required)
    if has_skin and not has_body_part:
        continue  # 纯皮肤病 → 排除
    # 没皮肤、有筋骨部位 → 保留
    if not has_skin and has_body_part:
        output.append(r)
```

**实战数据**：颈肩腰腿痛查询 → 第一次粗筛 4377 条 → 加痹痛过滤 0 条（SQL 转义问题）→ 加 Python 端精筛后 121 张最终结果（其中皮肤病被剔除 60+ 条）。

### 约束 B：古今同名方剂去重

**问题本质**：经典膏药方剂（如**狗皮膏/虎骨膏/金不换膏/太乙膏/万应膏/阳和解凝膏**）在数据库里**14+ 个变方同名出现**，如：
  - `狗皮膏` — 14 条不同方（清·陈文治《疡科选粹》原方 → 现代 13 个中成药变方）
  - `虎骨膏` — 2 条（清·吴谦《医宗金鉴》+ 现代变方）
  - `加味太乙膏` — 4 条（明·陈实功原方 + 3 个清代变方）
  - `万应膏` — 9 条
  - `化铁膏` / `化痞膏` — 1+10 条
  - `紫金膏` — 15 条（明·陈实功 + 清·吴谦 + 现代多个变方）

**症状**：直接用 `MingCheng LIKE '%狗皮膏%'` 返回 14 条，但其中只有 1 条是**清代原方**，其余 13 条是现代工艺变方（药材重量不同、基质改为橡胶+凡士林）。

**解决 SOP**：
  - **数据库设计阶段**：保留 `DISTINCT MingCheng` 后，**保留全部变方**但每条标注出处朝代
  - **文档撰写阶段**：在「经典方根」章节把同一基方的多个变方**家族化**呈现（如太乙膏家族 3 个变方 / 狗皮膏家族 3 个变方 / 虎骨膏家族 3 个变方）
  - **核心区分维度**：
    - 古方：**有具体朝代+古籍**（清·吴谦《医宗金鉴》1742 年）
    - 现代方：**有现代中成药批号/部颁标准**（生川乌800两 / 防己256两 / 橡胶656两 等工业化配方）

### 约束 C：现代中成药 vs 古籍原方 分层

**问题本质**：膏药方的**剂型基质**古今差异巨大：
  - **古方**（唐宋明清）：麻油+黄丹基质（铅丹+麻油熬炼）
  - **近代方**（清末民国）：加入松香、蜂蜡
  - **现代方**（1960 后）：加入橡胶+凡士林+羊毛脂+氧化锌+松香+汽油（巴布膏/橡胶膏剂型）

**症状**：同一首「狗皮膏」古方用黄丹，现代方用橡胶基质——这两者在药效/透皮/安全性都不同，但都在 zysjyj 库里以同名方出现。

**解决 SOP**：在文档「朝代溯源」章节**显式标注**每一首方属于哪一类基质，并在「高频核心药」统计时**长药名优先**避免短药误匹配（详见约束 D）。

### 约束 D（附赠）：长药名优先匹配

**问题本质**：高频药统计时，「生」会匹配到「生地/生姜/生川乌」，「川」会匹配到「川乌/川芎/川断」，导致统计严重不准。

**解决 SOP**：

```python
herbs = ['生地', '生姜', '生川乌', '生草乌', '川乌', '川芎', '川断', '川椒',
         '草乌', '当归', '乳香', '没药', '麝香', ...]
# 长药名优先匹配（按长度降序）
for h in sorted(herbs, key=lambda x: -len(x)):
    if h in cf: counter[h] += 1
```

**实战数据**：颈肩腰腿痛查询 → 「当归」频次 102 是真实数（90%+ 方剂含当归）；如果不长药优先，「川」会统计成 200+ 假阳性。

---

## 二、与母工作流（wenyao_query_workflow.md）的差异对比

| 维度 | 母工作流（闻药） | 本工作流（膏药） |
|------|------------------|------------------|
| **核心主题** | 鼻/鼻窍（明确单一） | 筋骨痹痛（边界模糊：皮肤 vs 筋骨） |
| **病证范围** | 鼻塞/鼻渊/鼻衄/中恶（明确） | 颈/肩/臂/腰/腿/膝/足 + 痹证总称（多部位） |
| **动词** | 吹/纳/灌/嗅/取嚏/熏（明确外用动词） | 贴之/薄贴/摊贴/敷之（但同时有「敷」+「痹」易混入皮肤病） |
| **同名方变方数** | 闻药少（鼻烟 11 / 通鼻窍 19） | 极多（狗皮 14 / 太乙 4 / 万应 9 / 紫金 15） |
| **朝代分层** | 单一朝代为主（清代鼻烟） | 必须显式分层（古方/现代中成药基质差异） |
| **皮肤痹痛 vs 筋骨痹痛** | N/A | **核心陷阱**（约束 A） |
| **同名方去重** | 简单去重 | 家族化呈现（约束 B） |
| **基质分层** | N/A | 古/近代/现代 3 类（约束 C） |
| **典型过滤陷阱** | 关键词不够宽 / 不含真动词 | **皮肤病痹痛误入** / 复合 WHERE 单引号冲突（陷阱 1） |

---

## 三、复合 WHERE 子句的 SQL 字符串转义陷阱（实战踩到）

### 陷阱 1：Python 文档字符串内嵌 SQL 单引号导致 0 命中

**症状**：原本应当返回 700+ 条方剂的复合 WHERE 查询返回 **0 条**。

**问题代码**：
```python
# ❌ 错误：'''...''' 文档字符串内嵌 '...' SQL 单引号边界冲突
q = f'''SELECT DISTINCT MingCheng, GongNengZZ FROM zysjyj 
WHERE (MingCheng LIKE '%膏%' OR ChuFang LIKE '%薄贴%') 
AND (GongNengZZ LIKE '%痹%' OR GongNengZZ LIKE '%腰%')'''
# 实际生成的 SQL 是 WHERE (MingCheng LIKE '%膏%' OR ChuFang LIKE '%薄贴%' )
# 后面 AND 子句被 Python 字符串截断或者 SQL 解析异常
```

**解决代码**：
```python
# ✅ 正确：用 \" 而不是单引号
q = """SELECT DISTINCT MingCheng, GongNengZZ FROM zysjyj
WHERE (MingCheng LIKE \"%膏%\" OR ChuFang LIKE \"%薄贴%\")
AND (GongNengZZ LIKE \"%痹%\" OR GongNengZZ LIKE \"%腰%\")"""

# ✅ 或者：把 f-string 拆成两步，单独用 chr(39) 替代内层引号
q = f"SELECT ... WHERE (MingCheng LIKE '{chr(39)}膏{chr(39)}')"
```

**实战数据**：颈肩腰腿痛查询 → 第一次粗筛 0 条 → 改为 `\"` 后命中 121 张最终结果。

### 陷阱 2：SQL OR 列表被 AND 切断

**症状**：粗筛返回 0 条，但拆开单 OR 子句都能命中 10+ 条。

**问题代码**：
```python
# ❌ 错误：Python 字符串拼接时把列表 join 后，被 f-string {} 解析错乱
verbs = ['%膏%', '%薄贴%', '%贴之%']
gaoji_clauses = []
for k in verbs:
    gaoji_clauses.append(f"MingCheng LIKE '{k}'")
    gaoji_clauses.append(f"ChuFang LIKE '{k}'")
    gaoji_clauses.append(f"GongNengZZ LIKE '{k}'")
gaoji_where = ' OR '.join(gaoji_clauses)
# gaoji_where = "MingCheng LIKE '%膏%' OR ChuFang LIKE '%膏%' OR GongNengZZ LIKE '%膏%' OR ..."

# 接下来 AND 痹痛时：
bbi_clauses = []
for k in pain_kw:
    bbi_clauses.append(f"ChuFang LIKE '{k}'")
    bbi_clauses.append(f"GongNengZZ LIKE '{k}'")
bbi_where = ' OR '.join(bbi_clauses)

q = f"SELECT ... WHERE ({gaoji_where}) AND ({bbi_where})"
# 这种嵌套本身 OK，但 f-string 中如果出现 \" 单引号嵌套会冲突
```

**解决代码**：
```python
# ✅ 正确：用占位符? 而不是直接拼接字符串
def dec(v, enc='gbk'):
    return v.decode(enc, errors='replace') if isinstance(v, bytes) else v

verbs = ['%膏%', '%薄贴%', '%贴之%']
pain_kw = ['%痹%', '%腰%', '%腿%', '%膝%', '%肩%', '%颈%']

# 构造 WHERE 子句（占位符方式）
where_parts = []
params = []
for v in verbs:
    for f in ['MingCheng', 'ChuFang', 'GongNengZZ']:
        where_parts.append(f"{f} LIKE ?")
        params.append(v)

where_main = ' OR '.join(where_parts)

for k in pain_kw:
    for f in ['ChuFang', 'GongNengZZ']:
        where_parts.append(f"{f} LIKE ?")
        params.append(k)
where_bbi = ' OR '.join(where_parts[len(verbs)*3:])

q = f"SELECT DISTINCT MingCheng, ChuFang, GongNengZZ FROM zysjyj WHERE ({where_main}) AND ({where_bbi})"
cur = conn.execute(q, params)
```

### 陷阱 3：编码一刀切（zysjyj=GBK vs zysjllsj=UTF-8）

**症状**：zysjllsj 临床理论库返回的标题乱码（?取代汉字）。

**问题代码**：
```python
# ❌ 错误：text_factory 全局切 GBK（适合 zysjyj，但 zysjllsj 是 UTF-8）
conn.text_factory = lambda b: b.decode('gbk', errors='replace')
cur = conn.execute("SELECT BiaoTi, NeiRong FROM zysjllsj WHERE BiaoTi = '薄贴论'")
# 返回乱码：'???¨??????'
```

**解决代码**：
```python
# ✅ 正确：每张表用专属解码函数
def dec_yj(v):
    """zysjyj = GBK"""
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v

def dec_llsj(v):
    """zysjllsj = UTF-8"""
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

# 方剂库用 dec_yj，理论库用 dec_llsj
```

---

## 四、Stage 1 关键词扩展（膏药专题专用）

### 1.1 主题关键词分类

| 用户自然语言 | 主题 | 病证 | 制剂形态 |
|------------|------|------|----------|
| 「颈肩腰腿痛膏药」 | 痹 / 风湿 / 寒湿 / 筋骨 | 痹痛 / 历节 / 痛风 / 鹤膝 | 膏 / 薄贴 / 贴之 |
| 「跌打损伤膏药」 | 伤 / 瘀 / 血 | 跌打 / 骨折 / 闪挫 | 摊贴 / 敷之 |
| 「风湿疼痛膏药」 | 风 / 湿 / 寒 | 风湿 / 寒湿 / 湿痹 | 膏药薄贴 |
| 「狗皮膏/虎骨膏」 | 具体方名 | 腰腿痛 / 筋骨痛 | 太乙膏 / 万应膏 |

### 1.2 中医专业术语映射（按外治法场景）

| 膏药主题 | 必含病证词 | 必含部位词 | 必含形态词 |
|---------|-----------|-----------|-----------|
| **颈肩腰腿痛** | 痹/历节/痛风/风湿/寒湿/筋骨 | 颈/项/肩/臂/腰/腿/膝/足/脚/背/脊/筋骨 | 膏/薄贴/摊贴/贴之/敷之 |
| **跌打损伤** | 跌打/打扑/闪挫/骨折/筋伤 | 跌/扑/打/闪/挫 | 膏药/薄贴/敷之 |
| **皮肤病膏药**（应**排除**）| 顽癣/瘙痒/抓搔/鹅掌风/血风疮 | 皮肤/痒 | 敷/贴/涂（无「痹在筋骨」部位词） |

---

## 五、Stage 2 SQL 全库精筛（实战代码）

### 5.1 第一步：方名膏剂 + 痹痛主治粗筛

```python
import sqlite3

DB = 'references/external/zysj.db'
conn = sqlite3.connect(DB)

def dec_yj(v):
    if v is None: return None
    return v.decode('gbk', errors='replace') if isinstance(v, bytes) else v

# A. 膏剂形态关键词（方名+处方+主治任意字段命中）
gaoji_kw_list = ['膏', '薄贴', '摊贴', '贴之', '膏药', '药膏',
                 '贴患处', '贴患', '烘贴', '熨之']

# B. 痹痛专属病证关键词
bbi_pain_list = ['颈项', '项强', '肩臂', '肩痛', '臂痛', '腿痛', '膝痛',
                 '足痛', '脚痛', '背痛', '脊痛', '腰腿', '腰膝', '腰脊',
                 '腰酸', '腰疼', '腿酸', '腿疼',
                 '痹', '历节', '白虎风', '鹤膝', '痛风',
                 '行痹', '着痹', '痛痹', '周痹', '湿痹', '寒痹', '热痹', '血痹',
                 '筋痹', '脉痹', '骨痹', '肌痹',
                 '风湿', '寒湿', '湿痹',
                 '筋骨疼痛', '骨节疼痛', '肢节疼痛', '关节疼痛', '筋脉拘挛',
                 '筋急', '筋挛', '拘挛', '挛急', '筋伤', '转筋',
                 '麻木', '不仁', '半身不遂', '偏枯',
                 '筋骨', '骨节', '肢节', '关节', '筋脉', '筋络',
                 '流痰', '痰注', '鹤膝', '缓风', '筋缩',
                 # 跌打损伤
                 '跌打', '打扑', '闪挫', '骨折', '筋断', '跌伤', '打伤',
                 '伤折', '挫伤', '筋伤', '骨碎', '扭伤']

# 用占位符? 构造 WHERE
where_parts = []
params = []
for k in gaoji_kw_list:
    for f in ['MingCheng', 'ChuFang', 'GongNengZZ']:
        where_parts.append(f"{f} LIKE ?")
        params.append(f'%{k}%')

gaoji_where = ' OR '.join(where_parts)

bbi_where_parts = []
bbi_params = []
for k in bbi_pain_list:
    for f in ['ChuFang', 'GongNengZZ']:
        bbi_where_parts.append(f"{f} LIKE ?")
        bbi_params.append(f'%{k}%')

bbi_where = ' OR '.join(bbi_where_parts)

# 完整 SQL
q = f"""SELECT DISTINCT MingCheng, ChuFang, GongNengZZ, TypeID 
FROM zysjyj 
WHERE ({gaoji_where}) AND ({bbi_where})"""

all_params = params + bbi_params
cur = conn.execute(q, all_params)
rows = list(cur)
print(f"Stage 2 膏剂 + 痹痛主治: {len(rows)} 条")
```

### 5.2 第二步：Python 端精筛（关键！应用约束 A/B）

```python
output = []
seen = set()
for r in rows:
    name = dec_yj(r[0]) or ''
    if not name or name in seen:
        continue
    cf = dec_yj(r[1]) or ''
    gz = dec_yj(r[2]) or ''
    blob = cf + '||' + gz + '||' + name

    # 1. 主治必须命中至少一个痹痛专属词
    pain_hits = [k for k in bbi_pain_list if k in gz]
    if not pain_hits:
        continue

    # 2. 部位字命中（应用约束 A：白名单部位词）
    body_parts = ['颈', '项', '肩', '臂', '腰', '腿', '膝', '足', '脚',
                  '背', '脊', '骱']
    bbt_hits = [b for b in ['筋骨', '骨节', '肢节', '关节', '筋脉', '筋络']
                if b in gz or b in cf]
    if not any(b in gz for b in body_parts) and not bbt_hits:
        continue

    # 3. 排除皮肤痹痛（约束 A 核心：黑名单关键词 + 无筋骨部位）
    skin_disease_kw = ['顽癣', '瘙痒', '抓搔', '疥', '鹅掌风', '皮癣',
                       '风癣', '湿癣', '血风疮', '肤痒', '痒搔',
                       '脓水', '黄水', '浸淫', '湿疹']
    has_skin = any(k in blob for k in skin_disease_kw)
    has_body = any(b in gz for b in body_parts) or bbt_hits
    if has_skin and not has_body:
        continue

    # 4. 同名方去重（约束 B：保留变方但在文档中家族化）
    seen.add(name)
    output.append({
        'name': name,
        'chufang': cf,
        'gongnengzz': gz,
        'typeid': r[3],
        'pain_hits': pain_hits,
        'body_parts': [b for b in body_parts if b in gz],
    })

print(f"Stage 2 精筛（颈肩腰腿痛/筋骨痹痛）: {len(output)} 条")
```

### 5.3 第三步：朝代溯源（zysjllsj 临床理论库）

```python
def dec_llsj(v):
    if v is None: return None
    return v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v

# 找「膏药」「薄贴」「贴腰膏」专题文献
themes = ['薄贴', '膏药', '贴腰', '筋骨闪挫', '风湿诸般']
results = []
for t in themes:
    cur = conn.execute(
        f"SELECT ID, BiaoTi, NeiRong FROM zysjllsj WHERE BiaoTi LIKE '%{t}%'"
    )
    for r in cur:
        title = dec_llsj(r[1]) or ''
        content = dec_llsj(r[2]) or ''
        # 必须含痹痛/筋骨
        if any(k in content for k in ['痹', '筋骨', '腰', '腿', '膝', '肩']):
            results.append({
                'id': r[0], 'title': title, 'theme': t,
                'snippet': content[:500]
            })
print(f"zysjllsj 溯源: {len(results)} 条")

# 关键溯源文献（实战 2026-09-07 验证）：
# ID=20378 「薄贴论」(吴尚先《理瀹骈文》1864 年)
# ID=152755 「第二节·薄贴各方」(清·张山雷《疡科纲要》)
# ID=196420 「贴腰膏」(《理瀹骈文》附方)
# ID=79213 「筋骨闪挫膏药方」(71 味大复方, 清·程鹏程《急救广生集》)
# ID=142736 「风湿诸般疼痛膏药」(清·程鹏程《急救广生集》)
# ID=6440 「薄贴（膏药）」(清·徐灵胎《医学源流论》)
```

---

## 六、Stage 3 分类与文档化（8 大功效分类 + 10 节结构）

### 6.1 按功效分类（实战：颈肩腰腿痛查询 121 张）

| 类别 | 数量 | 核心病机 | 代表方 |
|------|-----:|----------|--------|
| **跌打损伤** | 34 | 瘀血内阻、筋断骨折 | 红药贴膏/精制狗皮膏/金不换膏 |
| **腰痛** | 27 | 肾虚/寒湿/血瘀 | 蠲痛五汁膏/虎骨膏/鹿茸膏 |
| **风寒湿痹** | 22 | 风寒湿三气杂至 | 集宝疗痹膏/阳和解凝膏/代温灸膏 |
| **全身筋骨痹痛** | 15 | 全身性筋骨疼痛 | 除湿膏/苍梧道士陈元膏/风损膏药 |
| **筋脉麻木/拘挛** | 13 | 气血不达经络 | 白芷膏/败龟膏/防己膏 |
| **腿膝足痛** | 5 | 下焦寒湿 | 汉防己膏/退痛膏/芥子膏 |
| **颈项痛** | 3 | 颈项强痛 | 桂枝石膏汤/化凤膏/琥珀膏 |
| **半身不遂/瘫痪** | 2 | 中风后遗症 | 益寿比天膏/洞天酥香膏 |

### 6.2 文档结构（10 节，对齐 wenyao_query_workflow.md §六 3.5）

```
1. 起源与触发问题（实战案例）
2. 方剂全表（按 8 大功效分类，含完整处方+主治）
3. 朝代溯源（7-9 个朝代）
4. Top 30-40 高频核心药（本草溯源，应用约束 D 长药优先）
5. 4-5 大经典方根家族（应用约束 B 家族化呈现）
6. 5 大临床实战首推方（按安全度分级）
7. 与本 skill 的关联
8. 临床决策算法（如颈肩腰腿痛 5 步：急性/慢性→虚实→部位→寒热→安全性）
9. 查询方法记录（可复现代码）
10. 变更记录（Changelog）
```

---

## 七、5 大经典方根家族（实战：颈肩腰腿痛查询）

| 方根 | 源流 | 核心组成 | 演变方数 |
|------|------|----------|----------|
| **太乙膏** | 明·陈实功《外科正宗》→ 清·吴谦《医宗金鉴》 | 玄参、白芷、当归、肉桂、生地、赤芍、大黄、黄丹 | **加味太乙膏/加味太一膏/集宝疗痹膏**（3+ 变方） |
| **万应膏** | 明·陈实功→ 清·吴谦 | 川乌、草乌、白芷、当归、大黄、穿山甲、麝香、黄丹 | **金不换膏/金不换神化膏/金不换神仙膏/金丝万应膏**（5+ 变方） |
| **狗皮膏** | 清·陈文治《疡科选粹》→ 现代《药典》 | 枳壳、防风、杏仁、泽泻、川乌、羌活、独活、苦参、穿山甲、麝香 | **精制狗皮膏/淮安狗皮膏**（14+ 变方含现代工艺） |
| **虎骨膏** | 清·吴谦《医宗金鉴》 | 虎骨、川乌、草乌、五加皮、桑枝、槐枝、续断、桃枝、威灵仙 | **虎骨熊油膏/鹿茸膏/保真膏**（3+ 变方） |
| **阳和解凝膏** | 清·王洪绪《外科证治全生集》 | 牛蒡子根、凤仙梗、川附、桂枝、大黄、当归、肉桂、草乌、川乌、僵蚕、苏合油、麝香 | **集宝疗痹膏/回阳玉龙膏**（2+ 变方） |

---

## 八、变更记录

### v1.0 (2026-09-07) — 首次固化
- **新增工作流**：从「颈肩腰腿痛膏药查询」提取的「中医外科膏药方专题查询工作流」
- **3 大专属约束**（vs 母工作流 wenyao_query_workflow.md）：
  - 约束 A：皮肤痹痛 vs 筋骨痹痛 去重（核心陷阱）
  - 约束 B：古今同名方剂 家族化呈现（狗皮 14+ / 太乙 4+ / 万应 9+ / 紫金 15+）
  - 约束 C：现代中成药 vs 古籍原方 分层（基质差异：麻油+黄丹 vs 橡胶+凡士林）
- **3 大 SQL 实战陷阱**：
  - 陷阱 1：Python 文档字符串内嵌 SQL 单引号导致 0 命中
  - 陷阱 2：复合 WHERE 子句被 f-string 切错乱
  - 陷阱 3：zysjyj=GBK / zysjllsj=UTF-8 编码一刀切
- **实战数据**：121 张方剂全表 / 76KB / 524 行 / 8 大功效分类 / Top 40 高频核心药
- **触发词**：「颈肩腰腿痛膏药」「筋骨疼痛膏药」「风湿疼痛膏药」「跌打损伤膏药」「狗皮膏」「虎骨膏」「贴腰膏」「筋骨闪挫膏药」「中医外科膏药方」「薄贴」「摊贴」「贴之」

**【相关文件】**

- `references/wenyao_query_workflow.md` — 母工作流（闻药·鼻吸·鼻烟方剂大全，本文档是姊妹专题）
- `references/gaoyao_jingjianyaotuiteng.md` — 颈肩腰腿痛膏药方大全（本工作流的实战案例）
- `references/wenyao_bixi_daquan.md` — 闻药大全（外治法姊妹专题）
- `references/kouqiang_kuiyang_zhenjiu.md` — 口腔溃疡针灸（外治法姊妹专题）
- `references/known_pitfalls.md` — 10 大 Python/Regex/SQL 陷阱（陷阱 1-3 是其扩展）
- `references/zhongyi_source_citation_principle.md` — 中医方剂引用原文 5 大铁律

**【触发词】**

「中医外科膏药」「中医外科膏方」「中医外科薄贴」「中医外科贴药」「膏药专题查询」「膏药方查询」「颈肩腰腿痛膏药查询」「跌打损伤膏药查询」「风湿疼痛膏药查询」「中医外科膏药工作流」「膏药工作流」