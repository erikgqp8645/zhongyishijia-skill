# references/raw/ — 中医世家原始数据库

> **⚠️ 本目录的数据不进入 git 仓库**（已在 `.gitignore` 排除）。
> 本目录仅供本地开发、调试、重蒸馏 evidence_cards 时使用。

## 📖 必读文档

- **[DATA_DICTIONARY.md](./DATA_DICTIONARY.md)** — 完整数据字典（4 张表 schema / 细辛完整剖析 / SOURCE_MAP 60+ 条 / 20+ 常用药材参考 / 跨机器开发指南）

## 文件清单

| 文件名 | 大小 | 来源 | 说明 |
|--------|-----:|------|------|
| `20120413mssql.sqlite` | 660 MB | 中医世家网站（zysj.com.cn） | 2012-04-13 MSSQL 数据库备份还原到 SQLite |

## 表结构

| 表名 | 含义 | 行数 | 用途 |
|------|------|-----:|------|
| `zysjyj` | 中药字典 | 70,350 | 单味药 + 中成药（含处方/主治/出处） |
| `zysjllsj` | 临床理论 | 166,423 | 历代医家临床论述 |
| `zysjzhsj` | 综合数据 | 80,809 | 综合方论/医话 |
| `zysjcell` | 章节分类索引 | 1,229 | 网站导航树（678 古医书目录） |

**总计 ~318,811 行**

## 关键字段映射（zysjyj）

| SQLite 字段 | 含义 | Evidence card 字段 |
|------------|------|--------------------|
| `MingCheng` | 名称（药材/方剂）| `title` |
| `ChuFang` | 处方组成 | `summary` 中的"处方" |
| `GongNengZZ` | 功能主治 | `summary` 中的"主治" |
| `ChuChu` | 出处（多出处拼接）| `source_ref` |
| `LaiYuan` | 来源引用 | — |
| `XingWei` | 性味 | `summary` 中的"性味" |
| `GuiJing` | 归经 | `summary` 中的"归经" |
| `FuFang` | 复方列表 | — |
| `TypeID` | 类别码 | `tags` 中的 `TypeID:X` |

`TypeID` 区分：
- `TypeID=40` → 中药材单味药（如"细辛"、"人参"）
- `TypeID=39` → 中成药/方剂（如"九味羌活丸"、"小青龙合剂"）

## 编码

- **GBK** 编码（Windows 桌面 MSSQL 还原特征）
- Python 读取必须：`conn.text_factory = lambda b: b.decode('gbk', errors='replace')`

## 验证清单

如果怀疑数据完整性，可执行：

```bash
# SHA256 应匹配 6fa194c9a4177dfdd483c8fd7aa37a9e24e371d0692a85a338777bb6e9aee26f
python -c "
import hashlib
h = hashlib.sha256()
with open('references/raw/20120413mssql.sqlite', 'rb') as f:
    for chunk in iter(lambda: f.read(8*1024*1024), b''):
        h.update(chunk)
print(h.hexdigest())
"

# 表行数应匹配
python -c "
import sqlite3
conn = sqlite3.connect('references/raw/20120413mssql.sqlite')
cur = conn.cursor()
for t in ['zysjyj', 'zysjllsj', 'zysjzhsj', 'zysjcell']:
    cur.execute(f'SELECT COUNT(*) FROM [{t}]')
    print(f'{t}: {cur.fetchone()[0]:,}')
"
# 期望: zysjyj=70350, zysjllsj=166423, zysjzhsj=80809, zysjcell=1229
```

## 与项目的关系

```
references/raw/20120413mssql.sqlite (660 MB, 本地, .gitignore)
        ↓ scripts/redistill_cards.py
references/text_distillation/evidence_cards.jsonl (232 MB, git-lfs, 已提交)
        ↓ Agent 用 scripts/search_course_notes.py / query_formula.py / query_herb.py
LLM 检索回答
```

## 派生数据位置

- `references/text_distillation/evidence_cards.jsonl` — 31.7 万张蒸馏卡（git-lfs 跟踪）
- `references/text_distillation/herb_index.jsonl` — （计划中）反向索引