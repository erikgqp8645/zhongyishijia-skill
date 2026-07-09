# 中医世家 SQLite 数据库 — 数据字典与开发指南

> **目的**：让任何开发者、任何机器都能立即理解并使用 `20120413mssql.sqlite`。
> **目标读者**：新加入项目的开发者、CI/CD 维护者、数据工程师。
> **关联文件**：`README.md`（项目级）、`./20120413mssql.sqlite`（660 MB）、`scripts/query_herb.py`（消费者）

---

## 0. 跨机器开发便携性指南（**先看这节**）

### 0.1 路径策略

**绝对禁止硬编码** `C:\Users\Guo\Desktop\...` 这类个人路径。统一使用以下查找顺序：

```python
# scripts/_paths.py（计划中）— 推荐所有脚本 import
from pathlib import Path
import os

def find_sqlite_path() -> Path:
    """按优先级查找 SQLite 文件位置"""
    candidates = [
        # 1. 环境变量（推荐：CI/CD 用）
        Path(os.environ.get("ZHONGYISHIJIA_SQLITE", "")),
        # 2. 用户主目录下的约定路径
        Path.home() / ".cache" / "zhongyishijia" / "20120413mssql.sqlite",
        Path.home() / ".local" / "share" / "zhongyishijia" / "20120413mssql.sqlite",
        # 3. 项目内标准位置（当前文档约定）
        Path(__file__).resolve().parent.parent / "references" / "raw" / "20120413mssql.sqlite",
    ]
    for c in candidates:
        if c and c.exists() and c.is_file():
            return c
    raise FileNotFoundError(
        "找不到 20120413mssql.sqlite。请：\n"
        "1. 设置环境变量：export ZHONGYISHIJIA_SQLITE=/path/to/20120413mssql.sqlite\n"
        "2. 或放到 ~/.cache/zhongyishijia/20120413mssql.sqlite\n"
        "3. 或放到 <project>/references/raw/20120413mssql.sqlite"
    )
```

### 0.2 多用户/多机器的同步策略

| 场景 | 推荐方案 |
|------|---------|
| **本地开发** | 把 SQLite 放到 `references/raw/`（已 .gitignore） |
| **团队共享** | 内部网盘 / S3 / OSS + 一致 SHA256 校验 |
| **CI/CD** | 通过环境变量 `ZHONGYISHIJIA_SQLITE` 注入路径 |
| **Docker** | 挂载 volume 到 `/data/20120413mssql.sqlite`，容器内用 `Path("/data/20120413mssql.sqlite")` |

### 0.3 编码与平台差异

| 项 | Windows | Linux/macOS | Python 处理 |
|---|---|---|---|
| **文件编码** | GBK（MSSQL 备份还原特征）| GBK（与平台无关）| `conn.text_factory = lambda b: b.decode('gbk', errors='replace')` |
| **路径分隔符** | `\` | `/` | 永远用 `pathlib.Path`，不要字符串拼接 |
| **行尾** | CRLF | LF | `open(..., newline='')` |
| **终端输出** | 默认 GBK | 默认 UTF-8 | `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` |
| **大文件读取** | 8MB chunk | 8MB chunk | `for chunk in iter(lambda: f.read(8*1024*1024), b'')` |

### 0.4 文件完整性校验（任何机器部署时必跑）

```bash
# 期望 SHA256: 6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f
python -c "
import hashlib
h = hashlib.sha256()
with open('references/raw/20120413mssql.sqlite', 'rb') as f:
    for chunk in iter(lambda: f.read(8*1024*1024), b''):
        h.update(chunk)
