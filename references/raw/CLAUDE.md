[根目录](../../../CLAUDE.md) > [references](../../CLAUDE.md) > **raw**

# references/raw — 原始 SQLite 数据库

> **职责**：存储 660MB 原始 SQLite 数据，用于本地开发、调试、重蒸馏。
> **状态**：v1.0 已交付（**不入 git**，本地缓存）；SHA256 = `6fa194c9...ee26f`。

---

## ⚠️ 重要约束

**本目录所有 `.sqlite`/`.db`/`.sqlite3` 文件均不入 git 仓库**（已在 `.gitignore` 排除）。每个开发者需自行：

1. 从 [中医世家网站](https://www.zysj.com.cn) 获取 `20120413mssql.sqlite`，或
2. 在团队内网盘 / S3 / OSS 同步，或
3. 通过环境变量 `ZHONGYISHIJIA_SQLITE` 指向其他位置的副本。

---

## 模块职责

存储 lineage-skill 蒸馏之前的**原始数据**，服务于：

1. **本地调试** — 当 evidence_cards.jsonl 有疑问时回查 SQLite 原文
2. **重蒸馏** — v3.0 计划通过 SQLite 重建 evidence_cards.jsonl 的结构化字段
3. **新功能开发** — v3.0 计划用 SQLite 直接查询实现 `query_herb.py`（80ms vs JSONL 8-15s）

---

## 文件清单

| 文件 | 大小 | git | 说明 |
|------|-----:|:---:|------|
| `20120413mssql.sqlite` | 660 MB | ❌ gitignore | MSSQL 备份还原到 SQLite（SHA256 校验） |
| `README.md` | 4 KB | ✅ | 本目录说明 + 表结构 + 验证清单 |
| `DATA_DICTIONARY.md` | 20 KB | ✅ | 完整数据字典（schema + 细辛案例 + SOURCE_MAP + SQL 模板） |

**注意**：README.md 和 DATA_DICTIONARY.md 入 git，但 `.sqlite` 文件被排除。

---

## 入口与启动

### 跨机器路径查找（find_sqlite_path 模板）

```python
from pathlib import Path
import os

def find_sqlite_path() -> Path:
    candidates = [
        # 1. 环境变量（推荐：CI/CD 用）
        Path(os.environ.get("ZHONGYISHIJIA_SQLITE", "")),
        # 2. 用户主目录下的约定路径
        Path.home() / ".cache" / "zhongyishijia" / "20120413mssql.sqlite",
        Path.home() / ".local" / "share" / "zhongyishijia" / "20120413mssql.sqlite",
        # 3. 项目内标准位置
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

### Python 连接模板

```python
import sqlite3
from pathlib import Path

conn = sqlite3.connect(str(find_sqlite_path()))
# 关键：声明 text_factory 解 GBK
conn.text_factory = lambda b: b.decode('gbk', errors='replace')
cur = conn.cursor()
```

---

## 对外接口

### 4 张表（按行数排序）

| 表名 | 含义 | 行数 | 占比 | 主要字段 |
|------|------|-----:|-----:|---------|
| `zysjyj` | 中药字典 | 70,350 | 22.1% | MingCheng / ChuFang / GongNengZZ / ChuChu / TypeID (40=单味药 / 39=方剂) |
| `zysjllsj` | 临床理论 | 166,423 | 52.2% | TypeID / BiaoTi / NeiRong / BM1-4 |
| `zysjzhsj` | 综合数据 | 80,809 | 25.4% | BiaoTi / NeiRong / TuPian / ZhaiLu / ShiJian |
| `zysjcell` | 章节分类索引 | 1,229 | 0.4% | Cell_ID / Cell_0 / Cell_BiaoTi / Cell_NeiRong |
| **合计** | | **318,811** | 100% | |

### 关键查询模式

```sql
-- 1. 单味药本草论述
SELECT MingCheng, XingWei, GuiJing, GongNengZZ, ChuChu, FuFang
FROM zysjyj
WHERE TypeID = 40 AND MingCheng = '细辛';

-- 2. 含某药的所有方剂
SELECT ID, MingCheng, ChuFang, GongNengZZ, ChuChu
FROM zysjyj
WHERE TypeID = 39 AND ChuFang LIKE '%细辛%';

-- 3. 某书名下所有方剂
SELECT MingCheng, ChuFang, GongNengZZ
FROM zysjyj
WHERE TypeID = 39 AND ChuChu LIKE '%《伤寒论》%';

-- 4. 临床理论按 TypeID 筛
SELECT ID, BiaoTi, NeiRong FROM zysjllsj WHERE TypeID = 769 LIMIT 100;
-- 769 = 清《伤寒来苏集》柯琴

-- 5. 综合数据按时间
SELECT BiaoTi, NeiRong, ShiJian FROM zysjzhsj WHERE ShiJian >= '2000-01-01' ORDER BY ShiJian DESC LIMIT 50;
```

---

## 关键依赖与配置

### 文件完整性

- **SHA256**：`6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f`
- 部署到任何机器必跑 SHA256 校验（[DATA_DICTIONARY.md §1](./DATA_DICTIONARY.md)）

### 编码

- **GBK**（Windows MSSQL 还原特征）
- Python：`conn.text_factory = lambda b: b.decode('gbk', errors='replace')`

### 跨平台差异

| 项 | Windows | Linux/macOS |
|---|---|---|
| 路径分隔符 | `\` | `/` |
| 行尾 | CRLF | LF |
| 终端编码 | 默认 GBK | 默认 UTF-8 |

→ 用 `pathlib.Path`，不要字符串拼接。

---

## 数据模型

### zysjyj 关键字段映射

| SQLite 字段 | 含义 | Evidence card 字段 |
|------------|------|--------------------|
| `MingCheng` | 名称 | `title` |
| `ChuFang` | 处方组成 | `summary` 中的"处方" |
| `GongNengZZ` | 功能主治 | `summary` 中的"主治" |
| `ChuChu` | 出处（多出处拼接）| `source_ref` |
| `XingWei` | 性味 | `summary` 中的"性味" |
| `GuiJing` | 归经 | `summary` 中的"归经" |
| `FuFang` | 复方列表 | — |
| `TypeID` | 类别码 | `tags` 中的 `TypeID:X` |

### 顶级分类（zysjcell.Cell_0）

| Cell_0 | 子节点数 | 推断分类 |
|---:|---:|---|
| 301 | 694 | 📚 理论书系 |
| 701 | 429 | 📖 综合方论 |
| 830 | 81 | 地方医家 |
| 101 | 11 | 家传医书 |
| 401 | 7 | 中药方剂 |
| 其他 | 各 1-3 | 杂项 |

---

## 测试与质量

### 部署验证清单（任何机器必跑）

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

# 2. 行数校验：zysjyj=70350, zysjllsj=166423, zysjzhsj=80809, zysjcell=1229

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

### 已知问题

- 部分 `source_ref` 字符串不规范：`《伤寒论》` / `伤寒论` / `《伤寒论·辨太阳病脉证并治》` 同书多种形态
- 现代方剂多无作者字段（"《中国药典》"、"《方剂学》" 等机构编）
- `zysjcell.Cell_NeiRong`：80%+ 为空（导航节点无内容）
- `zysjyj.TuPian`：约 30% 药材有图片引用但文件不存在

---

## 常见问题 (FAQ)

**Q: 我没有 660MB SQLite 怎么办？**
A: 不影响正常使用。本 skill 已蒸馏为 232MB evidence_cards.jsonl，仅关键词检索不需要 SQLite。

**Q: 为什么要重新蒸馏？v3.0 为什么需要 SQLite？**
A: v3.0 计划：
1. 给 evidence_cards.jsonl 加 `card_kind/dynasty/book/author/prescribed_herbs` 结构化字段
2. 实现 `query_herb.py`（按中药查所有方剂，80ms 远快于 JSONL 8-15s）

**Q: 跨机器如何同步 660MB？**
A: 用环境变量 `ZHONGYISHIJIA_SQLITE` 指向网盘/S3 路径；或用 `~/.cache/zhongyishijia/` 约定路径。

---

## 相关文件清单

- [`./README.md`](./README.md) — 本目录说明
- [`./DATA_DICTIONARY.md`](./DATA_DICTIONARY.md) — 完整数据字典（**不要覆盖**）
- [`../text_distillation/CLAUDE.md`](../text_distillation/CLAUDE.md) — 派生数据（git-lfs）
- [`../../../docs/PLAN_v3_query_herb.md`](../../../docs/PLAN_v3_query_herb.md) — v3.0 计划（重蒸馏 + query_herb）

---

## 变更记录 (Changelog)

### 2026-07-06
- 新增本模块 CLAUDE.md
- **不覆盖** [./README.md](./README.md) 与 [./DATA_DICTIONARY.md](./DATA_DICTIONARY.md)

### v1.0
- 20120413mssql.sqlite 首次入库本地（不含 git）