print(h.hexdigest())
"
```

---

## 1. 文件清单

| 文件名 | 大小 | SHA256 | 来源 |
|--------|----:|--------|------|
| `20120413mssql.sqlite` | 660 MB | `6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f` | 中医世家网站 2012-04-13 MSSQL 备份还原 |

---

## 2. 数据库结构总览

| 表名 | 含义 | 行数 | 占比 | 主要字段特征 |
|------|------|-----:|-----:|-------------|
| `zysjyj` | 中药字典 | 70,350 | 22.1% | 38 列，含处方/功能主治/出处/图片 |
| `zysjllsj` | 临床理论 | 166,423 | 52.2% | 8 列，BiaoTi/NeiRong/BM1-4 分类码 |
| `zysjzhsj` | 综合数据 | 80,809 | 25.4% | 8 列，BiaoTi/NeiRong + TuPian/ZhaiLu/ShiJian |
| `zysjcell` | 章节分类索引 | 1,229 | 0.4% | 12 列，网站导航树 |
| **合计** | | **318,811** | 100% | |

---

## 3. 表 schema 详解

### 3.1 `zysjyj`（中药字典）— 38 列

**核心字段**（按使用频率）：

| 字段 | 类型 | 含义 | 说明 |
|------|------|------|------|
| `ID` | INTEGER | 主键（不唯一） | 与 TypeID 联合查 |
| `TypeID` | INTEGER | 类别码 | **40=单味药 / 39=方剂** |
| `MingCheng` | TEXT | 名称 | 药材名（如"细辛"）或方剂名（如"九味羌活丸"）|
| `ChuFang` | TEXT | 处方组成 | 多行逗号分隔（"麻黄,芍药,细辛..."）|
| `GongNengZZ` | TEXT | 功能主治 | 分号分隔（"散寒祛风;止痛;温肺化饮"）|
| `ChuChu` | TEXT | 出处 | **多出处拼接**（"1.出自《神农本草经》。... 2.《名医别录》：... 3.《本草图经》：..."）|
| `LaiYuan` | TEXT | 来源引用 | 如"《中华本草》" |
| `XingWei` | TEXT | 性味 | "辛；温；小毒" |
| `GuiJing` | TEXT | 归经 | "肺；肾；心；肝" |
| `FuFang` | TEXT | 复方列表 | "小青龙汤《伤寒论》；麻黄附子汤《伤寒论》" |
| `YongFaYL` | TEXT | 用法用量 | "内服：煎汤，1.5-9g；研末，1-3g" |
| `ZhuYi` | TEXT | 禁忌 | "气虚多汗，血虚头痛，阴虚咳嗽等忌服" |
| `ZhiFa` | TEXT | 制法 | |
| `XingZhuang` | TEXT | 性状 | |
| `HuaXueCF` | TEXT | 化学成分 | |
| `YaoLiZY` | TEXT | 药理作用 | |
| `DuXing` | TEXT | 毒性 | |
| `JianBie` | TEXT | 鉴别 | |
| `HanLiangCD` | TEXT | 含量测定 | |
| `PaoZhi` | TEXT | 炮制 | |
| `XingWei2` | TEXT | 性味 (备用) | 极少使用 |
| `GuiJing2` | TEXT | 归经 (备用) | 极少使用 |
| `GuiGe` | TEXT | 规格 | |
| `ZhuCang` | TEXT | 贮藏 | |
| `ZhiJi` | TEXT | 制剂 | |
| `GeJiaLS` | TEXT | 各家论述 | |
| `LinChuangYY` | TEXT | 临床应用 | |
| `BeiZhu` | TEXT | 备注 | |
| `ZhaiLu` | TEXT | 摘录 | |
| `ShiJian` | TEXT | 时间 | |
| `PYFile` | TEXT | 拼音文件名 | "guangzao" |
| `TuPian` | TEXT | 图片文件名（多） | "guangzao_1.jpg,guangzao_2.jpg" |
| `PinYin` | TEXT | 拼音 | "guangzao" |
| `PinYinZT` | TEXT | 拼音字头 | "gz" |
| `YingWenMing` | TEXT | 英文名 | "FRUCTUS CHOEROSPONDIATIS" |
| `BieMing` | TEXT | 别名 | |
| `ChuFang2` | TEXT | 处方 (备用) | 极少使用 |
| `NumberID` | INTEGER | 编号 | |

**TypeID 分布**（zykjyj 中）：
- `TypeID=40` — 单味药（如"细辛"、"人参"、"麻黄"）
- `TypeID=39` — 中成药/方剂（如"九味羌活丸"、"小青龙合剂"）
- 其他 TypeID — 历史遗留类别，少量存在

### 3.2 `zysjllsj`（临床理论）— 8 列

| 字段 | 类型 | 含义 |
|------|------|------|
| `TypeID` | INTEGER | 类别码（28/69/254/337/472/495/517/648/691/700/708/725/760/769/895/944/1032/1034/1101/1293/1295/...） |
| `ID` | INTEGER | 主键 |
| `BiaoTi` | TEXT | 标题 |
| `NeiRong` | TEXT | 内容（CRLF 分隔多段）|
| `BM1` | INTEGER | 分类码 1 |
| `BM2` | INTEGER | 分类码 2 |
| `BM3` | INTEGER | 分类码 3 |
| `BM4` | INTEGER | 分类码 4 |

**TypeID → (朝代, 著作, 作者) 映射**：见 `scripts/query_formula.py` 的 `TYPEID_MAP`（29 条已收录）

### 3.3 `zysjzhsj`（综合数据）— 8 列

| 字段 | 类型 | 含义 |
|------|------|------|
| `TypeID` | INTEGER | 类别码 |
| `ID` | INTEGER | 主键 |
| `BiaoTi` | TEXT | 标题 |
| `NeiRong` | TEXT | 内容 |
| `TuPian` | TEXT | 图片 |
| `ZhaiLu` | TEXT | 摘录 |
| `ShiJian` | TEXT | 时间（如 "2005-09-30"）|
| `KeyWord` | TEXT | 关键词 |

### 3.4 `zysjcell`（章节分类索引）— 12 列

| 字段 | 类型 | 含义 |
|------|------|------|
| `Cell_ID` | INTEGER | 自身节点 ID |
| `Cell_0` | INTEGER | 父节点 ID（顶级分类的 10 个值：101/201/301/401/501/701/801/830/901/1012）|
| `Cell_1` | INTEGER | 同级排序（同 Cell_0 下的顺序）|
| `Cell_2` | INTEGER | 同级排序（更深一层）|
| `Cell_BiaoTi` | TEXT | 标题（分类名/书名）|
| `Cell_TuPian` | TEXT | 图片 |
| `Cell_PinYin` | TEXT | 拼音 URL slug |
| `Cell_JianJie` | TEXT | 简介 |
| `Cell_NeiRong` | TEXT | 内容（多为空）|
| `Cell_ZhiXingWenJian` | TEXT | ASP 文件名 |
| `Cell_WenJianJia` | TEXT | URL 路径 |
| `Cell_ShiJian` | TEXT | 时间 |

**10 个顶级分类**（按 Cell_0 出现次数排序）：

| Cell_0 | 子节点数 | 推断分类 | 代表内容 |
|---:|---:|---|---|
| **301** | **694** | 📚 理论书系 | 中医基础理论/诊断学/内/外/妇/儿/眼科学/针灸学/中药学；《黄帝内经》《伤寒论》《本草纲目》|
| **701** | **429** | 📖 综合方论 | 各家注解/临证应用 |
| 830 | 81 | 地方医家 | 王绍堂/王体仁等 |
| 101 | 11 | 家传医书 | 民间医家传承手稿 |
| 401 | 7 | 中药方剂 | 中药/方剂索引 |
| 201 | 3 | 业内相关 | 友情链接/公告 |
| 501 | 1 | 杂集 | 单条 |
| 801 | 1 | 医学心得 | 单条 |
| 901 | 1 | 单条 | 单条 |
| 1012 | 1 | 单条 | 单条 |

### 3.5 书籍章节拼接机制（BM1-BM4 层级结构）

> **核心发现**：一本中医古籍（如《伤寒论》）通过 `zysjllsj` 表的 **BM1/BM2/BM3/BM4 四级层级编号** + `zysjcell` 导航树还原章节结构。

#### 3.5.1 两表分工

| 表 | 职责 | 角色 |
|---|---|---|
| `zysjcell` | 网站侧边栏导航树 | **目录索引**：告诉网站"《伤寒论》在哪个 URL 下，有哪些章节" |
| `zysjllsj` | 书的正文内容 | **正文存储**：所有条文/方剂的实际内容，按 BM1-4 层级存放 |

#### 3.5.2 `zysjcell` 导航树结构

`Cell_0 / Cell_1 / Cell_2` 三级层级，对应网站的侧边栏树形导航：

| 字段 | 含义 | 伤寒论的典型值 |
|---|---|---|
| `Cell_0` | 一级分类 | `301` = 理论书系 |
| `Cell_1` | 二级分类（书名）| `5` = 中医伤寒类 |
| `Cell_2` | 三级排序（章节序号）| `10` = 《伤寒论》, `12` = 《伤寒杂病论》, … |
| `Cell_BiaoTi` | 节点标题 | 《伤寒论》 |
| `Cell_WenJianJia` | URL 路径 | `/lilunshuji/shanghanlun/` |

**示例**（Cell_0=301 理论书系下的伤寒分支）：

```sql
SELECT Cell_ID, Cell_0, Cell_1, Cell_2, Cell_BiaoTi, Cell_WenJianJia
FROM zysjcell
WHERE Cell_WenJianJia LIKE '%shanghan%'
ORDER BY Cell_2;
-- Cell_ID=98,  Cell_0=301, Cell_1=5, Cell_2=10  → 《伤寒论》
-- Cell_ID=103, Cell_0=301, Cell_1=5, Cell_2=12  → 《伤寒杂病论》
-- Cell_ID=155, Cell_0=301, Cell_1=5, Cell_2=150 → 《伤寒发微论》
-- ...
```

#### 3.5.3 `zysjllsj` 正文 BM1-BM4 层级

BM = "编目"（bookmark/catalog 的缩写），4 级编号唯一确定一条记录：

```
BM1=10   → 书名：《伤寒论》
  └─ BM2=17  → 章：辨太阳病  (共100条记录)
       ├─ BM3=1   → 节：第1节（麻黄汤等方）
       │    ├─ BM4=0 → 节标题行（如"榧子树皮酒方"）
       │    ├─ BM4=1 → 正文条目（如"手部"症状）
       │    ├─ BM4=2 → 正文条目（如"绱呴戦敪"）
       │    └─ BM4=3 → 正文条目（如"1.白虎汤（《伤寒论》）"）
       ├─ BM3=2   → 节：第2节（桂枝汤等方）
       └─ BM3=3   → 节：第3节（葛根汤等方）
```

**字段含义**：

| 层级 | 字段 | 含义 | 伤寒论示例 |
|---|---|---|---|
| 书 | `BM1` | 书名编号 | `10` = 《伤寒论》 |
| 章 | `BM2` | 章编号 | `17` = 辨太阳病 |
| 节 | `BM3` | 节编号（从 1 开始）| `1` = 第 1 节 |
| 条 | `BM4` | 条目序号（`0` = 标题/前言；`>0` = 正文）| `3` = 第 3 条 |

**层级规律**：
- `BM3=0, BM4=0` → 整本书的前言/总论（极少）
- `BM3>0, BM4=0` → 本节的章节标题行（如方剂名、篇名）
- `BM3>0, BM4>0` → 本节的具体条文/方剂正文
- 同一 `BM3` 下有多条时，`BM4` 从 1 起递增

#### 3.5.4 完整定位示例：白虎汤条文

```sql
SELECT ID, BiaoTi, NeiRong, BM1, BM2, BM3, BM4
FROM zysjllsj
WHERE BM1=10 AND BM2=17 AND BM3=1 AND BM4=3;
-- ID=193248, BiaoTi="1.白虎汤（《伤寒论》）", NeiRong="组成·用法·功能..."
```

| 字段 | 值 | 含义 |
|---|---|---|
| ID | 193248 | 主键 |
| BM1 | 10 | 《伤寒论》 |
| BM2 | 17 | 辨太阳病 |
| BM3 | 1 | 第 1 节 |
| BM4 | 3 | 第 3 条（白虎汤正文）|
| BiaoTi | 1.白虎汤（《伤寒论》）| 标题 |
| NeiRong | 组成:石膏30g 知母9g… | 612 字完整条文 |

#### 3.5.5 重建一本书的 SQL

```sql
-- 重建《伤寒论》全部章节目录
SELECT DISTINCT BM2, BM3, BiaoTi
FROM zysjllsj
WHERE BM1 = 10
  AND BM3 = 0          -- 只取节标题行
  AND BM4 = 0
ORDER BY BM2, BM3;

-- 取出某一章（如 BM2=17 辨太阳病）的全部条文
SELECT BM3, BM4, BiaoTi, NeiRong
FROM zysjllsj
WHERE BM1 = 10 AND BM2 = 17 AND BM3 > 0
ORDER BY BM3, BM4;

-- 用 zysjcell 交叉验证：找到 BM1=10 对应哪本书
SELECT Cell_BiaoTi, Cell_WenJianJia
FROM zysjcell
WHERE Cell_0 = 301 AND Cell_1 = 5 AND Cell_2 = 10;
-- → 《伤寒论》, /lilunshuji/shanghanlun/
```

#### 3.5.6 已知规律

- `BM1` 值域：`1` ~ `213`，共 213 种不同书籍
- `BM2` 在同一 `BM1` 下通常 `1` ~ `161`（章数不等）
- 伤寒论（BM1=10）有 **161 章**，其中 BM2=17（辨太阳病）包含 100 条记录
- **Cell_2 与 BM1 无直接数值对应关系**（伤寒论 Cell_2=10→BM1=10；伤寒杂病论 Cell_2=12→BM1=3）
- **关键发现：`zysjllsj.TypeID` 与 `zysjcell.Cell_ID` 共享同一数值域**（988 个共同值）
  - 可通过 `TypeID=Cell_ID` 互查两表
  - 对 166,423 条记录中的 166,421 条（99.999%），其 `TypeID` 都能在 `zysjcell` 中找到对应节点
  - 但 `TypeID` 的语义是"主题/分类/医家"，不是"书籍"——同一本书（如《伤寒论》）的注解会被多个 `TypeID` 分散到多个 `BM1` 中
  - **正确桥接方向**：`TypeID` → 在各 `BM1` 下的分布集中度 → 取集中度 ≥90% 的 `TypeID` → 用 `Cell_ID` 查 `Cell_BiaoTi` 得书名

#### 3.5.7 BM1→书名 桥接算法与已知映射

**算法**（自动建立 `BM1→书名` 映射）：

```sql
-- 1. 对每个交集中的 TypeID，找其最集中的 BM1 及集中度
SELECT TypeID, BM1, COUNT(*) as cnt
FROM zysjllsj
WHERE TypeID IN (SELECT DISTINCT Cell_ID FROM zysjcell)
GROUP BY TypeID, BM1;

-- 2. 取集中度 >= 90% 的高可信 TypeID
-- 3. 用 Cell_ID 查 zysjcell.Cell_BiaoTi 得书名
SELECT Cell_BiaoTi FROM zysjcell WHERE Cell_ID = :typeid;
```

**已确认的 BM1→书名 映射**（见 `scripts/_book_map.py`）：

| BM1 | 确认书名 | 覆盖条目 | 验证状态 |
|----:|----------|-------:|:--------:|
| 3 | 《伤寒杂病论》 | 7,569 | ✅ 人工确认 |
| 10 | 《伤寒论》 | 7,724 | ✅ 人工确认 |
| 1 | （综合政策文件） | 8,878 | ⚠️ 待复核 |
| 2 | （中医内科学） | 17,053 | ⚠️ 待复核 |
| 4 | （中药学/药学） | 10,467 | ⚠️ 待复核 |
| 5 | （各家医方） | 11,853 | ⚠️ 待复核 |
| 6 | （本草/药物学） | 12,948 | ⚠️ 待复核 |
| 7-213 | — | — | ⏳ 待逐本验证 |

> **重要**：部分 `BM1` 内容横跨多本书（如 BM1=2 含多种临床理论），强行映射到单一书名会丢失信息。这些 `BM1` 应标记为"综合"而非具体书名。
| 黄帝内经·素问 | 3 | 100 | — | — | — | 同上 |
| 金匮要略 | 52 | 125 | — | — | — | 同上 |
| 难经 | 15 | 102 | — | — | — | 同上 |

> **注**：本草纲目等书的 BM1 难以通过书名匹配确定（章节标题不含书名），因为同一本书的内容被分散在多个 BM1 下。实际使用中建议以 **BM1=10（伤寒论）** 为唯一样本，验证重建逻辑后再扩展。

---

## 4. 编码与连接

```python
import sqlite3
from pathlib import Path

def open_zysj_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    # 关键：声明 text_factory 解 GBK
    conn.text_factory = lambda b: b.decode('gbk', errors='replace')
    return conn
```

**错误模式**：不设置 `text_factory` 会得到 `b'\x...'` 的字节串。

---

## 5. 典型药材案例：细辛（完整剖析）

### 5.1 细辛本药记录

**位置**：`zysjyj`，`TypeID=40`，`MingCheng='细辛'`

```sql
SELECT MingCheng, ChuChu, LaiYuan, GongNengZZ, XingWei, GuiJing, FuFang
FROM zysjyj
WHERE TypeID=40 AND MingCheng='细辛';
```

| 字段 | 真实值 |
|------|------|
| MingCheng | 细辛 |
| XingWei | 辛；温；小毒 |
| GuiJing | 肺；肾；心；肝；胆；脾经 |
| GongNengZZ | 散寒祛风；止痛；温肺化饮；通窍。主风寒表证；头痛，牙痛；风湿痹痛；痰饮咳喘；鼻塞；鼻渊；口疮 |
| YongFaYL | 内服：煎汤，1.5-9g；研末，1-3g。外用：适量... |
| ZhuYi | 气虚多汗，血虚头痛，阴虚咳嗽等忌服... |
| FuFang | 小青龙汤《伤寒论》；麻黄附子汤《伤寒论》；苓甘五味姜辛汤《金匮要略》 |
| ChuChu | 1.出自《神农本草经》。... 2.《名医别录》：... 3.《本草图经》：...（《吴普本草》《药性论》《本草经疏》《汤液本草》《雷公炮制药性解》《本草纲目》《医学衷中参西录》等多出处拼接）|

### 5.2 细辛关联数据统计

| 数据维度 | 来源 | 数量 | 说明 |
|----------|------|----:|------|
| 本药本草论述 | zysjyj TypeID=40 | 1 条 | 历代综合于一条记录的 ChuChu 字段 |
| 含细辛的方剂 | zysjyj TypeID=39, ChuFang LIKE '%细辛%' | **2,639 条** | 方剂库中含此药材 |
| 临床理论涉及 | zysjllsj NeiRong LIKE '%细辛%' | **5,933 条** | 历代医家论述 |
| 综合数据涉及 | zysjzhsj NeiRong LIKE '%细辛%' | **938 条** | |
| **总涉及** | | **9,511 条** | |

### 5.3 含细辛的经典方剂（节选自 zysjyj FuFang/ChuFang 字段）

| 方剂名 | 来源 | 处方（节选）| 主治 |
|--------|------|------------|------|
| **小青龙汤** | 《伤寒论》东汉 张仲景 | 麻黄、芍药、细辛、干姜… | 外寒内饮 |
| **麻黄附子细辛汤** | 《伤寒论》东汉 张仲景 | 麻黄二两，细辛二两，附子一枚 | 少阴病始得之，反发热脉沉 |
| **苓甘五味姜辛汤** | 《金匮要略》东汉 张仲景 | 茯苓、甘草、五味子、干姜、细辛 | 痰饮 |
| 川芎圆 | 《太平惠民和剂局方》宋 | 川芎、龙脑、薄荷叶、细辛五两 | 消风壅，化痰涎 |
| 羌活防风汤 | （宋明方书）| 羌活、防风、川芎、细辛各一钱 | 破伤风 |
| 加减三五七散 | （宋明方书）| 细辛八两，干姜十两，防风十二两 | 八风五痹 |
| 羌活愈风汤 | （宋明方书）| 含细辛七分半 | 肾肝虚筋骨弱 |
| 祛风至宝丹 | （宋明方书）| 含细辛五钱 | 诸风热 |
| 黑神丹 | （宋明方书）| 含细辛三钱半 | 风气上攻口眼歪斜 |
| 橘皮汤 | 《太平圣惠方》宋 王怀隐 | 含细辛一两半 | 肺脏本热伤风 |
| 款冬花丸 | 《太平圣惠方》宋 王怀隐 | 含细辛二两 | 积年咳嗽唾脓血 |
| 川芎散 | （宋明方书）| 含北细辛三分 | 眩晕恶风自汗 |
| 薏苡仁散 | 《太平圣惠方》宋 王怀隐 | 含细辛一两 | 肝中风四肢挛急 |

---

## 6. 完整 SOURCE_MAP（朝代/作者推断字典）

> **目的**：`scripts/query_formula.py` 与 `query_herb.py` 共用这套映射，从 `source_ref` 字符串推断 (朝代, 著作, 作者)。
> **当前规模**：53 条 SOURCE_MAP + 29 条 TYPEID_MAP = 82 条。
> **覆盖率**：实测算 17.2% 命中；扩展后预计可达 60%+。

### 6.1 SOURCE_MAP（书名 → 朝代/著作/作者）

```python
SOURCE_MAP = {
    # ── 东汉 ──
    "伤寒论":     ("东汉", "《伤寒论》",     "张仲景"),
    "金匮要略":   ("东汉", "《金匮要略》",   "张仲景"),
    # ── 梁 ──
    "本草经集注": ("梁",   "《本草经集注》", "陶弘景"),
    "名医别录":   ("梁",   "《名医别录》",   "陶弘景"),
    # ── 魏 ──
    "吴普本草":   ("魏",   "《吴普本草》",   "吴普"),
    # ── 唐 ──
    "新修本草":   ("唐",   "《新修本草》",   "苏敬"),
    "唐本草":     ("唐",   "《新修本草》",   "苏敬"),
    "千金":       ("唐",   "《备急千金要方》", "孙思邈"),
    "千金翼方":   ("唐",   "《千金翼方》",   "孙思邈"),
    "备急千金要方": ("唐", "《备急千金要方》", "孙思邈"),
    "外台":       ("唐",   "《外台秘要》",   "王焘"),
    "外台秘要":   ("唐",   "《外台秘要》",   "王焘"),
    "药性论":     ("唐",   "《药性论》",     "甄权"),
    # ── 宋 ──
    "证类本草":   ("宋",   "《经史证类备急本草》", "唐慎微"),
    "经史证类备急本草": ("宋", "《经史证类备急本草》", "唐慎微"),
    "本草图经":   ("宋",   "《本草图经》",   "苏颂"),
    "圣济总录":   ("宋",   "《圣济总录》",   "赵佶"),
    "圣惠":       ("宋",   "《太平圣惠方》", "王怀隐"),
    "太平圣惠方": ("宋",   "《太平圣惠方》", "王怀隐"),
    "局方":       ("宋",   "《太平惠民和剂局方》", ""),
    "太平惠民和剂局方": ("宋", "《太平惠民和剂局方》", ""),
    # ── 金 ──
    "明理论":     ("金",   "《明理论》",     "成无己"),
    "成无己":     ("金",   "《明理论》",     "成无己"),
    # ── 元 ──
    "汤液本草":   ("元",   "《汤液本草》",   "王好古"),
    # ── 日本江户 ──
    "药征":       ("日本江户", "《药征》",     "吉益东洞"),
    "吉益东洞":   ("日本江户", "《药征》",     "吉益东洞"),
    # ── 明 ──
    "本草纲目":   ("明",   "《本草纲目》",   "李时珍"),
    "景岳全书":   ("明",   "《景岳全书》",   "张介宾"),
    "伤寒论条辨": ("明",   "《伤寒论条辨》", "方有执"),
    "证治准绳":   ("明",   "《证治准绳》",   "王肯堂"),
    "医学入门":   ("明",   "《医学入门》",   "李梴"),
    "奇效良方":   ("明",   "《奇效良方》",   "方贤"),
    "普济方":     ("明",   "《普济方》",     "朱橚"),
    "本草经疏":   ("明",   "《本草经疏》",   "缪希雍"),
    "雷公炮制药性解": ("明", "《雷公炮制药性解》", "李中梓"),
    # ── 清 ──
    "四圣心源":   ("清",   "《四圣心源》",   "黄元御"),
    "伤寒悬解":   ("清",   "《伤寒悬解》",   "黄元御"),
    "医学金针":   ("清",   "《医学金针》",   "黄元御"),
    "伤寒来苏集": ("清",   "《伤寒来苏集》", "柯琴"),
    "医宗金鉴":   ("清",   "《医宗金鉴》",   "吴谦"),
    "伤寒论集注": ("清",   "《伤寒论集注》", "张隐庵"),
    "伤寒论辨证广注": ("清", "《伤寒论辨证广注》", "汪昂"),
    "本草备要":   ("清",   "《本草备要》",   "汪昂"),
    "伤寒缵论":   ("清",   "《伤寒缵论》",   "张璐"),
    "本经逢原":   ("清",   "《本经逢原》",   "张璐"),
    "伤寒大白":   ("清",   "《伤寒大白》",   "秦之桢"),
    "证治汇补":   ("清",   "《证治汇补》",   "李用粹"),
    "伤寒论纲目": ("清",   "《伤寒论纲目》", "沈金鳌"),
    "伤寒论本旨": ("清",   "《伤寒论本旨》", "章楠"),
    "伤寒论类方": ("清",   "《伤寒论类方》", "徐灵胎"),
    "辨证录":     ("清",   "《辨证录》",     "陈士铎"),
    "医学真传":   ("清",   "《医学真传》",   "高士宗"),
    "药证续编":   ("清",   "《药证续编》",   "村井杶"),
    "伤寒温疫条辨": ("清", "《伤寒温疫条辨》", "杨栗山"),
    "伤寒论经解": ("清",   "《伤寒经解》",   ""),
    "伤寒论集成": ("清",   "《伤寒论集成》", ""),
    # ── 民国 ──
    "曹颖甫":     ("民国", "《伤寒金匮发微》", "曹颖甫"),
    "经方实验录": ("民国", "《经方实验录》", "曹颖甫"),
    "医学衷中参西录": ("民国", "《医学衷中参西录》", "张锡纯"),
    # ── 现代 ──
    "中华本草":   ("现代", "《中华本草》",   "国家中医药管理局《中华本草》编委会"),
    "中国药典":   ("现代", "《中国药典》",   "国家药典委员会"),
    "全国中草药汇编": ("现代", "《全国中草药汇编》", "全国中草药汇编编写组"),
    "中药大辞典": ("现代", "《中药大辞典》", "江苏新医学院"),
    "辞典":       ("现代", "《中药大辞典》", "江苏新医学院"),  # 脱敏形式
    "北京市中药成药选集": ("现代", "《北京市中药成药选集》", "北京市卫生局"),
    "中国中医药报": ("现代", "《中国中医药报》", ""),
    "方剂学":     ("现代", "《方剂学》",     ""),
    "方剂歌诀":   ("现代", "《方剂歌诀》",   ""),
    "中医名词":   ("现代", "《中医名词术语》", ""),
    "中医症状":   ("现代", "《中医症状鉴别》", ""),
    "中医大辞典": ("现代", "《中医大辞典》", ""),
}
```

### 6.2 TYPEID_MAP（zysjllsj TypeID → 朝代/著作/作者）

```python
TYPEID_MAP = {
    "58":  ("东汉", "《伤寒论》", "张仲景"),
    "98":  ("东汉", "《伤寒论》", "张仲景"),
    "103": ("东汉", "《伤寒论》", "张仲景"),
    "124": ("明",   "《景岳全书》", "张介宾"),
    "166": ("现代", "《中医大辞典》", ""),
    "195": ("现代", "《中医名词术语》", ""),
    "254": ("清",   "《本草备要》", "汪昂"),
    "280": ("清",   "《伤寒经解》", ""),
    "337": ("清",   "《医宗金鉴》", "吴谦"),
    "472": ("明",   "《景岳全书》", "张介宾"),
    "495": ("清",   "《本经逢原》", "张璐"),
    "517": ("民国", "《经方实验录》", "曹颖甫"),
    "648": ("清",   "《伤寒论集注》", "张隐庵"),
    "691": ("清",   "《药证续编》", "村井杶"),
    "700": ("清",   "《证治汇补》", "李用粹"),
    "708": ("清",   "《伤寒论本旨》", "章楠"),
    "725": ("清",   "《伤寒论集注》", "张隐庵"),
    "760": ("清",   "《伤寒温疫条辨》", "杨栗山"),
    "769": ("清",   "《伤寒来苏集》", "柯琴"),
    "895": ("日本江户", "《药征》", "吉益东洞"),
    "944": ("清",   "《伤寒论辨证广注》", "汪昂"),
    "1032": ("民国", "《伤寒金匮发微》", "曹颖甫"),
    "1034": ("清",   "《医宗金鉴》", "吴谦"),
    "1101": ("清",   "《伤寒论经解》", ""),
    "1293": ("清",   "《伤寒悬解》", "黄元御"),
    "1295": ("清",   "《四圣心源》", "黄元御"),
}
```

### 6.3 DYNASTY_ORDER（朝代排序权重）

```python
DYNASTY_ORDER = {
    "东汉": 0, "晋": 1, "唐": 2, "宋": 3, "金": 4, "元": 5,
    "日本江户": 6, "明": 7, "清": 8, "民国": 9, "现代": 10,
}
```

---

## 7. 常用 SQL 查询模板

### 7.1 单味药的本草论述

```sql
SELECT MingCheng, XingWei, GuiJing, GongNengZZ, ChuChu, FuFang
FROM zysjyj
WHERE TypeID = 40
  AND MingCheng = '细辛';
```

### 7.2 某药参与的所有方剂

```sql
SELECT ID, MingCheng, ChuFang, GongNengZZ, ChuChu
FROM zysjyj
WHERE TypeID = 39
  AND ChuFang LIKE '%细辛%'
ORDER BY ChuChu;
```

### 7.3 某书名下的所有方剂

```sql
SELECT MingCheng, ChuFang, GongNengZZ
FROM zysjyj
WHERE TypeID = 39
  AND ChuChu LIKE '%《伤寒论》%';
```

### 7.4 某朝代的所有方剂

```sql
SELECT MingCheng, ChuFang, GongNengZZ, ChuChu
FROM zysjyj
WHERE TypeID = 39
  AND (ChuChu LIKE '%伤寒论%'
    OR ChuChu LIKE '%金匮要略%');
```

### 7.5 临床理论检索（按 TypeID）

```sql
SELECT ID, BiaoTi, NeiRong
FROM zysjllsj
WHERE TypeID = 769   -- 清《伤寒来苏集》柯琴
LIMIT 100;
```

### 7.6 综合数据按时间筛选

```sql
SELECT BiaoTi, NeiRong, ShiJian
FROM zysjzhsj
WHERE ShiJian >= '2000-01-01'
ORDER BY ShiJian DESC
LIMIT 50;
```

### 7.7 章节分类导航（树形）

```sql
-- 顶级分类
SELECT DISTINCT Cell_0 FROM zysjcell ORDER BY Cell_0;
-- → 101, 201, 301, 401, 501, 701, 801, 830, 901, 1012

-- Cell_0=301 下的所有书（理论书系 694 本）
SELECT Cell_ID, Cell_BiaoTi, Cell_PinYin
FROM zysjcell
WHERE Cell_0 = 301
ORDER BY Cell_1, Cell_2;
```

---

## 8. 其他药材/方剂参考清单

下表为项目中已确认存在的常用药材（开发中可能用到的样本）：

| 药材名 | MingCheng 示例 | TypeID | 经典方剂代表 |
|--------|----------------|:------:|-------------|
| 细辛 | 细辛 | 40 | 小青龙汤 / 麻黄附子细辛汤 |
| 麻黄 | 麻黄 | 40 | 麻黄汤 / 麻黄附子细辛汤 / 麻黄升麻汤 |
| 桂枝 | 桂枝 | 40 | 桂枝汤 / 桂枝人参汤 |
| 人参 | 人参 | 40 | 人参汤 / 桂枝人参汤 |
| 党参 | 党参 | 40 | （人参/党参互鉴）|
| 干姜 | 干姜 | 40 | 理中丸 / 苓甘五味姜辛汤 |
| 附子 | 附子 | 40 | 麻黄附子细辛汤 / 四逆汤 |
| 甘草 | 甘草 | 40 | （调和诸药，数百方）|
| 白术 | 白术 | 40 | 理中丸 |
| 黄芩 | 黄芩 | 40 | 黄芩汤 |
| 川芎 | 川芎 | 40 | 川芎茶调散 / 川芎圆 |
| 当归 | 当归 | 40 | 当归四逆汤 |
| 白芍 | 白芍 | 40 | 桂枝汤 / 当归四逆汤 |
| 半夏 | 半夏 | 40 | 小青龙汤 / 半夏厚朴汤 |
| 五味子 | 五味子 | 40 | 小青龙汤 / 苓甘五味姜辛汤 |
| 茯苓 | 茯苓 | 40 | 五苓散 / 苓甘五味姜辛汤 |
| 羌活 | 羌活 | 40 | 九味羌活丸 / 羌活胜湿汤 |
| 防风 | 防风 | 40 | 九味羌活丸 / 玉屏风散 |
| 苍术 | 苍术 | 40 | 九味羌活丸 / 平胃散 |

**查询方法**（以桂枝为例）：

```sql
SELECT MingCheng, XingWei, GuiJing, GongNengZZ, FuFang
FROM zysjyj
WHERE TypeID = 40 AND MingCheng = '桂枝';

-- 含桂枝的所有方剂
SELECT ID, MingCheng, ChuFang, GongNengZZ, ChuChu
FROM zysjyj
WHERE TypeID = 39 AND ChuFang LIKE '%桂枝%';
```

---

## 9. 已知问题与注意事项

### 9.1 编码问题

- **HTML 实体未转义**：部分卡片含 `&amp;#236;` 等实体，输出到终端会显乱码
- **解决方案**：脚本输出前 `html.unescape()`

### 9.2 数据完整性

- **Source 字符串不一致**：同一书可能有 `《伤寒论》`/`伤寒论`/`《伤寒论·辨太阳病脉证并治》` 等多种形态
- **作者信息缺失**：现代方剂多无作者字段（"《中国药典》"、"《方剂学》" 等机构编）

### 9.3 字段为空

- `zysjcell.Cell_NeiRong`：80%+ 为空（导航节点无内容）
- `zysjyj.LaiYuan`：部分药材为空
- `zysjyj.TuPian`：约 30% 药材有图片引用但文件不存在

### 9.4 多用户协作建议

| 角色 | 责任 |
|------|------|
| **数据维护者** | 维护 SOURCE_MAP / TYPEID_MAP；定期跑 `find_sqlite_path()` 校验 |
| **脚本开发者** | 必须从 `find_sqlite_path()` 获取路径，绝不硬编码 |
| **CI/CD 维护者** | 通过环境变量 `ZHONGYISHIJIA_SQLITE` 注入；构建前先校验 SHA256 |
| **文档维护者** | 新增映射或药材时同步更新本文档第 6/8 节 |

---

## 10. 验证清单（任何机器部署时执行）

```bash
# 1. SHA256 校验
python -c "
import hashlib
h = hashlib.sha256()
with open('references/raw/20120413mssql.sqlite', 'rb') as f:
    for chunk in iter(lambda: f.read(8*1024*1024), b''):
        h.update(chunk)
assert h.hexdigest() == '6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f', 'SHA256 mismatch!'
print('✓ SHA256 OK')
"

# 2. 行数校验
python -c "
import sqlite3
conn = sqlite3.connect('references/raw/20120413mssql.sqlite')
conn.text_factory = lambda b: b.decode('gbk', errors='replace')
cur = conn.cursor()
expected = {'zysjyj': 70350, 'zysjllsj': 166423, 'zysjzhsj': 80809, 'zysjcell': 1229}
for t, n in expected.items():
    cur.execute(f'SELECT COUNT(*) FROM [{t}]')
    actual = cur.fetchone()[0]
    assert actual == n, f'{t}: expected {n}, got {actual}'
    print(f'✓ {t}: {actual:,}')
"

# 3. 关键药材存在性
python -c "
import sqlite3
conn = sqlite3.connect('references/raw/20120413mssql.sqlite')
conn.text_factory = lambda b: b.decode('gbk', errors='replace')
cur = conn.cursor()
for herb in ['细辛', '麻黄', '桂枝', '人参', '党参']:
    cur.execute('SELECT COUNT(*) FROM zysjyj WHERE TypeID=40 AND MingCheng=?', (herb,))
    n = cur.fetchone()[0]
    print(f'✓ {herb}: {n} 条本草记录')
"

# 4. .gitignore 验证
git check-ignore references/raw/20120413mssql.sqlite && echo '✓ SQLite 已正确排除'
```

---

## 11. 关联文档

- 项目根目录 `README.md` — 仓库总览
- `docs/PLAN_v3_query_herb.md` — v3.0 开发计划
- `scripts/_source_map.py`（计划中）— 共用映射模块
- `scripts/query_formula.py` — 朝代排序方剂查询
- `scripts/query_herb.py`（计划中）— 按中药查方剂
- `scripts/build_herb_index.py`（计划中）— 反向索引构建
- `references/text_distillation/evidence_cards.jsonl` — 蒸馏后 31.7 万张证据卡